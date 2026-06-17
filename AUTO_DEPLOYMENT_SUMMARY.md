# Auto-Deployment Architecture Summary

## What You Now Have

A **production-ready Lambda auto-deployment system** that:

✅ Automatically deploys on every merge to `main`  
✅ Intelligently detects which Lambdas changed  
✅ Builds optimal deployment packages  
✅ Only deploys changed services  
✅ Handles shared code (helper/) across services  
✅ Zero-downtime deployments  

---

## The 5 Files You Need

### 1. `.github/workflows/deploy-lambda.yml`
**What:** Main GitHub Actions workflow  
**Where:** `/Users/prometteur/Documents/Leaning/python-backend-learning/.github/workflows/deploy-lambda.yml`  
**Does:** Detects changes → builds packages → deploys to AWS  

### 2. `lambda-config.json`
**What:** Lambda function metadata  
**Where:** `/Users/prometteur/Documents/Leaning/python-backend-learning/lambda-config.json`  
**Does:** Maps service names to AWS Lambda function names  
**You must update:**
```json
{
  "lambdas": {
    "onboarding": {
      "function_name": "YOUR-ACTUAL-LAMBDA-NAME-HERE"
    },
    "email": {
      "function_name": "YOUR-EMAIL-LAMBDA-NAME-HERE"
    }
  }
}
```

### 3. `LAMBDA_DEPLOYMENT_GUIDE.md`
**What:** Complete deployment documentation  
**Where:** `/Users/prometteur/Documents/Leaning/python-backend-learning/LAMBDA_DEPLOYMENT_GUIDE.md`  
**Does:** Everything you need to know + troubleshooting  

### 4. `scripts/setup_lambda_deployment.py`
**What:** Automated setup helper script  
**Where:** `/Users/prometteur/Documents/Leaning/python-backend-learning/scripts/setup_lambda_deployment.py`  
**Does:** Creates IAM user, sets up AWS, verifies config  

### 5. `services/*/lambda_function.py`
**What:** Lambda entry points (you already have these)  
**Where:** Already exist in your repo  
**Must have:** These are the files GitHub Actions will package  

---

## Quick Start (5 Minutes)

### Step 1: Install AWS CLI

```bash
# macOS
brew install awscli

# or download from https://aws.amazon.com/cli/
```

### Step 2: Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Output format: json
```

### Step 3: Run Setup Script

```bash
cd /Users/prometteur/Documents/Leaning/python-backend-learning
python3 scripts/setup_lambda_deployment.py
```

This script will:
- ✅ Create IAM user `github-lambda-deployer`
- ✅ Create access keys
- ✅ List your Lambda functions
- ✅ Create missing Lambda functions in AWS
- ✅ Show you credentials to add to GitHub

### Step 4: Add Secrets to GitHub

Go to your GitHub repo:
1. **Settings** → **Secrets and variables** → **Actions**
2. Add two secrets:
   - `AWS_ACCESS_KEY_ID` = (from setup script)
   - `AWS_SECRET_ACCESS_KEY` = (from setup script)

### Step 5: Update `lambda-config.json`

Edit the file and set correct Lambda function names:

```bash
nano lambda-config.json
```

Find your Lambda names:
```bash
aws lambda list-functions --query 'Functions[*].FunctionName' --output text
```

### Step 6: Test!

```bash
git add .github/workflows/deploy-lambda.yml lambda-config.json LAMBDA_DEPLOYMENT_GUIDE.md
git commit -m "feat: add Lambda auto-deployment"
git push origin main
```

**Watch deployment:**
- Go to **Actions** tab on GitHub
- Click the running workflow
- Watch it deploy your Lambdas in real-time!

---

## How It Works: The Full Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Developer: git push origin main                            │
│  (Code merged with changes to services/onboarding_service/) │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Workflow Triggered                                  │
│  .github/workflows/deploy-lambda.yml                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Job 1: detect-changes                                      │
│  - git diff $before $after                                  │
│  - Check: services/onboarding_service/ changed? YES         │
│  - Check: services/email_service/ changed? NO               │
│  - Output: onboarding_lambda_changed=true                   │
│  - Output: email_lambda_changed=false                       │
└────────────────────────┬────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
  ┌──────────────────┐    ┌──────────────────────┐
  │ Job 2a (Runs)    │    │ Job 2b (Skipped)     │
  │ build-onboarding │    │ build-email          │
  │ lambda           │    │ (not changed)        │
  └────────┬─────────┘    └──────────────────────┘
           │
           ▼
  ┌──────────────────────────────────┐
  │ Create Lambda deployment package │
  │ - Copy helper/                   │
  │ - Copy services/onboarding_*/    │
  │ - pip install requirements.txt   │
  │ - zip -r onboarding-lambda.zip . │
  └────────┬─────────────────────────┘
           │
           ▼
  ┌──────────────────────────────────┐
  │ Upload as GitHub Artifact        │
  │ (retained for 1 day)             │
  └────────┬─────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Job 3: deploy-onboarding-lambda                            │
│  - Download onboarding-lambda.zip artifact                  │
│  - aws configure (use AWS_ACCESS_KEY_ID, AWS_SECRET...)     │
│  - aws lambda update-function-code \                        │
│    --function-name dev-onboarding \                         │
│    --zip-file fileb://onboarding-lambda.zip                 │
│  - aws lambda wait function-updated                         │
│  - ✅ DEPLOYED!                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                    ✅ DONE
            New code is LIVE on AWS Lambda
```

---

## Scenarios

### Scenario A: Fix email service bug

```bash
# Edit services/email_service/adapters/email_adapter.py
# Commit and push
git push origin main
```

**Result:**
- ✅ Email Lambda rebuilds and deploys
- ⏭️ Onboarding Lambda skips (no changes)
- 🎯 Only email service is updated

### Scenario B: Update shared logging

```bash
# Edit helper/logging_utils.py
git push origin main
```

**Result:**
- ✅ Both Lambdas rebuild (both use helper/)
- ✅ Both Lambdas deploy in parallel
- 🎯 Both services get updated logging

### Scenario C: Update documentation

```bash
# Edit README.md
git push origin main
```

**Result:**
- ⏭️ No Lambda changes detected
- ⏭️ Workflow runs but skips build and deploy
- 🎯 No unnecessary AWS updates

---

## Key Files and Paths

```
project/
├── .github/
│   └── workflows/
│       └── deploy-lambda.yml              ✅ Workflow config
├── lambda-config.json                     ✅ Lambda metadata
├── LAMBDA_DEPLOYMENT_GUIDE.md            ✅ Full documentation
├── scripts/
│   └── setup_lambda_deployment.py         ✅ Setup helper
├── services/
│   ├── onboarding_service/
│   │   └── onboarding/
│   │       ├── lambda_function.py         ✅ Entry point
│   │       ├── requirements.txt           ✅ Dependencies
│   │       ├── handler.py                 
│   │       ├── registry.py
│   │       └── v1/
│   └── email_service/
│       ├── lambda_function.py             ✅ Entry point
│       ├── requirements.txt               ✅ Dependencies
│       ├── handler.py
│       └── ...
└── helper/                                ✅ Shared code
    ├── logging_utils.py
    ├── event_publisher.py
    ├── domain_events.py
    └── ...
```

---

## What Gets Deployed

### Onboarding Lambda ZIP Contains:

```
onboarding-lambda.zip (uploaded to AWS)
│
├── helper/                           # Shared utilities
│   ├── logging_utils.py
│   ├── event_publisher.py
│   ├── domain_events.py
│   └── ...
│
├── services/onboarding_service/      # Application code
│   └── onboarding/
│       ├── lambda_function.py        ← AWS calls this
│       ├── handler.py
│       ├── registry.py
│       ├── v1/
│       └── requirements.txt (installed below)
│
└── boto3/                            # Installed dependencies
    pydantic/
    urllib3/
    certifi/
    ... (everything from pip install)
```

### Email Lambda ZIP Contains:

```
email-lambda.zip (uploaded to AWS)
│
├── helper/                           # Same shared code
├── services/email_service/           # Application code
│   ├── lambda_function.py            ← AWS calls this
│   ├── handler.py
│   ├── dependencies.py
│   └── ...
│
└── (all dependencies installed)
```

---

## Environment Variables

Lambda functions have access to environment variables set in `lambda-config.json`:

```json
{
  "lambdas": {
    "onboarding": {
      "environment": {
        "STAGE": "dev",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Your Python code can access:

```python
import os

stage = os.getenv('STAGE')      # 'dev'
log_level = os.getenv('LOG_LEVEL')  # 'INFO'
```

---

## Workflow Triggers

The workflow **only** runs when:

```yaml
on:
  push:
    branches:
      - main                    # Must push to main
    paths:
      - 'services/**'           # AND changes in services/
      - 'helper/**'             # OR changes in helper/
      - '.github/workflows/deploy-lambda.yml'  # OR workflow itself
```

So:
- ✅ Push to main with service changes → Runs
- ❌ Push to dev branch → Doesn't run
- ❌ Push to main but only edit README → Doesn't run
- ✅ Push to main with helper changes → Runs

---

## AWS Permissions Required

The IAM user created by the setup script needs:

```
AWSLambda_FullAccess
├── lambda:UpdateFunctionCode      ✅ Deploy new code
├── lambda:UpdateFunctionConfiguration  ✅ Change settings
├── lambda:GetFunction              ✅ Verify deployment
└── ... (all Lambda permissions)
```

No need for S3, DynamoDB, or other AWS services permissions (that's for the Lambda itself, not the deployer).

---

## Troubleshooting

**Q: Workflow doesn't run after push?**
- Check branch: must be `main`
- Check files: must change `services/` or `helper/`
- Check **Actions** tab → Enable workflows if disabled

**Q: AWS credential error?**
- Verify secrets are set: Settings → Secrets
- Check names exactly: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Regenerate if unsure: Run setup script again

**Q: Lambda function not found?**
- Update `lambda-config.json` with correct names
- List functions: `aws lambda list-functions`
- Create missing: Run setup script with "Create Lambdas" option

**Q: ZIP file too large?**
- Check `lambda-config.json` `exclude_patterns`
- Remove test files: `find . -path ./tests -prune -o -type f -name "*.pyc" -delete`
- Use Layers for heavy deps: See guide

**Q: Deployment succeeds but Lambda doesn't work?**
- Check Lambda logs: `aws logs tail /aws/lambda/dev-onboarding --follow`
- Verify handler: Should be `lambda_function.lambda_handler`
- Check IAM role: Lambda needs permissions for SQS, SNS, DynamoDB, etc.

---

## Next Steps

1. ✅ Run setup script
2. ✅ Add GitHub secrets
3. ✅ Update `lambda-config.json`
4. ✅ Push a test commit
5. ✅ Watch Actions tab
6. ✅ Verify Lambda is live in AWS

Then explore:
- Multi-environment deployments (dev, staging, prod)
- Blue-green deployments (traffic shifting)
- Lambda Layers for shared dependencies
- Automated testing before deploy
- Rollback on failure

---

## Reference

Full details: See `LAMBDA_DEPLOYMENT_GUIDE.md`

AWS CLI commands: See guide's "Quick Reference" section

Setup errors: See guide's "Troubleshooting" section

