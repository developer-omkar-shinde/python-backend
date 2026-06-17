# Lambda Auto-Deployment Guide

## Overview

This setup provides **automatic, production-ready Lambda deployment** on every merge to `main` branch using GitHub Actions.

### What Happens On Merge

```
1. Code merged to main
   ↓
2. GitHub Actions triggered
   ↓
3. Detect which Lambda changed (onboarding, email, or both)
   ↓
4. Build deployment package (with dependencies)
   ↓
5. Deploy to AWS Lambda
   ↓
6. Wait for Lambda to be ready
   ↓
7. ✅ Live on AWS
```

---

## Setup Steps

### 1. Add AWS Credentials to GitHub

Your GitHub repo needs AWS credentials to deploy. This is a one-time setup:

**Step 1: Create IAM User for GitHub Actions**

```bash
# Using AWS CLI
aws iam create-user --user-name github-lambda-deployer

# Attach policy for Lambda deployment
aws iam attach-user-policy \
  --user-name github-lambda-deployer \
  --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess
```

**Step 2: Create Access Keys**

```bash
aws iam create-access-key --user-name github-lambda-deployer
```

This outputs:
```json
{
  "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
  "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

**Step 3: Add to GitHub Repository Secrets**

On GitHub:
1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add two secrets:
   - **Name:** `AWS_ACCESS_KEY_ID`
   - **Value:** (paste AccessKeyId from step 2)
4. Click **New repository secret** again
   - **Name:** `AWS_SECRET_ACCESS_KEY`
   - **Value:** (paste SecretAccessKey from step 2)

✅ Now GitHub Actions can deploy to AWS

---

### 2. Update `lambda-config.json`

Edit `/lambda-config.json` to match your AWS Lambda function names:

```json
{
  "lambdas": {
    "onboarding": {
      "function_name": "dev-onboarding",  // ← Change to YOUR Lambda function name
      ...
    },
    "email": {
      "function_name": "dev-email-service",  // ← Change to YOUR Lambda function name
      ...
    }
  }
}
```

To find your Lambda function names in AWS:

```bash
aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime]' --output table
```

### 3. Create Lambda Functions in AWS

If you don't have Lambda functions yet, create them:

```bash
# For onboarding Lambda
aws lambda create-function \
  --function-name dev-onboarding \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://placeholder.zip \
  --timeout 300 \
  --memory-size 512

# For email Lambda
aws lambda create-function \
  --function-name dev-email-service \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://placeholder.zip \
  --timeout 300 \
  --memory-size 512
```

---

## How It Works

### File Structure

```
project/
├── .github/workflows/
│   └── deploy-lambda.yml          # ← Main CI/CD workflow
├── lambda-config.json             # ← Lambda metadata
├── services/
│   ├── onboarding_service/
│   │   └── onboarding/
│   │       ├── lambda_function.py # ← Entry point
│   │       └── requirements.txt   # ← Dependencies
│   └── email_service/
│       ├── lambda_function.py
│       └── requirements.txt
└── helper/                        # ← Shared code (bundled with each Lambda)
```

### Workflow Steps Explained

#### 1. **Detect Changes** (`detect-changes` job)
- Compares current commit with previous commit
- Checks if `services/onboarding_service/` or `helper/` changed
- Checks if `services/email_service/` or `helper/` changed
- Sets output flags: `onboarding-lambda-changed`, `email-lambda-changed`

```yaml
if: git diff ... | grep -E '^services/onboarding_service/|^helper/'
```

This means:
- Changing `services/onboarding_service/onboarding/lambda_function.py` → triggers onboarding build
- Changing `helper/logging_utils.py` → triggers BOTH builds (shared code)
- Changing `services/email_service/schemas.py` → triggers only email build

#### 2. **Build Lambda Package** (`build-onboarding-lambda` / `build-email-lambda` jobs)
- Copies service code
- Installs dependencies from `requirements.txt`
- Creates ZIP file with all code and dependencies
- Uploads ZIP as artifact

```bash
pip install -r requirements.txt -t .
zip -r lambda.zip .
```

Result: A single ZIP file with everything Lambda needs to run.

#### 3. **Deploy to AWS** (`deploy-onboarding-lambda` / `deploy-email-lambda` jobs)
- Downloads built ZIP file
- Authenticates with AWS using stored credentials
- Calls `aws lambda update-function-code`
- Waits for Lambda to finish updating

```bash
aws lambda update-function-code \
  --function-name dev-onboarding \
  --zip-file fileb://onboarding-lambda.zip
```

---

## What Gets Deployed in the ZIP

### Onboarding Lambda ZIP includes:

```
onboarding-lambda.zip
├── helper/
│   ├── logging_utils.py
│   ├── request_context.py
│   ├── event_publisher.py
│   ├── domain_events.py
│   └── ...
├── services/
│   └── onboarding_service/
│       └── onboarding/
│           ├── lambda_function.py        ← Entry point
│           ├── handler.py
│           ├── registry.py
│           ├── v1/
│           ├── main.py
│           └── ...
├── boto3/                                ← AWS SDK
├── pydantic/                             ← Validation library
├── urllib3/                              ← Dependencies
└── ... (all dependencies)
```

### Email Lambda ZIP includes:

```
email-lambda.zip
├── helper/
│   ├── logging_utils.py
│   └── ...
├── services/
│   └── email_service/
│       ├── lambda_function.py            ← Entry point
│       ├── handler.py
│       ├── dependencies.py
│       ├── use_cases/
│       ├── adapters/
│       └── ...
├── boto3/
├── pydantic/
└── ...
```

---

## Deployment Scenarios

### Scenario 1: Fix a bug in email service

```bash
# Edit services/email_service/adapters/email_adapter.py
git add .
git commit -m "fix: improve email retry logic"
git push origin main
```

**What happens:**
1. Workflow detects `services/email_service/` changed
2. Sets `email-lambda-changed=true`
3. Skips `build-onboarding-lambda` (didn't change)
4. Builds email Lambda package
5. Deploys only email Lambda to AWS
6. ✅ Onboarding Lambda unchanged, email service has fix

### Scenario 2: Update shared logging (affects both)

```bash
# Edit helper/logging_utils.py
git add .
git commit -m "refactor: structured logging improvements"
git push origin main
```

**What happens:**
1. Workflow detects `helper/` changed
2. Sets BOTH `onboarding-lambda-changed=true` AND `email-lambda-changed=true`
3. Builds BOTH Lambda packages (helper is included in each)
4. Deploys BOTH Lambdas to AWS in parallel
5. ✅ Both services have updated logging

### Scenario 3: Update documentation only

```bash
# Edit README.md
git add .
git commit -m "docs: update deployment instructions"
git push origin main
```

**What happens:**
1. Workflow detects NO service code changed
2. Sets `onboarding-lambda-changed=false` AND `email-lambda-changed=false`
3. Skips all build and deploy jobs
4. ✅ No unnecessary AWS Lambda updates

---

## Monitoring Deployments

### View workflow status on GitHub

1. Go to your repo → **Actions**
2. Click on the workflow run
3. See real-time logs for each job

### Check Lambda status in AWS

```bash
# See latest deployment
aws lambda get-function --function-name dev-onboarding

# View function logs
aws logs tail /aws/lambda/dev-onboarding --follow

# Check recent invocations
aws lambda list-event-source-mappings \
  --function-name dev-onboarding \
  --query 'EventSourceMappings[*].[UUID,State]'
```

---

## Environment Variables

You can set different configs per environment. Update `lambda-config.json`:

```json
{
  "lambdas": {
    "onboarding": {
      "function_name": "dev-onboarding",
      "environment": {
        "STAGE": "dev",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Lambda will have access to these via `os.getenv()`:

```python
import os
stage = os.getenv('STAGE')  # 'dev'
log_level = os.getenv('LOG_LEVEL')  # 'DEBUG'
```

---

## Troubleshooting

### Deployment fails: "Role not found"

**Error:**
```
InvalidParameterValueException: The role defined for the function cannot be assumed
```

**Fix:** Ensure Lambda execution role exists and has correct policies:

```bash
# Create IAM role for Lambda
aws iam create-role \
  --role-name lambda-execution-role \
  --assume-role-policy-document file://trust-policy.json

# Attach basic Lambda permissions
aws iam attach-role-policy \
  --role-name lambda-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### ZIP file too large

**Error:**
```
An error occurred (RequestEntityTooLargeException) when calling the UpdateFunctionCode operation
```

**Fix:** Use Lambda Layers for large dependencies. Update workflow to exclude `.pyc` files:

```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -r {} +
```

### Workflow doesn't trigger

**Check:**
1. Workflow file is in `.github/workflows/deploy-lambda.yml` ✅
2. You're pushing to `main` branch ✅
3. You changed files matching the `paths:` filter ✅
4. Check **Actions** tab → see logs

---

## Next Steps: Multi-Environment

To deploy to multiple environments (dev, stg, prod), extend the workflow:

```yaml
env:
  ENVIRONMENTS: 'dev,staging,prod'

deploy-onboarding-lambda:
  strategy:
    matrix:
      environment: [dev, staging, prod]
  steps:
    - name: Deploy to ${{ matrix.environment }}
      run: |
        FUNC=$(jq -r '.lambdas.onboarding["${{ matrix.environment }}_name"]' lambda-config.json)
        aws lambda update-function-code --function-name $FUNC --zip-file fileb://onboarding-lambda.zip
```

And add to `lambda-config.json`:

```json
{
  "lambdas": {
    "onboarding": {
      "dev_name": "dev-onboarding",
      "staging_name": "staging-onboarding",
      "prod_name": "prod-onboarding"
    }
  }
}
```

---

## Best Practices

✅ **Do:**
- Test locally before pushing
- Use meaningful commit messages
- Run `pytest` in GitHub Actions before deploying
- Use environment variables for configuration
- Keep `requirements.txt` minimal

❌ **Don't:**
- Commit AWS credentials
- Deploy directly to prod without testing in dev first
- Use `lambda update-function-configuration` to change memory/timeout (update in IaC)
- Ignore deployment failures
- Leave failed Lambdas in production

---

## Quick Reference

| Command | What it does |
|---------|-------------|
| `git push origin main` | Triggers workflow |
| Check **Actions** tab | View deployment status |
| `aws lambda get-function --function-name dev-onboarding` | Check live Lambda |
| `aws logs tail /aws/lambda/dev-onboarding --follow` | View Lambda logs |
| Update `lambda-config.json` | Change function names/configs |
| Update `.github/workflows/deploy-lambda.yml` | Change deployment logic |

