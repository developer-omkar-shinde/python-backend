# Lambda Auto-Deployment via GitHub Actions

Whenever code is pushed to `main` (touching `services/onboarding_service/`, `helper/`, or the build script), GitHub Actions automatically builds and deploys the onboarding Lambda to AWS. No manual steps required.

---

## How It Works

```
git push origin main
        ↓
GitHub Actions (.github/workflows/deploy-lambda.yml)
        ↓
  1. Checkout code
  2. Read lambda-config.json  →  function name, handler, region
  3. bash scripts/build_onboarding_lambda.sh  →  dist/onboarding-lambda.zip
  4. Authenticate to AWS  (GitHub secrets)
  5. aws lambda update-function-code
  6. aws lambda update-function-configuration  (sets handler)
        ↓
user-events-processor is live with new code
```

---

## Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/deploy-lambda.yml` | GitHub Actions workflow |
| `lambda-config.json` | Target function name, handler, region |
| `scripts/build_onboarding_lambda.sh` | Builds the deployment zip |

---

## lambda-config.json

```json
{
  "lambdas": {
    "onboarding": {
      "function_name": "user-events-processor",
      "region": "us-east-1",
      "handler": "onboarding.lambda_function.lambda_handler"
    }
  }
}
```

Change `function_name` or `region` here to retarget the deployment without editing the workflow.

---

## What Gets Packaged

`scripts/build_onboarding_lambda.sh` copies two directories to the zip root:

```
dist/onboarding-lambda.zip
├── onboarding/          ←  services/onboarding_service/onboarding/
│   ├── lambda_function.py    ← AWS entry point
│   ├── handler.py
│   ├── registry.py
│   ├── __init__.py
│   └── v1/...
└── helper/              ←  helper/
    ├── utilities.py
    ├── event_publisher.py
    └── ...
```

Both must be at the root because `lambda_function.py` uses package-relative imports (`from . import handler`, `from helper.utilities import get_logger`).

No third-party deps are bundled — `boto3` is already provided by the Lambda runtime.

---

## AWS Setup (One-Time)

### Lambda function

The target function `user-events-processor` already exists in account `088971275490`, region `us-east-1`, runtime `python3.14`.

### IAM deployer user

A dedicated IAM user `github-onboarding-deployer` was created with a scoped policy — it can only update this one Lambda function:

```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:UpdateFunctionCode",
    "lambda:UpdateFunctionConfiguration",
    "lambda:GetFunction",
    "lambda:GetFunctionConfiguration"
  ],
  "Resource": "arn:aws:lambda:us-east-1:088971275490:function:user-events-processor"
}
```

### GitHub repository secrets

Two secrets must exist in the repo (**Settings → Secrets and variables → Actions**):

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Access key for `github-onboarding-deployer` |
| `AWS_SECRET_ACCESS_KEY` | Secret key for `github-onboarding-deployer` |

---

## Workflow Trigger Paths

The workflow only runs when a push to `main` touches one of these paths:

```yaml
paths:
  - 'services/onboarding_service/**'
  - 'helper/**'
  - 'scripts/build_onboarding_lambda.sh'
  - 'lambda-config.json'
  - '.github/workflows/deploy-lambda.yml'
```

Pushes that only modify docs, tests, or other services skip the workflow entirely.

---

## Verifying a Deployment

```bash
# Confirm handler and last-modified time
aws lambda get-function-configuration \
  --function-name user-events-processor \
  --region us-east-1 \
  --query '{Handler:Handler,LastModified:LastModified,CodeSize:CodeSize}' \
  --output table

# Tail live logs
aws logs tail /aws/lambda/user-events-processor --region us-east-1 --follow

# Test invoke with a UserCreated SQS record
aws lambda invoke \
  --function-name user-events-processor \
  --region us-east-1 \
  --payload '{"Records":[{"body":"{\"Message\":\"{\\\"event_type\\\":\\\"UserCreated\\\",\\\"user_id\\\":\\\"u1\\\",\\\"first_name\\\":\\\"Test\\\"}\"}"}]}' \
  /tmp/out.json && cat /tmp/out.json
```

---

## Adding a New Lambda Service

1. Add a `scripts/build_<service>_lambda.sh` following the same pattern as the onboarding one.
2. Add a new entry to `lambda-config.json`:
   ```json
   "email": {
     "function_name": "dev-email-service",
     "region": "us-east-1",
     "handler": "email_service.lambda_function.lambda_handler"
   }
   ```
3. Add a new job to `.github/workflows/deploy-lambda.yml` following the same four-step pattern (read config → build → auth → deploy).

---

## Troubleshooting

**Workflow didn't trigger after push**
Check that you changed a file matching the `paths:` filter above.

**`ResourceNotFoundException` in the Deploy step**
The `function_name` in `lambda-config.json` doesn't match any Lambda in your account. Run `aws lambda list-functions --query 'Functions[*].FunctionName'` to find the correct name.

**`InvalidSignatureException` or `AuthFailure`**
The GitHub secrets are wrong or expired. Recreate the access key:
```bash
aws iam create-access-key --user-name github-onboarding-deployer
```
Then update both secrets in the GitHub repo settings.

**Handler error (`Unable to import module`)**
The zip layout is wrong. Unzip locally and confirm `onboarding/` and `helper/` are at the root (not nested under a subdirectory):
```bash
bash scripts/build_onboarding_lambda.sh
unzip -l dist/onboarding-lambda.zip | head -20
```
