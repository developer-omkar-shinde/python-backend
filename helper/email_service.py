"""Email service subscriber — listens to SNS events and sends emails.

In production, this would be a separate service or Lambda function
that subscribes to the user-events SNS topic.

Flow:
1. onboarding_service publishes UserCreated event to SNS
2. SNS forwards event to SQS queue (or triggers Lambda)
3. email_service consumes from SQS and processes
4. Sends welcome email via SES/SendGrid
5. Records sent in DynamoDB for audit

This demonstrates the subscriber pattern.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class EmailTemplate:
    """Email template configuration."""

    template_name: str
    subject: str
    html_body: str


class EmailService:
    """Sends emails via AWS SES.

    In a real system, this would be instantiated per event from SQS,
    making it resilient to failures.
    """

    def __init__(self, region: str = "us-east-1"):
        self.ses_client = boto3.client("ses", region_name=region)
        self.ddb_resource = boto3.resource("dynamodb", region_name=region)
        self.email_log_table = self.ddb_resource.Table("email_logs")

    def send_welcome_email(
        self,
        user_id: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> bool:
        """Send welcome email to newly created user.

        Args:
            user_id: User ID (for idempotency)
            email: User's email address
            first_name: User's first name
            last_name: User's last name

        Returns:
            True if sent successfully
        """
        try:
            # Check if already sent (idempotency)
            if self._already_sent(user_id, "welcome"):
                logger.info(f"Welcome email already sent to {email}")
                return True

            # Send via SES
            template = self._get_welcome_template(first_name)
            message_id = self.ses_client.send_email(
                Source="noreply@company.com",
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": template.subject},
                    "Body": {"Html": {"Data": template.html_body}},
                },
            )["MessageId"]

            # Log in DynamoDB
            self._log_email_sent(
                user_id=user_id,
                email=email,
                email_type="welcome",
                message_id=message_id,
            )

            logger.info(f"Welcome email sent to {email} (MessageId: {message_id})")
            return True

        except ClientError as exc:
            logger.error(f"Failed to send welcome email to {email}: {exc}")
            self._log_email_failed(user_id, email, "welcome", str(exc))
            return False

    def send_verification_email(
        self,
        user_id: str,
        email: str,
        verification_code: str,
    ) -> bool:
        """Send email verification code.

        Args:
            user_id: User ID
            email: Email address
            verification_code: 6-digit code

        Returns:
            True if sent successfully
        """
        try:
            template = EmailTemplate(
                template_name="verification",
                subject="Verify Your Email Address",
                html_body=f"""
                <h1>Email Verification</h1>
                <p>Your verification code is:</p>
                <h2>{verification_code}</h2>
                <p>This code expires in 10 minutes.</p>
                """,
            )

            message_id = self.ses_client.send_email(
                Source="noreply@company.com",
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": template.subject},
                    "Body": {"Html": {"Data": template.html_body}},
                },
            )["MessageId"]

            self._log_email_sent(
                user_id=user_id,
                email=email,
                email_type="verification",
                message_id=message_id,
            )

            return True

        except ClientError as exc:
            logger.error(f"Failed to send verification email to {email}: {exc}")
            return False

    def _get_welcome_template(self, first_name: str) -> EmailTemplate:
        """Get welcome email template."""
        return EmailTemplate(
            template_name="welcome",
            subject=f"Welcome to Company, {first_name}!",
            html_body=f"""
            <html>
                <body>
                    <h1>Welcome, {first_name}!</h1>
                    <p>Thank you for signing up with Company.</p>
                    <p>Get started by:</p>
                    <ul>
                        <li>Complete your profile</li>
                        <li>Verify your email address</li>
                        <li>Add a payment method</li>
                    </ul>
                    <p><a href="https://app.company.com/onboarding">Start Now</a></p>
                    <p>Questions? Contact support@company.com</p>
                </body>
            </html>
            """,
        )

    def _already_sent(self, user_id: str, email_type: str) -> bool:
        """Check if email already sent (idempotency check)."""
        try:
            response = self.email_log_table.get_item(
                Key={
                    "user_id": user_id,
                    "sort_key": f"email#{email_type}",
                }
            )
            return "Item" in response
        except ClientError:
            return False

    def _log_email_sent(
        self,
        user_id: str,
        email: str,
        email_type: str,
        message_id: str,
    ) -> None:
        """Log successfully sent email in DynamoDB."""
        try:
            self.email_log_table.put_item(
                Item={
                    "user_id": user_id,
                    "sort_key": f"email#{email_type}",
                    "email": email,
                    "message_id": message_id,
                    "status": "sent",
                    "sent_at": datetime.now(UTC).isoformat(),
                }
            )
        except ClientError as exc:
            logger.warning(f"Failed to log email in DynamoDB: {exc}")

    def _log_email_failed(
        self,
        user_id: str,
        email: str,
        email_type: str,
        reason: str,
    ) -> None:
        """Log failed email attempt in DynamoDB."""
        try:
            self.email_log_table.put_item(
                Item={
                    "user_id": user_id,
                    "sort_key": f"email#{email_type}#failed",
                    "email": email,
                    "status": "failed",
                    "reason": reason,
                    "failed_at": datetime.now(UTC).isoformat(),
                }
            )
        except ClientError as exc:
            logger.warning(f"Failed to log email failure in DynamoDB: {exc}")


# ============================================================================
# Example: Lambda Handler that processes SNS events
# ============================================================================


def lambda_handler(event: dict[str, Any], context: Any) -> dict:
    """Lambda function that processes SNS events.

    AWS SNS publishes to SQS, and Lambda is triggered by SQS.
    This handler receives SNS events and sends emails.

    Event structure:
    {
        "Records": [
            {
                "Sns": {
                    "Subject": "UserCreated",
                    "Message": '{"event_type": "UserCreated", "data": {...}}'
                }
            }
        ]
    }
    """
    email_service = EmailService()
    results = []

    for record in event.get("Records", []):
        try:
            sns_message = record["Sns"]["Message"]
            event_data = json.loads(sns_message)

            event_type = event_data.get("event_type")
            user_data = event_data.get("data", {})

            # Handle different event types
            if event_type == "UserCreated":
                success = email_service.send_welcome_email(
                    user_id=user_data["user_id"],
                    email=user_data.get("email", "unknown@example.com"),
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                )
                results.append(
                    {
                        "event_type": event_type,
                        "user_id": user_data["user_id"],
                        "success": success,
                    }
                )

            elif event_type == "UserVerified":
                # Could send "verification completed" email
                logger.info(f"User {user_data['user_id']} verified")

            else:
                logger.warning(f"Unknown event type: {event_type}")

        except Exception as exc:
            logger.error(f"Failed to process SNS event: {exc}")
            results.append({"error": str(exc)})

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": len(results), "results": results}),
    }
