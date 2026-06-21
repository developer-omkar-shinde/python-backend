# AWS EventBridge — Content-Based Event Routing

EventBridge is an event bus with a **rules engine** in the middle. A publisher
emits an event once; rules decide which targets (SQS queues, Lambdas, etc.)
receive it — based on the event's `source`, `detail-type`, **and fields inside
`detail`**. That content filtering is the main thing SNS can't do well.

This guide documents the working implementation in this repo, verified against
real AWS (account `088971275490`, region `us-east-1`).

---

## SNS vs EventBridge (when to use which)

| | SNS (+ SQS) | EventBridge |
|---|---|---|
| Model | Topic broadcast / fan-out | Bus + rules engine |
| Filtering | Basic message-attribute filters | Full content filtering on `detail` |
| Routing | Subscriber gets everything on the topic | Rules route per event content |
| Scheduling | No | Yes (cron / rate rules) |
| SaaS / AWS source events | No | Yes (S3, CodePipeline, partners…) |
| Best for | "Notify everyone interested" | "Route this specific event to the right place" |

Rule of thumb: **SNS+SQS for simple fan-out, EventBridge when the middle layer
must decide where an event goes.**

---

## Architecture in this repo

```
Onboarding service (publisher)
    │  publish_business_event(UserSignedUp(...))
    ▼
EventBridge bus: trivelta-events
    │  rules match source / detail-type / detail
    ├── user.signed_up                 ──▶ welcome-email-queue
    ├── kyc.approved AND country == GH  ──▶ compliance-queue
    └── source == onboarding.service    ──▶ analytics-queue   (catch-all)
                                              │ SQS triggers Lambda
                                              ▼
                                   onboarding consumer Lambda
                                   unwrap envelope → dispatch by detail-type
                                   → batchItemFailures (partial retry)
```

This mirrors `bonus_platform_service/bonus_service_v2` in the reference repo,
where EventBridge events are delivered **through SQS** (rule → SQS target) for
durability and retries, then unwrapped by the consumer.

---

## Files

| File | Role |
|------|------|
| `helper/eventbridge_client.py` | Lazy-init boto3 `events` client |
| `helper/business_events.py` | Typed `BusinessEvent` dataclasses (`UserSignedUp`, `KycApproved`, …) |
| `helper/business_event_publisher.py` | `publish_business_event()` → `put_events` |
| `services/onboarding_service/onboarding/eventbridge_handler.py` | Unwrap envelope, dispatch by `detail-type`, return `batchItemFailures` |
| `services/onboarding_service/onboarding/registry.py` | `register_eventbridge_event(detail_type)` |
| `services/onboarding_service/onboarding/lambda_function.py` | Router: EventBridge-wrapped vs SNS/SQS domain events |
| `scripts/setup_eventbridge.sh` | Create bus + queues + rules (idempotent) |
| `scripts/publish_demo_event.py` | Publish a demo event to the bus |

---

## The event shape

A published event has three routing-relevant parts:

```json
{
  "source":      "onboarding.service",
  "detail-type": "kyc.approved",
  "detail":      { "user_id": "u1", "country": "GH", "tier": "gold" }
}
```

EventBridge then wraps it with metadata before delivery. This is what a
consumer actually receives in the SQS body:

```json
{
  "version": "0",
  "id": "05cdb99b-...",
  "detail-type": "kyc.approved",
  "source": "onboarding.service",
  "account": "088971275490",
  "time": "2026-06-21T15:24:16Z",
  "region": "us-east-1",
  "resources": [],
  "detail": { "event_id": "...", "user_id": "u1", "country": "GH", "tier": "gold" }
}
```

The consumer reads `detail-type` (to pick a handler) and `detail` (the payload).

---

## Publishing (the producer side)

```python
from helper.business_events import UserSignedUp
from helper.business_event_publisher import publish_business_event

publish_business_event(
    UserSignedUp(user_id="u1", email="a@b.com", first_name="Omkar", country="GH")
)
```

`publish_business_event` returns `True`/`False` instead of raising, so a publish
failure never breaks the caller's main flow (it logs for alerting). Under the
hood it calls:

```python
events.put_events(Entries=[{
    "Source":       event.source,        # "onboarding.service"
    "DetailType":   event.detail_type,   # "user.signed_up"
    "Detail":       json.dumps(event.detail()),
    "EventBusName": "trivelta-events",
}])
```

---

## Rules (the routing layer)

Rules are defined in `scripts/setup_eventbridge.sh`. An **event pattern** is a
JSON match document; arrays mean "any of these values".

```jsonc
// Rule 1 — only sign-ups
{"source":["onboarding.service"],"detail-type":["user.signed_up"]}

// Rule 2 — KYC approvals, but ONLY for Ghana (content filter on detail)
{"source":["onboarding.service"],"detail-type":["kyc.approved"],"detail":{"country":["GH"]}}

// Rule 3 — everything from onboarding (catch-all, e.g. analytics)
{"source":["onboarding.service"]}
```

Each rule has an SQS target, plus a queue access policy allowing
`events.amazonaws.com` to `sqs:SendMessage` (scoped to that rule's ARN).

---

## Consuming (the subscriber side)

Handlers register by `detail-type`:

```python
@registry.register_eventbridge_event("user.signed_up")
def on_user_signed_up(detail: dict) -> None:
    ...
```

The Lambda entry point (`lambda_function.py`) inspects the first record's shape
and routes the batch:

- EventBridge envelope (`detail-type` + `detail`) → `dispatch_eventbridge_records`
  (returns `batchItemFailures` so only failed records are retried).
- SNS-wrapped domain event (`Message` → flat `event_type`) → queue-handler registry.

---

## Verified routing result

Publishing 3 events:

```bash
python3 scripts/publish_demo_event.py user.signed_up
python3 scripts/publish_demo_event.py kyc.approved --country GH
python3 scripts/publish_demo_event.py kyc.approved --country NG
```

Landed as:

| Queue | Rule | Messages | Why |
|-------|------|----------|-----|
| `welcome-email-queue` | `detail-type = user.signed_up` | 1 | only the signup |
| `compliance-queue` | `kyc.approved` AND `country = GH` | 1 | **NG was filtered out** |
| `analytics-queue` | `source = onboarding.service` | 3 | all events |

The NG `kyc.approved` event never reached compliance — that is content-based
routing in action.

---

## Try it yourself

```bash
# 1. Create bus + queues + rules (idempotent, needs admin AWS creds)
bash scripts/setup_eventbridge.sh

# 2. Publish events
python3 scripts/publish_demo_event.py user.signed_up
python3 scripts/publish_demo_event.py kyc.approved --country GH
python3 scripts/publish_demo_event.py kyc.approved --country NG

# 3. Inspect routing
for q in welcome-email-queue compliance-queue analytics-queue; do
  url="https://sqs.us-east-1.amazonaws.com/088971275490/$q"
  cnt=$(aws sqs get-queue-attributes --queue-url "$url" \
        --attribute-names ApproximateNumberOfMessages \
        --query 'Attributes.ApproximateNumberOfMessages' --output text)
  echo "$q: $cnt"
done

# 4. Peek at an envelope
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/088971275490/compliance-queue \
  --query 'Messages[0].Body' --output text | python3 -m json.tool
```

---

## Production notes

- **Delivery path:** prefer rule → SQS → Lambda (durable, retries, DLQ, partial
  batch) over rule → Lambda direct. This repo uses the SQS path.
- **Schema discovery:** EventBridge Schema Registry can infer schemas from events
  and generate typed bindings.
- **Archive & replay:** a bus can archive events and replay them to targets —
  useful for backfills and debugging.
- **DLQ:** attach a dead-letter queue to each rule target for events that fail
  delivery to the target.
- **IaC:** in production these buses/rules/queues live in Terraform
  (`tf-eventbridge-setup` in the reference org), not a shell script. The script
  here is for learning.

---

## Teardown (remove demo resources)

```bash
BUS=trivelta-events; REGION=us-east-1
for r in onboarding-signups onboarding-kyc-gh onboarding-all; do
  aws events remove-targets --rule "$r" --event-bus-name "$BUS" --ids 1 --region $REGION
  aws events delete-rule --name "$r" --event-bus-name "$BUS" --region $REGION
done
aws events delete-event-bus --name "$BUS" --region $REGION
for q in welcome-email-queue compliance-queue analytics-queue; do
  aws sqs delete-queue --queue-url "https://sqs.$REGION.amazonaws.com/088971275490/$q" --region $REGION
done
```
