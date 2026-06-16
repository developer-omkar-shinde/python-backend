# AWS Event-Driven Architecture: SNS → SQS → Lambda

Complete guide to building event-driven microservices using AWS SNS, SQS, and Lambda.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Step-by-Step Setup](#step-by-step-setup)
4. [Code Patterns](#code-patterns)
5. [Deployment](#deployment)
6. [Reference Implementation](#reference-implementation)

---

## Quick Start

**The simplest event flow:**

```bash
# 1. Create SNS topic
aws sns create-topic --name user-events --region us-east-1

# 2. Create SQS queue
aws sqs create-queue --queue-name user-events-queue --region us-east-1

# 3. Subscribe queue to topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:user-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:ACCOUNT:user-events-queue

# 4. Create Lambda function
aws lambda create-function \
  --function-name user-events-processor \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role

# 5. Configure SQS trigger on Lambda
aws lambda create-event-source-mapping \
  --event-source-arn arn:aws:sqs:us-east-1:ACCOUNT:user-events-queue \
  --function-name user-events-processor \
  --batch-size 10
```

Done! You now have:
- **SNS topic** → publishes events
- **SQS queue** → buffers & stores messages
- **Lambda** → processes messages

---

## Architecture

### Why SNS → SQS → Lambda?

```
┌─────────────────────────────────────────────────────────┐
│                 Event-Driven Pattern                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Publisher Service                                     │
│  (onboarding_service)                                 │
│        │                                               │
│        │ publishes UserCreated event                   │
│        v                                               │
│  SNS Topic (user-events)                              │
│        │                                               │
│        │ fan-out to subscribers                        │
│        ├──────┬──────┬──────┐                         │
│        v      v      v      v                         │
│       SQS   SQS    SQS    Email                       │
│    (onboarding) (analytics) (fraud)  Endpoint        │
│        │                                               │
│        └──► Lambda: onboarding_event_processor        │
│        │                                               │
│        └──► Lambda: email_service                     │
│        │                                               │
│        └──► Lambda: fraud_detection                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Benefits of SNS → SQS → Lambda

| Aspect | Direct SNS→Lambda | SQS Buffer |
|--------|-------------------|-----------|
| **Durability** | ❌ Event lost if Lambda fails | ✅ Message persists in queue |
| **Buffering** | ❌ Lambda must keep up with volume | ✅ SQS absorbs traffic spikes |
| **Retries** | ❌ Limited SNS retries | ✅ Full SQS retry logic |
| **Decoupling** | ❌ Lambda tied to SNS timing | ✅ Lambda processes at own pace |
| **Dead Letter Queue** | ❌ No DLQ support | ✅ Failed messages → DLQ |

---

## Step-by-Step Setup

### Step 1: Create SNS Topic

**Via AWS Console:**
1. Go to **SNS** → **Topics**
2. Click **Create topic**
3. Enter name: `user-events`
4. Click **Create**

**Via CLI:**
```bash
aws sns create-topic --name user-events --region us-east-1
```

**Save the ARN:**
```bash
TOPIC_ARN="arn:aws:sns:us-east-1:088971275490:user-events"
```

---

### Step 2: Create SQS Queue

**Via AWS Console:**
1. Go to **SQS** → **Queues**
2. Click **Create queue**
3. Enter name: `user-events-queue`
4. Type: **Standard**
5. Scroll to **Configuration**:
   - **Visibility timeout**: 300 seconds (5 min)
   - **Message retention**: 1209600 seconds (14 days)
6. Click **Create queue**

**Via CLI:**
```bash
aws sqs create-queue \
  --queue-name user-events-queue \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=1209600 \
  --region us-east-1
```

**Save the URL and ARN:**
```bash
QUEUE_URL="https://sqs.us-east-1.amazonaws.com/088971275490/user-events-queue"
QUEUE_ARN="arn:aws:sqs:us-east-1:088971275490:user-events-queue"
```

---

### Step 3: Set Queue Permissions

Allow SNS to send messages to SQS.

**Via Console:**
1. Open the queue
2. Click **Access Policy** tab
3. Click **Edit**
4. Paste this policy (replace ARNs):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "sns.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:088971275490:user-events-queue",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:sns:us-east-1:088971275490:user-events"
        }
      }
    }
  ]
}
```

**Via CLI:**
```bash
aws sqs set-queue-attributes \
  --queue-url $QUEUE_URL \
  --attributes '{
    "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$QUEUE_ARN'\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"'$TOPIC_ARN'\"}}}]}"
  }' \
  --region us-east-1
```

---

### Step 4: Subscribe SQS to SNS

Connect them — messages published to SNS automatically go to SQS.

**Via Console:**
1. Go to **SNS** → **Topics** → **user-events**
2. Scroll to **Subscriptions**
3. Click **Create subscription**
4. Fill in:
   - **Topic ARN**: (auto-filled)
   - **Protocol**: `Amazon SQS`
   - **Endpoint**: Paste `QUEUE_ARN`
5. Click **Create subscription**

**Via CLI:**
```bash
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol sqs \
  --notification-endpoint $QUEUE_ARN \
  --region us-east-1
```

✅ Now messages published to SNS automatically go to SQS!

---

### Step 5: Create Lambda Function

**Via Console:**
1. Go to **Lambda** → **Functions**
2. Click **Create function**
3. Fill in:
   - **Function name**: `user-events-processor`
   - **Runtime**: Python 3.12
   - **Execution role**: Create new role with basic Lambda permissions
4. Click **Create function**

**Via CLI:**
```bash
aws lambda create-function \
  --function-name user-events-processor \
  --runtime python3.12 \
  --role arn:aws:iam::088971275490:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_code.zip \
  --region us-east-1
```

---

### Step 6: Add Code to Lambda

Use the **handler.py** and **lambda_function.py** pattern from our codebase.

**File structure:**
```
onboarding_service/onboarding/
├── lambda_function.py       ← Entry point
├── handler.py              ← Event handlers (with @registry.register_queue_event)
├── registry.py             ← Handler registry
└── dependencies.py         ← ServiceContainer DI
```

**lambda_function.py:**
```python
import json
from . import logger
from . import handler  # triggers decorator registration
from .registry import registry

def lambda_handler(event, context):
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            message = json.loads(body["Message"]) if "Message" in body else body
            event_type = message.get("event_type", "")
            
            handler_fn = registry.get_queue_handler(event_type)
            if handler_fn:
                handler_fn(message)
        except Exception:
            logger.exception("Failed to process record")
            raise
```

---

### Step 7: Configure SQS as Lambda Trigger

**Via Console:**
1. Open Lambda function
2. Click **Configuration** tab
3. Click **Add trigger** (left sidebar)
4. Select **SQS**
5. Fill in:
   - **SQS queue**: `user-events-queue`
   - **Batch size**: `10`
   - **Batch window**: `5`
6. Click **Add**

**Via CLI:**
```bash
aws lambda create-event-source-mapping \
  --event-source-arn arn:aws:sqs:us-east-1:088971275490:user-events-queue \
  --function-name user-events-processor \
  --batch-size 10 \
  --region us-east-1
```

✅ Lambda now processes SQS messages automatically!

---

### Step 8: Grant Lambda SQS Permissions

Make sure Lambda IAM role has permissions to read from SQS.

**Attach policy to role:**
```bash
aws iam attach-role-policy \
  --role-name lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole
```

---

## Code Patterns

### Event Publisher (in onboarding_service)

**domain_events.py** — Define events as dataclasses:
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class UserCreated:
    user_id: str
    email: str
    first_name: str
    
    @property
    def event_type(self) -> str:
        return self.__class__.__name__  # Returns "UserCreated"
```

**event_publisher.py** — Publish events:
```python
from helper.event_publisher import EventPublisher

publisher = EventPublisher(sns_client, topic_arn)
event = UserCreated(user_id="123", email="alice@example.com", first_name="Alice")
publisher.publish(event)
```

**Published to SNS as flat JSON:**
```json
{
  "event_type": "UserCreated",
  "event_id": "uuid-1234",
  "occurred_at": "2024-06-16T12:00:00Z",
  "user_id": "123",
  "email": "alice@example.com",
  "first_name": "Alice"
}
```

---

### Event Consumer (in email_service or onboarding_service)

**registry.py** — Handler registry:
```python
class ModuleRegistry:
    def register_queue_event(self, event_type: str):
        def decorator(fn):
            self._queue_handlers[event_type] = fn
            return fn
        return decorator

registry = ModuleRegistry()
```

**handler.py** — Register handlers via decorators:
```python
@registry.register_queue_event("UserCreated")
def handle_user_created(data: dict) -> None:
    user_id = data.get("user_id")
    email = data.get("email")
    # Send welcome email...

@registry.register_queue_event("UserVerified")
def handle_user_verified(data: dict) -> None:
    user_id = data.get("user_id")
    # Send verification email...
```

**lambda_function.py** — Dispatch via registry:
```python
import handler  # triggers @registry.register_queue_event decorators

def lambda_handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        message = json.loads(body["Message"]) if "Message" in body else body
        event_type = message.get("event_type")
        
        handler_fn = registry.get_queue_handler(event_type)
        if handler_fn:
            handler_fn(message)  # Call the registered handler
```

---

## Deployment

### Package Code

```bash
cd /path/to/project

# Create ZIP with code
zip -r lambda_package.zip \
  services/onboarding_service/onboarding \
  services/email_service \
  helper \
  -x "*.pyc" "*.pycache/*" "tests/*"
```

### Deploy to Lambda

```bash
# Deploy onboarding service
aws lambda update-function-code \
  --function-name user-events-processor \
  --zip-file fileb://lambda_package.zip \
  --region us-east-1

# Deploy email service
aws lambda update-function-code \
  --function-name email-events-processor \
  --zip-file fileb://lambda_package.zip \
  --region us-east-1
```

### Test End-to-End

**1. Publish test event:**
```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:088971275490:user-events \
  --message '{
    "event_type": "UserCreated",
    "event_id": "test-123",
    "occurred_at": "2024-06-16T12:00:00Z",
    "user_id": "user-123",
    "email": "alice@example.com",
    "first_name": "Alice"
  }' \
  --region us-east-1
```

**2. Check SQS queue:**
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/088971275490/user-events-queue \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

**3. Check Lambda logs:**
```bash
aws logs tail /aws/lambda/user-events-processor --follow --region us-east-1
```

---

## Reference Implementation

Our implementation follows the `bonus_platform_service` architecture from the reference repo:

### File Structure

```
services/onboarding_service/onboarding/
├── lambda_function.py          ← Entry point (thin)
├── handler.py                  ← Event handlers with @registry decorators
├── registry.py                 ← Handler registry (decorator pattern)
├── dependencies.py             ← ServiceContainer (lazy initialization)
├── __init__.py                 ← Exports logger
└── v1/
    ├── services/               ← Business logic
    ├── repositories/           ← Data access
    └── controllers/            ← HTTP endpoints

services/email_service/
├── lambda_function.py          ← Same pattern
├── handler.py                  ← @registry.register_queue_event decorators
├── registry.py                 ← Same as onboarding
├── dependencies.py             ← ServiceContainer
└── use_cases/                  ← Email sending logic
    ├── send_welcome_email.py
    └── send_verification_email.py

helper/
├── event_publisher.py          ← Publish flat domain events
├── domain_events.py            ← Event dataclasses
└── utilities.py                ← get_logger, etc.
```

### Key Patterns

1. **Thin entry point** — `lambda_function.py` is 5-10 lines
2. **Handler registry** — `@registry.register_queue_event("EventType")`
3. **Lazy DI** — `ServiceContainer` with `get_*()` methods
4. **Flat events** — No nested `data` wrapper
5. **PascalCase event types** — `"UserCreated"` not `"user.created"`
6. **SNS envelope unwrap** — Check for `body["Message"]`
7. **Error handling** — `raise` on failure → SQS retries

---

## Troubleshooting

### Messages Not Arriving in SQS

1. Check SNS topic exists
2. Verify SQS queue policy allows SNS to send
3. Check subscription exists and is confirmed
4. Verify subscription filter policy (if set)

### Lambda Not Triggered

1. Verify SQS is configured as Lambda trigger
2. Check Lambda IAM role has `AWSLambdaSQSQueueExecutionRole`
3. Verify event source mapping is enabled

### Messages Processing Slowly

1. Increase batch size (up to 10)
2. Increase batch window (up to 300 seconds)
3. Increase Lambda concurrency

### Messages Lost

1. Check visibility timeout (Lambda timeout must be less)
2. Increase message retention period (default 4 days)
3. Consider Dead Letter Queue for failed messages

---

## Next Steps

1. **Add monitoring** — CloudWatch alarms for queue depth, Lambda errors
2. **Set up CI/CD** — GitHub Actions to auto-deploy on git push
3. **Add tests** — Unit + integration tests for handlers
4. **Configure DLQ** — Dead Letter Queue for permanently failed messages
5. **Add more events** — UserDeleted, UserUpdated, etc.

---

## Related Files

- `services/onboarding_service/onboarding/` — Full reference implementation
- `services/email_service/` — Email consumer example
- `helper/event_publisher.py` — Publishing logic
- `helper/domain_events.py` — Event definitions
