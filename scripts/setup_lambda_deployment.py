#!/usr/bin/env python3
"""
Lambda Deployment Setup Helper

This script helps set up AWS credentials and verify Lambda functions for GitHub Actions deployment.
Usage: python setup_lambda_deployment.py
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Optional


def run_command(cmd: list[str], capture: bool = True) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    try:
        if capture:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd)
            return result.returncode, ""
    except Exception as e:
        return 1, str(e)


def check_aws_cli() -> bool:
    """Verify AWS CLI is installed and configured."""
    print("✓ Checking AWS CLI...")
    code, output = run_command(["aws", "--version"])
    if code != 0:
        print("✗ AWS CLI not found. Install from: https://aws.amazon.com/cli/")
        return False
    print(f"  {output.strip()}")
    return True


def get_aws_account_id() -> Optional[str]:
    """Get AWS account ID."""
    print("\n✓ Getting AWS account ID...")
    code, output = run_command(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"])
    if code != 0:
        print("✗ Failed to get AWS account ID. Ensure AWS credentials are configured.")
        print("  Configure with: aws configure")
        return None
    account_id = output.strip()
    print(f"  Account ID: {account_id}")
    return account_id


def create_iam_user() -> Optional[tuple[str, str]]:
    """Create IAM user for GitHub Actions."""
    print("\n✓ Creating IAM user 'github-lambda-deployer'...")
    username = "github-lambda-deployer"

    # Check if user already exists
    code, _ = run_command(["aws", "iam", "get-user", "--user-name", username])
    if code == 0:
        print(f"  User '{username}' already exists.")
        response = input("  Rotate access keys? (y/n): ").lower()
        if response != "y":
            print("  Skipping user creation.")
            return None
        # Delete old keys
        code, output = run_command(["aws", "iam", "list-access-keys", "--user-name", username, "--query", "AccessKeyMetadata[0].AccessKeyId", "--output", "text"])
        if code == 0 and output.strip():
            delete_code, _ = run_command(["aws", "iam", "delete-access-key", "--user-name", username, "--access-key-id", output.strip()])
            if delete_code == 0:
                print(f"  Deleted old access key.")

    else:
        # Create new user
        code, output = run_command(["aws", "iam", "create-user", "--user-name", username])
        if code != 0:
            print(f"✗ Failed to create IAM user: {output}")
            return None
        print(f"  Created user: {username}")

    # Attach Lambda policy
    print("  Attaching Lambda policy...")
    policy_arn = "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
    code, _ = run_command(["aws", "iam", "attach-user-policy", "--user-name", username, "--policy-arn", policy_arn])
    if code != 0:
        print(f"✗ Failed to attach policy")
        return None
    print("  Policy attached.")

    # Create access keys
    print("  Creating access keys...")
    code, output = run_command(["aws", "iam", "create-access-key", "--user-name", username])
    if code != 0:
        print(f"✗ Failed to create access keys: {output}")
        return None

    try:
        creds = json.loads(output)
        access_key = creds["AccessKey"]["AccessKeyId"]
        secret_key = creds["AccessKey"]["SecretAccessKey"]
        print(f"  Access Key ID: {access_key}")
        print(f"  Secret Key: (hidden for security)")
        return access_key, secret_key
    except Exception as e:
        print(f"✗ Failed to parse credentials: {e}")
        return None


def list_lambda_functions() -> list[str]:
    """List all Lambda functions in the account."""
    print("\n✓ Fetching Lambda functions...")
    code, output = run_command(["aws", "lambda", "list-functions", "--query", "Functions[*].FunctionName", "--output", "text"])
    if code != 0:
        print("✗ Failed to list Lambda functions")
        return []
    
    functions = output.strip().split()
    if not functions:
        print("  No Lambda functions found.")
    else:
        print(f"  Found {len(functions)} Lambda function(s):")
        for func in sorted(functions):
            print(f"    - {func}")
    return functions


def verify_lambda_configs(functions: list[str]) -> bool:
    """Verify Lambda configurations in lambda-config.json."""
    print("\n✓ Verifying Lambda configurations...")
    
    config_file = Path("lambda-config.json")
    if not config_file.exists():
        print("✗ lambda-config.json not found")
        return False

    with open(config_file) as f:
        config = json.load(f)

    all_valid = True
    for service_name, service_config in config.get("lambdas", {}).items():
        func_name = service_config.get("function_name")
        if func_name not in functions:
            print(f"✗ Lambda '{func_name}' (for {service_name}) not found in AWS")
            all_valid = False
        else:
            print(f"✓ Lambda '{func_name}' (for {service_name}) exists")

    return all_valid


def create_lambda_function(account_id: str, func_name: str, service_type: str) -> bool:
    """Create a Lambda function in AWS."""
    print(f"\n✓ Creating Lambda function: {func_name}")

    role_arn = f"arn:aws:iam::{account_id}:role/lambda-execution-role"

    # Create a minimal placeholder zip
    code, _ = run_command(["python3", "-c", """
import zipfile
with zipfile.ZipFile('/tmp/placeholder.zip', 'w') as z:
    z.writestr('lambda_function.py', 'def lambda_handler(event, context):\\n    return {"statusCode": 200}')
"""])

    if code != 0:
        print("✗ Failed to create placeholder zip")
        return False

    cmd = [
        "aws", "lambda", "create-function",
        "--function-name", func_name,
        "--runtime", "python3.11",
        "--role", role_arn,
        "--handler", "lambda_function.lambda_handler",
        "--zip-file", "fileb:///tmp/placeholder.zip",
        "--timeout", "300",
        "--memory-size", "512"
    ]

    code, output = run_command(cmd)
    if code != 0:
        if "already exists" in output:
            print(f"  Lambda '{func_name}' already exists.")
            return True
        print(f"✗ Failed to create Lambda: {output}")
        return False

    print(f"  Created Lambda: {func_name}")
    return True


def print_setup_instructions(access_key: str, secret_key: str):
    """Print GitHub Actions setup instructions."""
    print("\n" + "="*70)
    print("SETUP INSTRUCTIONS FOR GITHUB ACTIONS")
    print("="*70)
    print("""
1. Go to your GitHub repository
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Create these two secrets:

   Secret 1:
   Name: AWS_ACCESS_KEY_ID
   Value: """)
    print(f"         {access_key}")
    print("""
   Secret 2:
   Name: AWS_SECRET_ACCESS_KEY
   Value: (copy and paste the secret key shown in setup output)
       """)
    print(f"         {secret_key}")
    print("""
5. Save both secrets
6. Push your code to main branch
7. Watch deployment in Actions tab!

""")


def main():
    """Main setup flow."""
    print("="*70)
    print("LAMBDA DEPLOYMENT SETUP")
    print("="*70)

    # Check prerequisites
    if not check_aws_cli():
        sys.exit(1)

    account_id = get_aws_account_id()
    if not account_id:
        sys.exit(1)

    # List existing functions
    functions = list_lambda_functions()

    # Optionally create IAM user
    print("\n" + "-"*70)
    setup_iam = input("Set up GitHub Actions IAM user? (y/n): ").lower()
    
    access_key = None
    secret_key = None
    
    if setup_iam == "y":
        result = create_iam_user()
        if result:
            access_key, secret_key = result
        else:
            print("Skipping IAM user setup.")

    # Create missing Lambda functions
    print("\n" + "-"*70)
    setup_lambdas = input("Create missing Lambda functions? (y/n): ").lower()
    
    if setup_lambdas == "y":
        config_file = Path("lambda-config.json")
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
            
            for service_name, service_config in config.get("lambdas", {}).items():
                func_name = service_config.get("function_name")
                if func_name not in functions:
                    if create_lambda_function(account_id, func_name, service_name):
                        functions.append(func_name)

    # Verify configurations
    print("\n" + "-"*70)
    if verify_lambda_configs(functions):
        print("✓ All Lambda configurations are valid!")
    else:
        print("⚠ Some Lambda functions are missing. Please create them manually or rerun this script.")

    # Print setup instructions if we created IAM user
    if access_key and secret_key:
        print_setup_instructions(access_key, secret_key)

    print("="*70)
    print("SETUP COMPLETE!")
    print("="*70)
    print("""
Next steps:
1. Configure GitHub secrets (if not done)
2. Push a commit to main branch
3. Watch Actions tab for deployment

For more info, see: LAMBDA_DEPLOYMENT_GUIDE.md
""")


if __name__ == "__main__":
    main()
