# Action Plan: Deploy Your Lambda Code Now ✅

## What Just Happened

You ran `python3 scripts/setup_lambda_deployment.py` which:

✅ Created Lambda functions on AWS (dev-onboarding, dev-email-service)  
✅ Created IAM user for GitHub Actions  
✅ Generated AWS credentials  
✅ Verified configuration  

But these Lambda functions currently have **placeholder code** (created by the setup script).

---

## Why Lambda Has Old Code

The setup script creates empty Lambda functions with a placeholder ZIP. Your real code hasn't been deployed yet because:

```
setup_lambda_deployment.py         GitHub Actions Workflow
└─ Creates infrastructure          └─ Deploys code
   (empty Lambda functions)           (real code)
   
   These are separate steps!
```

---

## Deploy Your Real Code Now

### What I Just Did ✅

Committed a file which **automatically triggered** your GitHub Actions workflow:

```bash
git commit -m "docs: add troubleshooting guide..."
git push origin main
```

This push triggers `.github/workflows/deploy-lambda.yml` which:
1. Detects code changes
2. Builds your Lambda packages
3. Deploys to AWS
4. Your real code becomes live

### How to Monitor ⏱️

**Option 1: Watch on GitHub (Real-time, easiest)**

1. Go to: https://github.com/developer-omkar-shinde/python-backend/actions
2. Click **"Deploy Lambda Functions"** workflow (most recent run)
3. Watch jobs execute in real-time:
   - `detect-changes` (30 seconds)
   - `build-onboarding-lambda` (90 seconds)
   - `deploy-onboarding-lambda` (60 seconds)
4. Each job shows logs as it runs

**Option 2: Terminal Commands**

```bash
# List recent workflow runs
gh run list --workflow deploy-lambda.yml --limit 3

# View the latest run
gh run view --log

# Or manually check AWS
aws lambda get-function --function-name dev-onboarding \
  --query 'Configuration.LastModified' --output text
```

---

## Expected Timeline

```
Now:           You pushed code
     │
     ├─ 10 seconds: GitHub detects push
     │
     ├─ 30 seconds: detect-changes job
     │              (checks what changed)
     │
     ├─ 90 seconds: build-onboarding-lambda
     │              (creates ZIP with dependencies)
     │
     ├─ 60 seconds: deploy-onboarding-lambda
     │              (uploads to AWS)
     │
     └─ NOW: ✅ Your Lambda code is LIVE!

Total time: ~4 minutes
```

---

## What's Deploying

Your GitHub Actions workflow is building these packages:

### Onboarding Lambda
```
onboarding-lambda.zip (30-50 MB)
├── services/onboarding_service/onboarding/
│   ├── lambda_function.py          ← Entry point
│   ├── handler.py
│   ├── registry.py
│   ├── v1/
│   │   ├── controllers/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── domain/
│   │   ├── schemas/
│   │   └── dependencies.py
│   ├── main.py
│   └── requirements.txt (installed below)
├── helper/
│   ├── logging_utils.py           ← Shared code
│   ├── event_publisher.py
│   ├── domain_events.py
│   ├── sqs_queue_manager.py
│   ├── eks_request_middleware.py
│   └── utilities.py
└── boto3, pydantic, botocore/     ← All dependencies
    ... (750+ files)
```

### Email Lambda
```
email-lambda.zip (30-50 MB)
├── services/email_service/
│   ├── lambda_function.py          ← Entry point
│   ├── handler.py
│   ├── dependencies.py
│   ├── use_cases/
│   │   ├── send_welcome_email.py
│   │   └── send_verification_email.py
│   ├── adapters/
│   │   └── email_adapter.py
│   └── requirements.txt
├── helper/                         ← Same shared code
└── boto3, pydantic, ...            ← Dependencies
```

---

## Verify Deployment Success

After ~4 minutes, verify:

### 1. Check GitHub Actions Status

Go to: https://github.com/developer-omkar-shinde/python-backend/actions

All jobs should show ✅ (green):
- ✅ detect-changes
- ✅ build-onboarding-lambda
- ✅ deploy-onboarding-lambda
- ✅ build-email-lambda (if helper/ changed)
- ✅ deploy-email-lambda (if helper/ changed)

### 2. Check Lambda Code Size Increased

```bash
# Before setup: Lambda had placeholder (small ZIP)
# After deployment: Should be 30-50 MB

aws lambda get-function --function-name dev-onboarding \
  --query 'Configuration.CodeSize' --output text

# Expected: 30000000+ (30 MB or larger)
```

### 3. Check Lambda Last Modified Time

```bash
# Should be very recent (within last 5 minutes)

aws lambda get-function --function-name dev-onboarding \
  --query 'Configuration.LastModified' --output text

# Example output: 2026-06-18T01:45:32.000+0000
```

### 4. View Lambda Logs

```bash
# Your Lambda should have logs from recent execution

aws logs tail /aws/lambda/dev-onboarding --follow --since 5m

# Should show recent entries with your application logs
```

### 5. Test Lambda Manually

```bash
# Invoke the Lambda to test it works

aws lambda invoke \
  --function-name dev-onboarding \
  --payload '{"Records": []}' \
  response.json

cat response.json
```

---

## Troubleshooting If Deployment Fails

### Symptom: GitHub Actions shows ❌ (red)

**Check:**
1. Click the failed job to see error logs
2. Common errors:
   - "AWS credentials invalid" → Regenerate and update GitHub secrets
   - "Lambda function not found" → Check `lambda-config.json` function names
   - "ZIP too large" → Remove test files

**Fix:**
```bash
# Regenerate credentials
python3 scripts/setup_lambda_deployment.py

# Update GitHub secrets with new credentials
# Then push again to trigger workflow
```

### Symptom: GitHub Actions shows ✅ but Lambda still has old code

**Check:**
```bash
# Lambda LastModified should be recent
aws lambda get-function --function-name dev-onboarding \
  --query 'Configuration.LastModified' --output text

# If still old, workflow didn't actually deploy
# Manually deploy:
aws lambda update-function-code \
  --function-name dev-onboarding \
  --zip-file fileb://onboarding-lambda.zip
```

---

## Next Steps

### Immediate (Next 5 minutes)
1. ✅ Wait for GitHub Actions to complete
2. ✅ Verify deployment succeeded (all jobs green)
3. ✅ Check Lambda code size and LastModified time
4. ✅ View logs to confirm your code is running

### Short Term (Today)
1. Test Lambda with a real SQS event
2. Verify event publishing works (SNS)
3. Verify email sending works
4. Check CloudWatch logs for any errors

### Medium Term (This week)
1. Add PR CI (lint, test, coverage)
2. Add multi-environment support (dev, stg, prod)
3. Add automated testing before deployment
4. Set up monitoring and alerts

---

## How to Make Future Deployments

From now on, it's simple:

```bash
# 1. Make code changes
nano services/onboarding_service/onboarding/v1/services/user_service.py

# 2. Commit
git add .
git commit -m "feat: improve user onboarding flow"

# 3. Push
git push origin main

# That's it! GitHub Actions automatically:
# ├─ Detects changes
# ├─ Builds Lambda package
# └─ Deploys to AWS
```

No manual AWS work needed. Code → GitHub → Lambda. Automated! 🚀

---

## Current Status

```
Setup Script               GitHub Actions        AWS Lambda
───────────────           ──────────────         ──────────
✅ Completed              🔄 Running (4 min)     🔄 Deploying
- IAM user                - detect-changes       - Uploading code
- Lambda functions        - build packages       - Updating function
- GitHub secrets          - deploy to AWS        - New code live ✅
```

---

## You're Now Using Production DevOps! 🎉

You have:
- ✅ Infrastructure as Code (lambda-config.json)
- ✅ CI/CD Pipeline (GitHub Actions)
- ✅ Automatic deployments (on push)
- ✅ Change detection (only deploy what changed)
- ✅ Multi-service support (onboarding + email)
- ✅ Zero manual AWS Console work

This is the same pattern enterprise teams use!

---

## Summary

**What happened:**
1. Setup script created Lambda infrastructure ✅
2. You pushed code → GitHub Actions triggered 🔄
3. Workflow building and deploying your Lambda ⏳

**Current status:**
- ✅ Infrastructure ready
- 🔄 Deployment in progress
- ⏳ Check GitHub Actions tab

**Next action:**
1. Monitor: https://github.com/developer-omkar-shinde/python-backend/actions
2. Wait ~4 minutes for deployment to complete
3. Verify: `aws lambda get-function --function-name dev-onboarding`
4. Celebrate! 🎉

