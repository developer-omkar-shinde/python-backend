# Email Service Structure - Following Reference Repo Pattern

## New Structure (Correct)

```
services/
├── onboarding_service/
│   └── onboarding/
│       ├── main.py                 ← EKS entry
│       ├── lambda_function.py      ← Lambda entry
│       └── v1/
│           ├── controllers/
│           ├── services/
│           ├── repositories/
│           └── ...
│
└── email_service/                  ← NEW: Separate Lambda service
    ├── lambda_function.py          ← AWS entry point (thin)
    ├── handler.py                  ← Event adapter layer
    ├── dependencies.py             ← DI container
    ├── schemas.py                  ← Pydantic models
    ├── use_cases/                  ← Business logic
    │   ├── send_welcome_email.py
    │   └── send_verification_email.py
    ├── adapters/                   ← Infrastructure adapters
    │   └── email_adapter.py        ← SES + DynamoDB
    ├── requirements.txt
    └── __init__.py

helper/                             ← Shared (no email code here!)
├── event_publisher.py              ← SNS adapter (shared)
├── domain_events.py                ← Domain events (shared)
├── utilities.py
└── ...
```

## Layer Explanation

### 1. `lambda_function.py` (AWS Entry Point)

**Role**: Thin wrapper — just imports and delegates

```python
from email_service.handler import lambda_handler

__all__ = ["lambda_handler"]
```

**Deployed as**: `email_service.lambda_function.lambda_handler`

### 2. `handler.py` (Event Adapter)

**Role**: Parse AWS/SQS/SNS events, route to use cases

```python
def lambda_handler(event, context):
    """Handle SQS records containing SNS events."""
    for record in event.get("Records", []):
        event_type = extract_event_type(record)
        
        if event_type == "UserCreated":
            send_welcome_email(...)  # Call use case
        elif event_type == "UserVerified":
            send_verification_email(...)  # Call use case
```

**Key Points**:
- Stays thin (no business logic)
- Knows about AWS event shapes
- Routes to use cases
- Handles errors gracefully

### 3. `use_cases/` (Business Logic)

**Role**: Pure functions — no AWS types

```python
# use_cases/send_welcome_email.py
def send_welcome_email(
    user_id: str,
    email_service: EmailAdapter,  # ← Injected
    first_name: str,
    last_name: str,
) -> dict:
    """Send welcome email."""
    return email_service.send_welcome_email(...)
```

**Benefits**:
- Testable without AWS
- Reusable (could be called from EKS)
- Pure functions (no side effects)
- Easy to understand

### 4. `adapters/` (Infrastructure)

**Role**: AWS clients (SES, DynamoDB)

```python
# adapters/email_adapter.py
class EmailAdapter:
    def __init__(self, ses_client, ddb_resource):
        self.ses_client = ses_client
        self.ddb_resource = ddb_resource
    
    def send_welcome_email(self, ...):
        # Calls SES API
        # Logs to DynamoDB
```

### 5. `dependencies.py` (DI Container)

**Role**: Wires all layers at startup

```python
class ServiceContainer:
    def _init_infrastructure(self):
        ses_client = boto3.client("ses")
        self._email_adapter = EmailAdapter(ses_client=ses_client)
    
    def get_email_service(self):
        return self._email_adapter

container = ServiceContainer()
```

### 6. `schemas.py` (Pydantic Models)

**Role**: Type validation, documentation

```python
class SendEmailRequest(BaseModel):
    user_id: str
    email: EmailStr
    template: str
    data: dict = {}
```

---

## Comparison: Before vs After

### ❌ BEFORE (Incorrect)

```
helper/
├── event_publisher.py
├── domain_events.py
└── email_service.py  ← ❌ Lambda logic in helper!
    └── lambda_handler() buried in helper
```

**Problems**:
- Lambda code mixed with shared utilities
- Can't deploy separately
- Helper grows too large
- Hard to version control

### ✅ AFTER (Correct)

```
services/email_service/
├── lambda_function.py              ← Clear AWS entry
├── handler.py                      ← Event adapter
├── use_cases/send_welcome_email.py ← Business logic
└── adapters/email_adapter.py       ← Infrastructure

helper/
├── event_publisher.py              ← SNS (shared)
├── domain_events.py                ← Events (shared)
└── utilities.py                    ← Utils (shared)
```

**Benefits**:
- Clear separation
- Can deploy independently
- Easy to find code
- Follows reference pattern

---

## Data Flow

```
AWS SQS Event
    ↓
lambda_function.py (entry)
    ↓
handler.py (adapter)
    ├─ Parses SNS message from SQS record
    ├─ Extracts event type
    └─ Routes to appropriate use case
    ↓
use_cases/send_welcome_email.py
    ├─ Pure business logic
    └─ Calls email_adapter
    ↓
adapters/email_adapter.py
    ├─ Calls SES API
    └─ Logs to DynamoDB
    ↓
Response back through handler
    ↓
AWS Lambda returns {statusCode: 200, body: ...}
```

---

## Testing Strategy

### Test Use Case (No AWS)

```python
def test_send_welcome_email():
    # Mock adapter
    mock_adapter = MockEmailAdapter()
    
    # Call use case
    result = send_welcome_email(
        user_id="123",
        email_service=mock_adapter,
        first_name="Alice",
        last_name="Smith"
    )
    
    # Assert
    assert result["success"] == True
    assert mock_adapter.sent_emails["welcome"] == 1
```

### Test Handler (With Fixtures)

```python
def test_handler_parses_user_created():
    event = {
        "Records": [
            {
                "Body": json.dumps({
                    "Message": json.dumps({
                        "event_type": "UserCreated",
                        "aggregate_id": "user_123",
                        "data": {"first_name": "Alice", ...}
                    })
                })
            }
        ]
    }
    
    result = lambda_handler(event, None)
    assert result["statusCode"] == 200
    assert "processed" in json.loads(result["body"])
```

---

## Deployment

### serverless.yml (Future)

```yaml
service: email-service

provider:
  name: aws
  runtime: python3.11
  region: us-east-1

functions:
  process_email_events:
    handler: email_service.lambda_function.lambda_handler
    events:
      - sqs:
          arn: arn:aws:sqs:us-east-1:123456789:email-service-queue
          batchSize: 10
```

---

## Next Steps

1. ✅ Create `services/email_service/` with this structure
2. ✅ Move Lambda code out of `helper/`
3. ✅ Keep `helper/event_publisher.py` and `helper/domain_events.py` (shared)
4. Create similar structure for `feature_service`
5. Create similar structure for `analytics_service`

---

## Key Takeaway

**Reference pattern**:
```
lambda_function.py (thin entry)
    ↓
handler.py (adapter)
    ↓
use_cases/ (business logic)
    ↓
adapters/ (infrastructure)
```

This matches **bonus_platform_service** and **onboarding_service** patterns! 🚀
