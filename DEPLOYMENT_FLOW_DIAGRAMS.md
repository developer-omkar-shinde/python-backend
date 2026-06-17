# Lambda Auto-Deployment Visual Guide

## Complete Deployment Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER'S WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  1. Local Development                                                    │
│     $ git clone ...                                                      │
│     $ code services/onboarding_service/                                  │
│     $ python3 -m pytest tests/                           (optional)      │
│     $ git add .                                                          │
│     $ git commit -m "fix: improve user creation logic"                   │
│     $ git push origin main                                              │
│                                                                           │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          │ Push event
                          │
┌─────────────────────────▼───────────────────────────────────────────────┐
│                    GITHUB ACTIONS WORKFLOW                              │
│                  .github/workflows/deploy-lambda.yml                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Job 1: detect-changes                                                  │
│  ┌──────────────────────────────────────────────────────┐               │
│  │ git diff HEAD~1 HEAD --name-only                     │               │
│  │                                                       │               │
│  │ Result:                                               │               │
│  │   services/onboarding_service/onboarding/v1/...py   │               │
│  │   services/onboarding_service/onboarding/lambda...py │               │
│  │                                                       │               │
│  │ Decision:                                             │               │
│  │   ✅ onboarding_lambda_changed = true               │               │
│  │   ❌ email_lambda_changed = false                   │               │
│  └──────────────────────────────────────────────────────┘               │
│                                                                           │
│                        │                                                │
│       ┌────────────────┴─────────────────┐                             │
│       │                                  │                             │
│       ▼ (if changed)                ▼ (if not changed)                │
│  ┌──────────────────┐           ┌─────────────────┐                  │
│  │ Job 2a: RUNS     │           │ Job 2b: SKIPPED │                  │
│  │ build-onboarding │           │ build-email     │                  │
│  │ -lambda          │           │                 │                  │
│  └────────┬─────────┘           └─────────────────┘                  │
│           │                                                           │
│           ▼                                                           │
│  ┌──────────────────────────────────────┐                            │
│  │ Build Onboarding Lambda Package      │                            │
│  │                                      │                            │
│  │ Step 1: Copy source code             │                            │
│  │   cp -r helper/ lambda-build/        │                            │
│  │   cp -r services/onboarding_* ...    │                            │
│  │                                      │                            │
│  │ Step 2: Install dependencies         │                            │
│  │   pip install -r requirements.txt -t . (750+ files)               │
│  │   → boto3 (~500 files)               │                            │
│  │   → pydantic (~150 files)            │                            │
│  │   → others (~100 files)              │                            │
│  │                                      │                            │
│  │ Step 3: Create ZIP                   │                            │
│  │   zip -r onboarding-lambda.zip .     │                            │
│  │   (Final size: ~25-50 MB)            │                            │
│  │                                      │                            │
│  │ Step 4: Upload to GitHub             │                            │
│  │   uses: actions/upload-artifact      │                            │
│  │   name: onboarding-lambda-package    │                            │
│  └────────┬─────────────────────────────┘                            │
│           │                                                           │
│           └──────────────────┐                                       │
│                              │ artifact ready                        │
│                              ▼                                       │
│  ┌──────────────────────────────────────┐                            │
│  │ Job 3: deploy-onboarding-lambda      │                            │
│  │                                      │                            │
│  │ Step 1: Download artifact            │                            │
│  │   uses: actions/download-artifact    │                            │
│  │                                      │                            │
│  │ Step 2: Configure AWS credentials    │                            │
│  │   AWS_ACCESS_KEY_ID: ${{ secrets.X }} │                           │
│  │   AWS_SECRET_ACCESS_KEY: ${{ ...}}   │                            │
│  │                                      │                            │
│  │ Step 3: Update Lambda                │                            │
│  │   aws lambda update-function-code \  │                            │
│  │     --function-name dev-onboarding \ │                            │
│  │     --zip-file fileb://...zip        │                            │
│  │                                      │                            │
│  │ Step 4: Wait for completion          │                            │
│  │   aws lambda wait function-updated   │                            │
│  │                                      │                            │
│  │ Result: ✅ DEPLOYED                  │                            │
│  └──────────────────────────────────────┘                            │
│                                                                           │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          │ API calls
                          │
┌─────────────────────────▼───────────────────────────────────────────────┐
│                           AWS CLOUD                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  AWS Lambda: dev-onboarding                                             │
│  ┌────────────────────────────────────────────────────────┐             │
│  │ Function: dev-onboarding                               │             │
│  │ Runtime: Python 3.11                                   │             │
│  │ Handler: lambda_function.lambda_handler                │             │
│  │ Memory: 512 MB                                         │             │
│  │ Timeout: 300 seconds                                   │             │
│  │                                                         │             │
│  │ Execution Role: lambda-execution-role                  │             │
│  │   Policies:                                             │             │
│  │   - CloudWatch Logs (write)                            │             │
│  │   - SQS (receive messages)                             │             │
│  │   - SNS (publish events)                               │             │
│  │   - DynamoDB (read/write test_users)                   │             │
│  │                                                         │             │
│  │ Environment Variables:                                 │             │
│  │   STAGE: dev                                           │             │
│  │   LOG_LEVEL: INFO                                      │             │
│  │                                                         │             │
│  │ Function Code:                                          │             │
│  │   ✅ UPDATED (just deployed!)                          │             │
│  │   Event Source: SQS queue (email-events)               │             │
│  │   Status: Active & Ready                               │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                           │
│  CloudWatch Logs: /aws/lambda/dev-onboarding                            │
│  ┌────────────────────────────────────────────────────────┐             │
│  │ [2026-06-18 01:15:32] Lambda deployed successfully     │             │
│  │ [2026-06-18 01:15:45] Received SQS event              │             │
│  │ [2026-06-18 01:15:46] Processing user.created event   │             │
│  │ [2026-06-18 01:15:47] User 123 onboarded successfully │             │
│  └────────────────────────────────────────────────────────┘             │
│                                                                           │
│  SQS Queues (Event Sources)                                             │
│  ├── email-events                                                       │
│  │   └── Connected to: Lambda dev-onboarding (trigger)                 │
│  ├── onboarding-events                                                  │
│  │   └── Connected to: Lambda dev-email-service (trigger)              │
│  └── ...                                                                │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## File Structure Visualization

```
project/
│
├── .github/
│   └── workflows/
│       └── deploy-lambda.yml                           ✅ Main workflow
│           ├── trigger: push to main + path filter
│           ├── detect-changes job
│           ├── build-onboarding-lambda job
│           ├── build-email-lambda job
│           ├── deploy-onboarding-lambda job
│           └── deploy-email-lambda job
│
├── lambda-config.json                                  ✅ Configuration
│   ├── lambdas.onboarding.function_name
│   ├── lambdas.email.function_name
│   └── build_config
│
├── scripts/
│   └── setup_lambda_deployment.py                      ✅ Setup helper
│       ├── check_aws_cli()
│       ├── create_iam_user()
│       ├── create_lambda_function()
│       └── verify_lambda_configs()
│
├── services/
│   │
│   ├── onboarding_service/                             ✅ Lambda service 1
│   │   └── onboarding/
│   │       ├── lambda_function.py                      ← AWS entry point
│   │       ├── handler.py                              ← Event handler
│   │       ├── registry.py                             ← Route handlers
│   │       ├── v1/
│   │       │   ├── controllers/
│   │       │   ├── services/
│   │       │   ├── repositories/
│   │       │   ├── domain/
│   │       │   ├── schemas/
│   │       │   └── dependencies.py
│   │       ├── main.py                                 (unused in Lambda)
│   │       └── requirements.txt                        ← Installed in ZIP
│   │
│   └── email_service/                                  ✅ Lambda service 2
│       ├── lambda_function.py                          ← AWS entry point
│       ├── handler.py
│       ├── dependencies.py
│       ├── use_cases/
│       ├── adapters/
│       └── requirements.txt
│
└── helper/                                             ✅ Shared code
    ├── logging_utils.py                               (bundled in both ZIPs)
    ├── request_context.py                             (bundled in both ZIPs)
    ├── event_publisher.py                             (bundled in both ZIPs)
    ├── domain_events.py                               (bundled in both ZIPs)
    ├── sqs_queue_manager.py
    ├── eks_request_middleware.py
    └── utilities.py
```

---

## AWS Deployment Package Content

```
┌─────────────────────────────────────────────────────────────┐
│        onboarding-lambda.zip (uploaded to AWS)              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  /                                                           │
│  ├── lambda_function.py                                     │
│  │   def lambda_handler(event, context):                    │
│  │       ...                                                │
│  │                                                          │
│  ├── handler.py                                             │
│  ├── registry.py                                            │
│  ├── services/                                              │
│  │   └── onboarding_service/                                │
│  │       └── onboarding/                                    │
│  │           ├── v1/                                        │
│  │           │   ├── controllers/                           │
│  │           │   ├── services/                              │
│  │           │   ├── repositories/                          │
│  │           │   └── ...                                    │
│  │           └── main.py                                    │
│  │                                                          │
│  ├── helper/                          ← Shared code        │
│  │   ├── logging_utils.py             (bundled)            │
│  │   ├── event_publisher.py           (bundled)            │
│  │   ├── domain_events.py             (bundled)            │
│  │   └── ...                                               │
│  │                                                          │
│  ├── boto3/                           ← Dependencies       │
│  │   ├── __init__.py                  (large!)             │
│  │   ├── s3/                                               │
│  │   ├── dynamodb/                                         │
│  │   ├── sqs/                                              │
│  │   └── ...                                               │
│  │                                                          │
│  ├── pydantic/                        ← Dependencies       │
│  │   ├── __init__.py                  (150+ files)         │
│  │   ├── v1/                                               │
│  │   ├── json.py                                           │
│  │   └── ...                                               │
│  │                                                          │
│  ├── botocore/                        ← Dependencies       │
│  ├── urllib3/                                              │
│  ├── certifi/                                              │
│  ├── typing_extensions/                                    │
│  └── ... (total ~750+ files)          ← Size: 25-50 MB     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Decision Tree

```
┌─────────────────────────────────────┐
│ Developer pushes to main branch      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ What files changed?                 │
└────────┬─────────────────────────────┘
         │
    ┌────┴───────────────────────────────────────┐
    │                                             │
    ▼                                             ▼
┌──────────────────────┐            ┌──────────────────────┐
│ services/onboarding/ │            │ services/email_      │
│ or helper/           │            │ or helper/           │
└────────┬─────────────┘            └──────────┬───────────┘
         │                                      │
    YES  │                                      │  YES
         ▼                                      ▼
    ┌────────────────────────────────────────────────┐
    │ Build onboarding-lambda.zip                    │
    └────────┬───────────────────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────────────────┐
    │ Deploy to AWS Lambda: dev-onboarding           │
    └────────┬───────────────────────────────────────┘
             │
             ▼
    ┌────────────────────────────────────────────────┐
    │ ✅ Onboarding Lambda live with new code        │
    └────────────────────────────────────────────────┘

Similar flow for email-lambda.zip → dev-email-service
```

---

## GitHub to AWS Communication

```
GitHub Actions                           AWS Cloud
┌──────────────────┐                 ┌─────────────────┐
│                  │                 │                 │
│ AWS Credentials: │◄────────────────┤ IAM User        │
│ ACCESS_KEY_ID    │ Stored as →      │ github-lambda-  │
│ SECRET_ACCESS    │ GitHub Secrets   │ deployer        │
│                  │                 │                 │
└──────────────────┘                 └─────────────────┘
         │
         │
         ▼
┌──────────────────┐
│ aws-actions/     │
│ configure-aws    │
│ credentials      │
│ (validates creds)│
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ aws lambda update-function-code      │
│   --function-name dev-onboarding     │
│   --zip-file fileb://...zip          │
│   --region us-east-1                 │
└────────┬─────────────────────────────┘
         │
         ▼
    AWS API Call
         │
         ▼
┌──────────────────────────────────────┐
│ Lambda service receives zip          │
│ Extracts to /var/task/               │
│ Reloads function code                │
│ Ready for next invocation             │
└──────────────────────────────────────┘
```

---

## Deployment Timeline

```
Time    Event                                     Status
────────────────────────────────────────────────────────────
00:00   Developer: git push origin main           🔄 Pushing
00:01   GitHub: Workflow triggered                🔄 Running
00:02   Job: detect-changes (30 seconds)          🟦 Computing
00:03   Job: build-onboarding (90 seconds)        🟦 Building
00:04   Job: deploy-onboarding (60 seconds)       🟦 Uploading
00:05   AWS: Lambda code updated                  ✅ LIVE
        
        Total time: ~5 minutes
        
        Your new code is now running on AWS Lambda!
```

---

## Multi-Service Deployment Scenario

```
Commit: "refactor: update shared event_publisher"
↓
Detects: helper/event_publisher.py changed
↓
Decision: Both lambdas use helper/ → rebuild both!
↓
┌──────────────────────┐    ┌──────────────────────┐
│ build-onboarding     │    │ build-email          │
│ (onboarding ZIP)     │    │ (email ZIP)          │
└─────────┬────────────┘    └──────────┬───────────┘
          │                            │
          └────────┬───────────────────┘
                   │ (parallel)
                   ▼
          ┌──────────────────────┐
          │ upload artifacts     │
          └─────────┬────────────┘
                    │
          ┌─────────┴──────────┐
          │                    │
          ▼                    ▼
     ┌─────────────┐      ┌──────────────┐
     │ deploy      │      │ deploy       │
     │ onboarding  │      │ email        │
     │ (parallel)  │      │ (parallel)   │
     └──────┬──────┘      └──────┬───────┘
            │                    │
            └────────┬───────────┘
                     ▼
            ┌─────────────────────┐
            │ ✅ Both lambdas live │
            │ with updated code    │
            └─────────────────────┘
```

---

## Summary Diagram

```
                           Your Repository
                    ┌──────────────────────────┐
                    │                          │
            ┌──────────────────────────────────┴─────┐
            │                                         │
         Code                               Configuration
            │                                         │
    ┌───────┴────────┐                       ┌────────┴────────┐
    │                │                       │                 │
 services/        helper/            lambda-config.json   .github/
  ├─ onboarding   (shared)            (function names)   workflows/
  └─ email                             (environments)     deploy-lambda.yml
                                       (dependencies)


                      On Push to Main
                             │
                             ▼
                    GitHub Actions Workflow
                             │
                ┌────────────┼────────────┐
                │            │            │
           Detect         Build         Deploy
           Changes       Packages        to AWS
                │            │            │
                └────────────┼────────────┘
                             │
                             ▼
                       AWS Lambda
                    (live for your SQS events)
```

