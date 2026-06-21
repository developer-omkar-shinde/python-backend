#!/usr/bin/env bash
# Provision the EventBridge demo: custom bus -> rules -> SQS queues.
#
# This is the "rules between publisher and subscriber" layer. The publisher
# (onboarding service) just calls put_events; these rules decide which SQS
# queue each event lands in, based on source / detail-type / detail fields.
#
# Idempotent: safe to re-run. Requires AWS CLI configured with admin rights.
#
# Topology created:
#   bus:   trivelta-events
#   rule:  onboarding-signups   (detail-type = user.signed_up)        -> welcome-email-queue
#   rule:  onboarding-kyc-gh     (detail-type = kyc.approved, country=GH) -> compliance-queue
#   rule:  onboarding-all        (source = onboarding.service)        -> analytics-queue
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
BUS_NAME="trivelta-events"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

echo "Account=$ACCOUNT_ID Region=$REGION Bus=$BUS_NAME"

# 1. Custom event bus -------------------------------------------------------
echo "==> Creating event bus: $BUS_NAME"
aws events create-event-bus --name "$BUS_NAME" --region "$REGION" >/dev/null 2>&1 \
  && echo "   created" || echo "   already exists"

# Helper: create an SQS queue and return its URL + ARN.
create_queue() {
  local qname="$1"
  local qurl qarn
  qurl="$(aws sqs create-queue --queue-name "$qname" --region "$REGION" \
            --query QueueUrl --output text)"
  qarn="$(aws sqs get-queue-attributes --queue-url "$qurl" \
            --attribute-names QueueArn --region "$REGION" \
            --query 'Attributes.QueueArn' --output text)"
  echo "$qurl|$qarn"
}

# Helper: allow EventBridge to send messages to a queue (queue access policy).
allow_eventbridge_to_send() {
  local qurl="$1" qarn="$2" rule_arn="$3"
  local policy
  policy=$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "events.amazonaws.com"},
    "Action": "sqs:SendMessage",
    "Resource": "$qarn",
    "Condition": {"ArnEquals": {"aws:SourceArn": "$rule_arn"}}
  }]
}
JSON
)
  aws sqs set-queue-attributes --queue-url "$qurl" --region "$REGION" \
    --attributes "{\"Policy\":$(printf '%s' "$policy" | jq -Rs .)}" >/dev/null
}

# Helper: create a rule on the bus + attach an SQS target.
create_rule_with_target() {
  local rule_name="$1" pattern="$2" qurl="$3" qarn="$4"
  local rule_arn
  rule_arn="$(aws events put-rule --name "$rule_name" --event-bus-name "$BUS_NAME" \
                --event-pattern "$pattern" --region "$REGION" \
                --query RuleArn --output text)"
  allow_eventbridge_to_send "$qurl" "$qarn" "$rule_arn"
  aws events put-targets --rule "$rule_name" --event-bus-name "$BUS_NAME" \
    --region "$REGION" \
    --targets "Id=1,Arn=$qarn" >/dev/null
  echo "   rule $rule_name -> $qarn"
}

# 2. Queues -----------------------------------------------------------------
echo "==> Creating SQS queues"
IFS='|' read -r WELCOME_URL WELCOME_ARN < <(create_queue "welcome-email-queue")
IFS='|' read -r COMPLIANCE_URL COMPLIANCE_ARN < <(create_queue "compliance-queue")
IFS='|' read -r ANALYTICS_URL ANALYTICS_ARN < <(create_queue "analytics-queue")
echo "   welcome:    $WELCOME_ARN"
echo "   compliance: $COMPLIANCE_ARN"
echo "   analytics:  $ANALYTICS_ARN"

# 3. Rules ------------------------------------------------------------------
echo "==> Creating rules + targets"

# Rule 1: only user.signed_up events -> welcome email queue
create_rule_with_target "onboarding-signups" \
  '{"source":["onboarding.service"],"detail-type":["user.signed_up"]}' \
  "$WELCOME_URL" "$WELCOME_ARN"

# Rule 2: kyc.approved AND country == GH -> compliance queue (content filtering!)
create_rule_with_target "onboarding-kyc-gh" \
  '{"source":["onboarding.service"],"detail-type":["kyc.approved"],"detail":{"country":["GH"]}}' \
  "$COMPLIANCE_URL" "$COMPLIANCE_ARN"

# Rule 3: every event from onboarding.service -> analytics queue (catch-all)
create_rule_with_target "onboarding-all" \
  '{"source":["onboarding.service"]}' \
  "$ANALYTICS_URL" "$ANALYTICS_ARN"

echo ""
echo "Done. Try publishing an event:"
echo "  python3 scripts/publish_demo_event.py user.signed_up"
echo ""
echo "Then read a queue (e.g. analytics):"
echo "  aws sqs receive-message --queue-url $ANALYTICS_URL --region $REGION"
