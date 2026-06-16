"""AWS SQS adapter for managing queues and SNS-SQS subscriptions.

SQS acts as a buffer between SNS and Lambda:
- SNS publishes events to SQS queue
- Lambda polls SQS and processes messages
- Failed messages stay in queue for retry
- Provides durability and decoupling

This is the recommended pattern for critical operations like emails and payments.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SQSQueueManager:
    """Manages SQS queues and SNS-SQS subscriptions."""

    def __init__(self, region: str = "us-east-1"):
        self.sqs_client = boto3.client("sqs", region_name=region)
        self.sns_client = boto3.client("sns", region_name=region)
        self.region = region

    def create_queue(
        self,
        queue_name: str,
        visibility_timeout: int = 300,
        message_retention: int = 1209600,
    ) -> str:
        """Create an SQS queue for event processing.

        Args:
            queue_name: Name of the queue (e.g., "user-events-queue")
            visibility_timeout: How long message stays hidden after Lambda receives it (seconds)
            message_retention: How long to keep messages in queue (seconds, default 14 days)

        Returns:
            Queue URL

        Typical settings:
            - Visibility timeout: 5 min (300 sec) - time for Lambda to process
            - Message retention: 14 days - keep unprocessed messages long enough
        """
        try:
            response = self.sqs_client.create_queue(
                QueueName=queue_name,
                Attributes={
                    "VisibilityTimeout": str(visibility_timeout),
                    "MessageRetentionPeriod": str(message_retention),
                },
            )
            queue_url = response["QueueUrl"]
            logger.info(f"Created SQS queue: {queue_url}")
            return queue_url
        except ClientError as exc:
            logger.error(f"Failed to create queue {queue_name}: {exc}")
            raise

    def get_queue_url(self, queue_name: str) -> str:
        """Get URL of existing queue."""
        try:
            response = self.sqs_client.get_queue_url(QueueName=queue_name)
            return response["QueueUrl"]
        except ClientError as exc:
            logger.error(f"Failed to get queue URL for {queue_name}: {exc}")
            raise

    def get_queue_arn(self, queue_url: str) -> str:
        """Get ARN from queue URL."""
        try:
            response = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url, AttributeNames=["QueueArn"]
            )
            return response["Attributes"]["QueueArn"]
        except ClientError as exc:
            logger.error(f"Failed to get queue ARN: {exc}")
            raise

    def subscribe_sns_to_queue(
        self, sns_topic_arn: str, queue_url: str, filter_policy: dict | None = None
    ) -> str:
        """Subscribe SNS topic to SQS queue.

        When events are published to SNS topic, they automatically go to SQS queue.

        Args:
            sns_topic_arn: ARN of SNS topic (e.g., "arn:aws:sns:us-east-1:123:user-events")
            queue_url: URL of SQS queue
            filter_policy: Optional filter to only send specific event types
                Example: {"EventType": ["user.created", "user.verified"]}

        Returns:
            Subscription ARN

        Example flow:
            1. User service publishes "user.created" event to SNS
            2. SNS routes it to this SQS queue
            3. Lambda polls queue and receives the message
            4. Lambda processes and deletes message
        """
        try:
            # Get queue ARN
            queue_arn = self.get_queue_arn(queue_url)

            # Create subscription
            params = {
                "TopicArn": sns_topic_arn,
                "Protocol": "sqs",
                "Endpoint": queue_arn,
                "Attributes": {
                    "RawMessageDelivery": "true",  # Forward message as-is without SNS wrapper
                },
            }

            if filter_policy:
                params["Attributes"]["FilterPolicy"] = json.dumps(filter_policy)

            response = self.sns_client.subscribe(**params)
            subscription_arn = response["SubscriptionArn"]

            logger.info(
                f"Subscribed SNS topic {sns_topic_arn} to SQS queue {queue_url}"
            )
            return subscription_arn

        except ClientError as exc:
            logger.error(
                f"Failed to subscribe SNS to SQS: {exc}",
            )
            raise

    def set_queue_policy(self, queue_url: str, sns_topic_arn: str) -> None:
        """Allow SNS to send messages to SQS queue.

        This is required for SNS-SQS subscription to work.
        """
        try:
            queue_arn = self.get_queue_arn(queue_url)

            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "sns.amazonaws.com"},
                        "Action": "sqs:SendMessage",
                        "Resource": queue_arn,
                        "Condition": {"ArnEquals": {"aws:SourceArn": sns_topic_arn}},
                    }
                ],
            }

            self.sqs_client.set_queue_attributes(
                QueueUrl=queue_url,
                Attributes={"Policy": json.dumps(policy)},
            )

            logger.info(f"Set queue policy to allow SNS {sns_topic_arn}")

        except ClientError as exc:
            logger.error(f"Failed to set queue policy: {exc}")
            raise

    def receive_messages(self, queue_url: str, max_messages: int = 10) -> list[dict]:
        """Receive messages from SQS queue.

        Used by Lambda or polling service to get messages.

        Args:
            queue_url: URL of SQS queue
            max_messages: Number of messages to receive (1-10)

        Returns:
            List of messages with Body, ReceiptHandle, etc.
        """
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=20,  # Long polling
            )
            return response.get("Messages", [])
        except ClientError as exc:
            logger.error(f"Failed to receive messages: {exc}")
            raise

    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """Delete message from queue after processing.

        Called after Lambda successfully processes a message.

        Args:
            queue_url: URL of SQS queue
            receipt_handle: Receipt handle from received message
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url, ReceiptHandle=receipt_handle
            )
            logger.info("Message deleted from queue")
        except ClientError as exc:
            logger.error(f"Failed to delete message: {exc}")
            raise

    def purge_queue(self, queue_url: str) -> None:
        """Delete all messages from queue (useful for testing)."""
        try:
            self.sqs_client.purge_queue(QueueUrl=queue_url)
            logger.info(f"Purged queue: {queue_url}")
        except ClientError as exc:
            logger.error(f"Failed to purge queue: {exc}")
            raise
