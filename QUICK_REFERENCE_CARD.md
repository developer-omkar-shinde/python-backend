# Lambda Auto-Deployment: Quick Reference Card

## 30-Second Setup

```bash
# 1. Install AWS CLI
brew install awscli

# 2. Configure AWS
aws configure
# Enter Access Key, Secret Key, Region (us-east-1), Format (json)

# 3. Run setup script
cd /Users/prometteur/Documents/Leaning/python-backend-learning
python3 scripts/setup_lambda_deployment.py
# Follow prompts, save the credentials

# 4. Add GitHub Secrets
# Go to: GitHub repo → Settings → Secrets and variables → Actions
# Add 2 secrets from setup script output:
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY

# 5. Done! Push code to test
git push origin main
# Watch Actions tab for deployment
```

---

## Files Created

| File | Purpose | Edit? |
|------|---------|-------|
| `.github/workflows/deploy-lambda.yml` | Main workflow | ❌ Usually no |
| `lambda-config.json` | Function names & config | ✅ **Yes** - Update function names |
| `scripts/setup_lambda_deployment.py` | Setup helper | ❌ No |
| `LAMBDA_DEPLOYMENT_GUIDE.md` | Full documentation | ℹ️ Reference |
| `AUTO_DEPLOYMENT_SUMMARY.md` | Quick start | ℹ️ Reference |
| `DEPLOYMENT_ARCHITECTURE_COMPARISON.md` | How it compares | ℹ️ Reference |
| `DEPLOYMENT_FLOW_DIAGRAMS.md` | Visual diagrams | ℹ️ Reference |

---

## Critical Update: `lambda-config.json`

You **must** update this file with your actual Lambda function names:

```json
{
  "lambdas": {
    "onboarding": {
      "function_name": "YOUR_LAMBDA_NAME_HERE"  // ← Change this
    },
    "email": {
      "function_name": "YOUR_EMAIL_LAMBDA_NAME"  // ← Change this
    }
  }
}
```

Find your Lambda names:
```bash
aws lambda list-functions --query 'Functions[*].FunctionName' --output text
```

---

## How It Works (3 Steps)

### Step 1: Detect
```bash
git diff HEAD~1 HEAD --name-only | grep services/
# Determines which Lambda(s) changed
```

### Step 2: Build
```bash
pip install -r requirements.txt -t .
zip -r lambda.zip .
# Creates deployment package with all dependencies
```

### Step 3: Deploy
```bash
aws lambda update-function-code --function-name NAME --zip-file fileb://lambda.zip
# Updates AWS Lambda with new code
```

---

## Common Scenarios

### I changed onboarding service code
```bash
git push origin main
```
→ Workflow detects `services/onboarding_service/` changed  
→ Only onboarding Lambda builds and deploys  
→ Email Lambda skips (no changes)

### I updated shared helper code
```bash
git push origin main
```
→ Workflow detects `helper/` changed  
→ Both Lambdas build and deploy (both use helper/)  
→ Saves time by not rebuilding unaffected services

### I updated README
```bash
git push origin main
```
→ Workflow detects no service changes  
→ Entire workflow skips (nothing to deploy)

---

## Viewing Deployment Status

### On GitHub
1. Go to **Actions** tab
2. Click the running workflow
3. See real-time logs

### On AWS
```bash
# Check Lambda status
aws lambda get-function --function-name dev-onboarding

# View logs in real-time
aws logs tail /aws/lambda/dev-onboarding --follow

# See Lambda config
aws lambda get-function-configuration --function-name dev-onboarding
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Workflow doesn't run | Check: Pushing to `main`? Changed `services/` or `helper/`? |
| AWS credential error | Run setup script again, regenerate secrets |
| Lambda not found | Update `lambda-config.json` with correct names |
| ZIP too large | Remove test files, exclude `__pycache__`, `.pyc` |
| Deployment succeeds but code doesn't work | Check Lambda logs: `aws logs tail /aws/lambda/NAME` |

---

## Key Files in Your Repo

```
.github/workflows/
  └── deploy-lambda.yml              ← Main workflow (runs automatically)

lambda-config.json                   ← ⭐ UPDATE THIS with your function names

services/
  ├── onboarding_service/
  │   └── onboarding/
  │       └── lambda_function.py     ← Entry point AWS calls
  └── email_service/
      └── lambda_function.py         ← Entry point AWS calls

helper/                              ← Shared code (bundled with each Lambda)
```

---

## Environment Variables

Lambda functions have access to vars from `lambda-config.json`:

```python
import os
stage = os.getenv('STAGE')      # 'dev'
log_level = os.getenv('LOG_LEVEL')  # 'INFO'
```

Configure in `lambda-config.json`:
```json
"environment": {
  "STAGE": "dev",
  "LOG_LEVEL": "INFO"
}
```

---

## What Gets Deployed

Each Lambda ZIP contains:

```
✅ Your code (services/, helper/)
✅ All dependencies (boto3, pydantic, etc.)
❌ Test files (excluded)
❌ Documentation (excluded)
❌ .git folder (excluded)
```

Total size: ~25-50 MB per Lambda

---

## Next Steps

1. ✅ Run setup script
2. ✅ Add GitHub secrets
3. ✅ Update `lambda-config.json`
4. ✅ Make a small change to onboarding service
5. ✅ `git push origin main`
6. ✅ Watch Actions tab
7. ✅ See Lambda live on AWS!

Then explore:
- Add PR CI (lint, test, coverage)
- Add Terraform for infrastructure
- Add multi-environment support (dev, staging, prod)
- Add Lambda Layers for better organization
- Add automated rollback on deployment failure

---

## AWS Permissions Required

The IAM user needs `AWSLambda_FullAccess` policy, which includes:

- `lambda:UpdateFunctionCode` - Update Lambda code
- `lambda:UpdateFunctionConfiguration` - Change settings
- `lambda:GetFunction` - Check status
- `lambda:CreateFunction` - Create Lambdas (optional)
- All other Lambda actions

---

## Costs

AWS Lambda free tier includes:
- 1,000,000 free requests per month
- 400,000 GB-seconds of compute time per month
- Always free, no credit card required initially

For learning projects: ~$0-5 per month

---

## Support & Documentation

- **Full Guide**: `LAMBDA_DEPLOYMENT_GUIDE.md` (2000+ lines)
- **Quick Reference**: `AUTO_DEPLOYMENT_SUMMARY.md`
- **Architecture**: `DEPLOYMENT_ARCHITECTURE_COMPARISON.md`
- **Visual Flows**: `DEPLOYMENT_FLOW_DIAGRAMS.md`

All files in your repository!

---

## Emergency Revert

If deployment breaks Lambda:

```bash
# Revert to previous commit
git revert HEAD
git push origin main
# Workflow redeploys previous working version automatically
```

Or manually:
```bash
# From AWS Console: Lambda → Choose function → Code → Upload new ZIP
# Or use AWS CLI with a known-good ZIP file
```

---

## Questions?

Refer to the comprehensive guides in your repo:
- `LAMBDA_DEPLOYMENT_GUIDE.md` - All details with examples
- `DEPLOYMENT_FLOW_DIAGRAMS.md` - Visual explanations
- `DEPLOYMENT_ARCHITECTURE_COMPARISON.md` - How it matches production patterns

