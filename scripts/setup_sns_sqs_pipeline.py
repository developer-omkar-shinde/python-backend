"""Setup script to connect SNS topic → SQS queue → Lambda function.

This script demonstrates how to:
1. Create SQS queue
2. Subscribe SNS topic to SQS queue
3. Set permissions for SNS to send to SQS
4. Wire Lambda to poll SQS

Run this once to set up the infrastructure.
"""

from helper.event_publisher import EventPublisher
from helper.sqs_queue_manager import SQSQueueManager

# Configuration
REGION = "us-east-1"
SNS_TOPIC_NAME = "user-events"
SQS_QUEUE_NAME = "user-events-queue"


def setup_sns_sqs_pipeline():
    """Set up SNS → SQS → Lambda pipeline."""

    print("🚀 Setting up SNS → SQS → Lambda pipeline\n")

    # Initialize clients
    event_publisher = EventPublisher(region=REGION)
    queue_manager = SQSQueueManager(region=REGION)

    # Step 1: Create SQS queue
    print("📋 Step 1: Creating SQS queue...")
    queue_url = queue_manager.create_queue(
        queue_name=SQS_QUEUE_NAME,
        visibility_timeout=300,  # 5 minutes for Lambda to process
        message_retention=1209600,  # 14 days
    )
    print(f"✅ Queue created: {queue_url}\n")

    # Step 2: Set permissions - Allow SNS to send to SQS
    print("🔐 Step 2: Setting queue permissions...")
    queue_manager.set_queue_policy(
        queue_url=queue_url,
        sns_topic_arn=event_publisher.user_events_topic_arn,
    )
    print(f"✅ Permissions set\n")

    # Step 3: Subscribe SNS topic to SQS queue
    print("🔗 Step 3: Subscribing SNS topic to SQS queue...")
    subscription_arn = queue_manager.subscribe_sns_to_queue(
        sns_topic_arn=event_publisher.user_events_topic_arn,
        queue_url=queue_url,
        # Optional: filter to only specific event types
        # filter_policy={"EventType": ["user.created", "user.verified"]}
    )
    print(f"✅ Subscription created: {subscription_arn}\n")

    print("=" * 60)
    print("✨ Setup Complete!")
    print("=" * 60)
    print(f"\nSNS Topic ARN:    {event_publisher.user_events_topic_arn}")
    print(f"SQS Queue URL:    {queue_url}")
    print(f"Subscription ARN: {subscription_arn}")
    print("\nNext steps:")
    print("1. Create Lambda function to process SQS messages")
    print("2. Configure SQS as Lambda trigger in AWS Console")
    print("3. Test by publishing an event")


if __name__ == "__main__":
    setup_sns_sqs_pipeline()
