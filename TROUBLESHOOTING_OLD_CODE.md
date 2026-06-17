# Lambda Deployment Troubleshooting: Old Code Still Live

## Problem: I ran setup script but Lambda still has old code

This is **expected and normal**! Here's why:

```
┌──────────────────────────────────────┐
│ Step 1: Run setup_lambda_deployment.py │
├──────────────────────────────────────┤
│ ✅ Creates Lambda functions on AWS   │
│ ✅ Creates IAM user                  │
│ ✅ Sets up GitHub secrets            │
│                                      │
│ ❌ Does NOT deploy your code         │
│    (Uses placeholder.zip)            │
└──────────────────────────────────────┘
         │
         │ (Placeholder code is now live)
         │
         ▼
┌──────────────────────────────────────┐
│ Step 2: Trigger GitHub Actions       │
├──────────────────────────────────────┤
│ ✅ Detects your code changes         │
│ ✅ Builds deployment package         │
│ ✅ Deploys real code to Lambda       │
│                                      │
│ Result: Real code is now live        │
└──────────────────────────────────────┘
```

---

## Solution: Trigger the GitHub Actions Workflow

The setup script creates the **infrastructure** (empty Lambda functions). The **GitHub Actions workflow** deploys your code.

### Option 1: Push a Code Change (Recommended)

```bash
cd /Users/prometteur/Documents/Leaning/python-backend-learning

# Make a small change (any change triggers deployment)
echo "# Deployment test" >> README.md

# Commit and push
git add README.md
git commit -m "test: trigger Lambda deployment"
git push origin main
```

**What happens:**
1. GitHub Actions triggered
2. Detects `services/` or `helper/` might have changed (uses git diff)
3. Builds your Lambdas
4. Deploys to AWS
5. Your real code is now live! ✅

### Option 2: Manual Deployment (Alternative)

If you want to deploy **right now without pushing**:

```bash
# Build the Lambda package locally
cd services/onboarding_service/onboarding

# Create build directory
mkdir -p lambda-build
cd lambda-build

# Copy code
cp -r ../../../helper .
cp -r .. services/onboarding_service/onboarding

# Install dependencies
pip install -r services/onboarding_service/onboarding/requirements.txt -t .

# Create ZIP
cd ..
zip -r onboarding-lambda.zip lambda-build/

# Deploy to AWS
aws lambda update-function-code \
  --function-name dev-onboarding \
  --zip-file fileb://onboarding-lambda.zip

# Wait for update
aws lambda wait function-updated --function-name dev-onboarding

echo "✅ Deployed!"
```

### Option 3: Monitor GitHub Actions Deployment

If you already pushed, check the deployment status:

```bash
# On GitHub:
# 1. Go to: repo → Actions tab
# 2. Click the "Deploy Lambda Functions" workflow
# 3. Watch the jobs:
#    ├─ detect-changes (running...)
#    ├─ build-onboarding-lambda (running...)
#    └─ deploy-onboarding-lambda (running...)

# On terminal, view logs:
gh run list --workflow deploy-lambda.yml --limit 1

# Get the run ID and view logs:
gh run view RUN_ID --log
```

---

## Verification: Confirm Your Code is Live

After deployment, verify:

### 1. Check Lambda Code in AWS Console

```bash
# Get Lambda function details
aws lambda get-function --function-name dev-onboarding \
  --query 'Configuration.[FunctionName,LastModified,CodeSize]' \
  --output table
```

Look for:
- ✅ `LastModified` should be recent (not old)
- ✅ `CodeSize` should be large (20-50 MB, not small)

### 2. Check Lambda Code SHA

```bash
# Get the code location
aws lambda get-function --function-name dev-onboarding \
  --query 'Code.Location' --output text
```

This URL contains the deployment info.

### 3. View Lambda Logs

```bash
# Check recent Lambda logs
aws logs tail /aws/lambda/dev-onboarding --follow

# Or list log streams
aws logs describe-log-streams \
  --log-group-name /aws/lambda/dev-onboarding \
  --query 'logStreams[*].[logStreamName,creationTime]' \
  --output table
```

### 4. Test Lambda Manually

```bash
# Invoke Lambda to see if new code works
aws lambda invoke \
  --function-name dev-onboarding \
  --payload '{"test": true}' \
  response.json

cat response.json
```

---

## Troubleshooting Steps

### Step 1: Verify AWS Credentials Work

```bash
# Check AWS CLI configuration
aws sts get-caller-identity
```

Expected output:
```json
{
  "UserId": "...",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::..."
}
```

If error: Your AWS credentials aren't configured or are wrong.
```bash
aws configure
# Re-enter Access Key, Secret Key, Region
```

### Step 2: Verify Lambda Exists

```bash
# List all Lambda functions
aws lambda list-functions --query 'Functions[*].FunctionName' --output table

# Look for: dev-onboarding, dev-email-service
```

If not found: Lambda function wasn't created or name is different.
```bash
# Check lambda-config.json for correct names
cat lambda-config.json | grep function_name

# Update if needed and run setup again
python3 scripts/setup_lambda_deployment.py
```

### Step 3: Verify GitHub Secrets

```bash
# Can't check from CLI, but go to:
# GitHub repo → Settings → Secrets and variables → Actions

# Should see:
# ✅ AWS_ACCESS_KEY_ID
# ✅ AWS_SECRET_ACCESS_KEY
```

If missing: Secrets weren't added to GitHub.
```bash
# Rerun setup script and copy the credentials
python3 scripts/setup_lambda_deployment.py

# Then manually add to GitHub
```

### Step 4: Check GitHub Actions Status

Go to GitHub repo:
1. Click **Actions** tab
2. Look for **"Deploy Lambda Functions"** workflow
3. Click it to see history
4. Most recent run should show:
   - ✅ detect-changes (completed)
   - ✅ build-onboarding-lambda (completed)
   - ✅ deploy-onboarding-lambda (completed)

If any show ❌: Click to see error logs.

### Step 5: Verify Workflow Was Triggered

```bash
# Recent pushes should trigger the workflow
git log --oneline -n 5

# Each push to main should have:
# - Created a workflow run
# - Built Lambda packages
# - Deployed to AWS
```

---

## Common Issues & Fixes

### Issue 1: "Lambda function not found"

```
Error: Could not connect to the endpoint URL: https://lambda.us-east-1.amazonaws.com/
```

**Fix:**
1. Verify Lambda exists: `aws lambda list-functions`
2. Verify AWS region in lambda-config.json matches workflow: `us-east-1`
3. Regenerate AWS credentials if older than 3 months

### Issue 2: "Access Denied"

```
Error: User is not authorized to perform: lambda:UpdateFunctionCode
```

**Fix:**
1. Check IAM user has `AWSLambda_FullAccess` policy
2. Regenerate access keys (old ones may have lost permissions)
3. Verify GitHub secrets match latest access keys

### Issue 3: "Lambda deployment succeeds but old code still runs"

```
Deploy shows ✅ but old Lambda code still executes
```

**Fix:**
1. Clear Lambda's environment/cache (doesn't apply to Lambda, but check):
   ```bash
   aws lambda update-function-configuration \
     --function-name dev-onboarding \
     --environment Variables={}
   ```
   Then restore:
   ```bash
   aws lambda update-function-configuration \
     --function-name dev-onboarding \
     --environment Variables='{STAGE:dev}'
   ```

2. Check if Lambda is version-aliased:
   ```bash
   aws lambda list-aliases --function-name dev-onboarding
   ```
   If yes, alias may point to old version.

3. Manually redeploy:
   ```bash
   aws lambda update-function-code \
     --function-name dev-onboarding \
     --zip-file fileb://onboarding-lambda.zip
   ```

### Issue 4: "ZIP file size is wrong"

Build created small ZIP instead of large one with dependencies.

**Fix:**
```bash
# Check what's in the ZIP
unzip -l onboarding-lambda.zip | head -20

# Should show:
# - helper/
# - services/onboarding_service/
# - boto3/
# - pydantic/
# - ... (lots of files)

# If only shows your code, pip install didn't work
# Rebuild manually:
pip install -r requirements.txt -t .
zip -r lambda.zip .
```

---

## Quick Fix Checklist

- [ ] AWS CLI configured: `aws configure`
- [ ] AWS credentials valid: `aws sts get-caller-identity`
- [ ] Lambda functions exist: `aws lambda list-functions`
- [ ] GitHub secrets added (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- [ ] `lambda-config.json` updated with correct function names
- [ ] Pushed code to main: `git push origin main`
- [ ] GitHub Actions workflow ran: Check Actions tab
- [ ] All jobs succeeded (green checkmarks)
- [ ] Lambda LastModified is recent: `aws lambda get-function --function-name dev-onboarding`

---

## Fast Track: Deploy Now

```bash
# 1. Verify setup
python3 scripts/setup_lambda_deployment.py

# 2. Push to trigger deployment
git add . && git commit -m "trigger deployment" && git push origin main

# 3. Monitor
# Go to: GitHub → Actions tab → Watch workflow run

# 4. Verify
aws lambda get-function --function-name dev-onboarding --query 'Configuration.LastModified'
# Should show recent timestamp

# 5. Check logs
aws logs tail /aws/lambda/dev-onboarding --follow
```

---

## What Should Happen

```
Time    Action                              Lambda Code Status
────────────────────────────────────────────────────────
00:00   Run: python3 setup_lambda_deployment.py
        ✅ Lambda created (placeholder code)  Placeholder ⏸️

00:05   Run: git push origin main
        ✅ Workflow triggered                 Placeholder ⏸️

00:06   GitHub Actions:
        ✅ detect-changes                    Placeholder ⏸️
        ✅ build-onboarding-lambda           Placeholder ⏸️
        ✅ deploy-onboarding-lambda          🔄 Deploying

00:07   AWS Lambda updated
        ✅ Code replaced                     ✅ LIVE! 🎉
```

---

## Next: Monitor Deployment in Real-Time

### Option 1: GitHub Actions UI (Easiest)

1. Go to your GitHub repo
2. Click **Actions** tab
3. Click **Deploy Lambda Functions** (most recent run)
4. Watch jobs execute in real-time
5. Click each job to see logs

### Option 2: Terminal

```bash
# List recent runs
gh run list --workflow deploy-lambda.yml --limit 5

# View a specific run
gh run view RUN_ID --log

# Follow a running workflow
gh run watch RUN_ID
```

---

## Summary

**The setup script:**
- ✅ Creates infrastructure (Lambda functions, IAM user)
- ✅ Sets up credentials
- ❌ Does NOT deploy your code (uses placeholder)

**GitHub Actions workflow:**
- ✅ Deploys your real code
- ✅ Runs on every push to main
- ✅ Can be manually triggered

**Next step:** Push code to main to trigger deployment!

```bash
git push origin main
```

Then watch it deploy live! 🚀

