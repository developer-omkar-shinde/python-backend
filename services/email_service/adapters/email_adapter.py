"""Email adapter — Interface to SES and DynamoDB for email logging."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class EmailAdapter:
    """Adapter to AWS SES for sending emails and logging."""

    def __init__(self, ses_client, ddb_resource):
        """Initialize with AWS clients."""
        self.ses_client = ses_client
        self.ddb_resource = ddb_resource
        self.email_log_table = ddb_resource.Table("email_logs")

    def send_welcome_email(
        self,
        user_id: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> bool:
        """Send welcome email via SES."""
        try:
            # Check idempotency
            if self._already_sent(user_id, "welcome"):
                logger.info(f"Welcome email already sent for user {user_id}")
                return True

            # Send via SES
            message_id = self.ses_client.send_email(
                Source="noreply@company.com",
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": f"Welcome {first_name}!"},
                    "Body": {
                        "Html": {
                            "Data": f"""
                            <html>
                                <body>
                                    <h1>Welcome, {first_name}!</h1>
                                    <p>Thank you for signing up.</p>
                                </body>
                            </html>
                            """
                        }
                    },
                },
            )["MessageId"]

            # Log in DynamoDB
            self._log_email_sent(user_id, email, "welcome", message_id)
            logger.info(f"Welcome email sent to {email}")

            return True

        except ClientError as exc:
            logger.error(f"Failed to send welcome email: {exc}")
            self._log_email_failed(user_id, email, "welcome", str(exc))
            return False

    def _already_sent(self, user_id: str, email_type: str) -> bool:
        """Check if email already sent (idempotency)."""
        try:
            response = self.email_log_table.get_item(
                Key={"user_id": user_id, "sort_key": f"email#{email_type}"}
            )
            return "Item" in response
        except ClientError:
            return False

    def _log_email_sent(
        self, user_id: str, email: str, email_type: str, message_id: str
    ) -> None:
        """Log successful email send."""
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
            logger.warning(f"Failed to log email: {exc}")

    def _log_email_failed(
        self, user_id: str, email: str, email_type: str, reason: str
    ) -> None:
        """Log failed email attempt."""
        try:
            self.email_log_table.put_item(
                Item={
                    "user_id": user_id,
                    "sort_key": f"email#{email_type}#failed",
                    "email": email,
                    "reason": reason,
                    "status": "failed",
                    "failed_at": datetime.now(UTC).isoformat(),
                }
            )
        except ClientError as exc:
            logger.warning(f"Failed to log email failure: {exc}")
