# AWS SNS, SQS, Lambda - Quick Commands

Copy-paste reference for common operations.

## Setup

### Create SNS Topic
```bash
aws sns create-topic --name user-events --region us-east-1
```

### Create SQS Queue
```bash
aws sqs create-queue \
  --queue-name user-events-queue \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=1209600 \
  --region us-east-1
```

### Set Queue Policy (allow SNS to send)
```bash
TOPIC_ARN="arn:aws:sns:us-east-1:ACCOUNT:user-events"
QUEUE_ARN="arn:aws:sqs:us-east-1:ACCOUNT:user-events-queue"

aws sqs set-queue-attributes \
  --queue-url "https://sqs.us-east-1.amazonaws.com/ACCOUNT/user-events-queue" \
  --attributes '{
    "Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"sns.amazonaws.com\"},\"Action\":\"sqs:SendMessage\",\"Resource\":\"'$QUEUE_ARN'\",\"Condition\":{\"ArnEquals\":{\"aws:SourceArn\":\"'$TOPIC_ARN'\"}}}]}"
  }' \
  --region us-east-1
```

### Subscribe Queue to Topic
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:user-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:ACCOUNT:user-events-queue \
  --region us-east-1
```

### Create Lambda Function
```bash
aws lambda create-function \
  --function-name user-events-processor \
  --runtime python3.12 \
  --role arn:aws:iam::ACCOUNT:role/lambda-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda.zip \
  --region us-east-1
```

### Add SQS Trigger to Lambda
```bash
aws lambda create-event-source-mapping \
  --event-source-arn arn:aws:sqs:us-east-1:ACCOUNT:user-events-queue \
  --function-name user-events-processor \
  --batch-size 10 \
  --region us-east-1
```

### Grant Lambda SQS Permissions
```bash
aws iam attach-role-policy \
  --role-name lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole
```

---

## Operations

### Publish Test Message
```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:user-events \
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

### Check Queue Messages
```bash
aws sqs get-queue-attributes \
  --queue-url "https://sqs.us-east-1.amazonaws.com/ACCOUNT/user-events-queue" \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1
```

### Receive Message from Queue
```bash
aws sqs receive-message \
  --queue-url "https://sqs.us-east-1.amazonaws.com/ACCOUNT/user-events-queue" \
  --region us-east-1
```

### Check Lambda Logs
```bash
aws logs tail /aws/lambda/user-events-processor --follow --region us-east-1
```

### View Lambda Configuration
```bash
aws lambda get-function-configuration \
  --function-name user-events-processor \
  --region us-east-1
```

### List Event Source Mappings
```bash
aws lambda list-event-source-mappings \
  --function-name user-events-processor \
  --region us-east-1
```

---

## Deployment

### Package Code
```bash
zip -r lambda.zip \
  services/onboarding_service \
  services/email_service \
  helper \
  -x "*.pyc" "*.pycache/*" "tests/*"
```

### Deploy to Lambda
```bash
aws lambda update-function-code \
  --function-name user-events-processor \
  --zip-file fileb://lambda.zip \
  --region us-east-1
```

### Update Function Configuration
```bash
aws lambda update-function-configuration \
  --function-name user-events-processor \
  --timeout 300 \
  --memory-size 512 \
  --region us-east-1
```

---

## Cleanup

### Delete Queue
```bash
aws sqs delete-queue \
  --queue-url "https://sqs.us-east-1.amazonaws.com/ACCOUNT/user-events-queue" \
  --region us-east-1
```

### Delete Topic
```bash
aws sns delete-topic \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:user-events \
  --region us-east-1
```

### Delete Lambda Function
```bash
aws lambda delete-function \
  --function-name user-events-processor \
  --region us-east-1
```

---

## Batch Operations

### Deploy All Services
```bash
# Package
zip -r lambda.zip services/ helper -x "*.pyc" "*.pycache/*"

# Deploy onboarding
aws lambda update-function-code \
  --function-name onboarding-events-processor \
  --zip-file fileb://lambda.zip

# Deploy email
aws lambda update-function-code \
  --function-name email-events-processor \
  --zip-file fileb://lambda.zip
```

### Monitor All Logs
```bash
# In separate terminals
aws logs tail /aws/lambda/onboarding-events-processor --follow
aws logs tail /aws/lambda/email-events-processor --follow
aws logs tail /aws/lambda/fraud-events-processor --follow
```

---

## Replace These

- `ACCOUNT` → Your AWS Account ID (e.g., `088971275490`)
- `user-events-queue` → Your queue name
- `user-events-processor` → Your Lambda function name
- `user-east-1` → Your AWS region
