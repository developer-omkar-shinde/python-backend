#!/bin/bash

################################################################################
# ECS Startup Script
# Purpose: Start ECS services and wait for them to be ready
# Usage: ./startup_ecs.sh [--cluster CLUSTER_NAME] [--service SERVICE_NAME]
################################################################################

set -e

# Default values
CLUSTER_NAME="python-backend"
SERVICE_NAME="onboarding-service"
REGION="us-east-1"
DESIRED_COUNT=1
TIMEOUT=300  # 5 minutes
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALB_CONFIG_FILE="$SCRIPT_DIR/alb-config.json"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --cluster)
      CLUSTER_NAME="$2"
      shift 2
      ;;
    --service)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --desired-count)
      DESIRED_COUNT="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --cluster CLUSTER_NAME    ECS cluster name (default: backend-learning-cluster)"
      echo "  --service SERVICE_NAME    Service name (default: onboarding-service)"
      echo "  --region REGION           AWS region (default: eu-north-1)"
      echo "  --desired-count COUNT     Number of tasks to run (default: 1)"
      echo "  --help                    Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Helper functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Verify AWS CLI is installed
if ! command -v aws &> /dev/null; then
  log_error "AWS CLI is not installed. Please install it first."
  exit 1
fi

# Verify credentials
if ! aws sts get-caller-identity --region "$REGION" &> /dev/null; then
  log_error "AWS credentials not configured. Please run: aws configure"
  exit 1
fi

log_info "Starting ECS service..."
log_info "Cluster: $CLUSTER_NAME"
log_info "Service: $SERVICE_NAME"
log_info "Region: $REGION"
log_info "Desired tasks: $DESIRED_COUNT"
echo ""

# Step 1: Check if cluster exists
if ! aws ecs describe-clusters --clusters "$CLUSTER_NAME" --region "$REGION" 2>/dev/null | grep -q "$CLUSTER_NAME"; then
  log_error "Cluster '$CLUSTER_NAME' not found."
  exit 1
fi

log_success "Cluster found: $CLUSTER_NAME"
echo ""

# Step 2: Recreate load balancer if it was previously deleted by shutdown_ecs.sh --delete-alb
if [ -f "$ALB_CONFIG_FILE" ]; then
  log_info "Found ALB config file. Checking if load balancer needs to be recreated..."

  LB_NAME=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(d['LoadBalancer']['LoadBalancerName'])
")

  # Check if the ALB already exists
  EXISTING_LB_ARN=$(aws elbv2 describe-load-balancers \
    --names "$LB_NAME" \
    --region "$REGION" \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null || echo "")

  if [ -z "$EXISTING_LB_ARN" ] || [ "$EXISTING_LB_ARN" = "None" ]; then
    log_info "Recreating load balancer: $LB_NAME"

    # Extract values from saved config
    SUBNETS=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(' '.join(az['SubnetId'] for az in d['LoadBalancer']['AvailabilityZones']))
")

    SECURITY_GROUPS=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(' '.join(d['LoadBalancer']['SecurityGroups']))
")

    SCHEME=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(d['LoadBalancer']['Scheme'])
")

    LB_TYPE=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(d['LoadBalancer']['Type'])
")

    NEW_LB_ARN=$(aws elbv2 create-load-balancer \
      --name "$LB_NAME" \
      --type "$LB_TYPE" \
      --scheme "$SCHEME" \
      --subnets $SUBNETS \
      --security-groups $SECURITY_GROUPS \
      --region "$REGION" \
      --query 'LoadBalancers[0].LoadBalancerArn' \
      --output text)

    log_success "Load balancer created: $NEW_LB_ARN"
    log_info "Waiting for load balancer to become active..."

    aws elbv2 wait load-balancer-available \
      --load-balancer-arns "$NEW_LB_ARN" \
      --region "$REGION"

    log_success "Load balancer is active."

    # Recreate each listener pointing to the original target group
    LISTENER_COUNT=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(len(d['Listeners']))
")

    for i in $(seq 0 $((LISTENER_COUNT - 1))); do
      PORT=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(d['Listeners'][$i]['Port'])
")
      PROTOCOL=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
print(d['Listeners'][$i]['Protocol'])
")
      TG_ARN=$(python3 -c "
import json
with open('$ALB_CONFIG_FILE') as f:
    d = json.load(f)
actions = d['Listeners'][$i]['DefaultActions']
for a in actions:
    if 'ForwardConfig' in a:
        print(a['ForwardConfig']['TargetGroups'][0]['TargetGroupArn'])
        break
    elif 'TargetGroupArn' in a:
        print(a['TargetGroupArn'])
        break
")

      aws elbv2 create-listener \
        --load-balancer-arn "$NEW_LB_ARN" \
        --protocol "$PROTOCOL" \
        --port "$PORT" \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
        --region "$REGION" \
        --output json > /dev/null

      log_success "Listener restored: $PROTOCOL:$PORT"
    done

    NEW_DNS=$(aws elbv2 describe-load-balancers \
      --load-balancer-arns "$NEW_LB_ARN" \
      --region "$REGION" \
      --query 'LoadBalancers[0].DNSName' \
      --output text)

    log_success "Load balancer DNS: $NEW_DNS"
    log_info "Note: DNS name may have changed. Update your Route53 / DNS records if needed."
    echo ""
  else
    log_info "Load balancer '$LB_NAME' already exists. Skipping recreation."
    echo ""
  fi
fi

# Step 3: Get service information
log_info "Retrieving service information..."

SERVICE_INFO=$(aws ecs describe-services \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME" \
  --region "$REGION" \
  --query 'services[0]' \
  --output json 2>/dev/null || echo "")

if [ -z "$SERVICE_INFO" ] || [ "$SERVICE_INFO" = "null" ]; then
  log_error "Service '$SERVICE_NAME' not found in cluster."
  exit 1
fi

CURRENT_DESIRED=$(echo "$SERVICE_INFO" | grep -o '"desiredCount":[0-9]*' | grep -o '[0-9]*')
CURRENT_RUNNING=$(echo "$SERVICE_INFO" | grep -o '"runningCount":[0-9]*' | grep -o '[0-9]*')

log_success "Service found: $SERVICE_NAME"
log_info "Current state: Running=$CURRENT_RUNNING, Desired=$CURRENT_DESIRED"
echo ""

# Step 4: Update desired count
log_info "Updating service to desired count: $DESIRED_COUNT"

aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$SERVICE_NAME" \
  --desired-count "$DESIRED_COUNT" \
  --region "$REGION" \
  --output json > /dev/null

log_success "Service update initiated"
echo ""

# Step 5: Wait for service to stabilize
log_info "Waiting for service to stabilize (up to 5 minutes)..."
START_TIME=$(date +%s)

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))

  # Check timeout
  if [ $ELAPSED -gt $TIMEOUT ]; then
    log_warning "Timeout waiting for service to stabilize"
    break
  fi

  # Get service status
  SERVICE_STATUS=$(aws ecs describe-services \
    --cluster "$CLUSTER_NAME" \
    --services "$SERVICE_NAME" \
    --region "$REGION" \
    --query 'services[0]' \
    --output json)

  RUNNING=$(echo "$SERVICE_STATUS" | grep -o '"runningCount":[0-9]*' | grep -o '[0-9]*')
  DESIRED=$(echo "$SERVICE_STATUS" | grep -o '"desiredCount":[0-9]*' | grep -o '[0-9]*')
  DEPLOYMENTS=$(echo "$SERVICE_STATUS" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)

  log_info "Tasks: Running=$RUNNING, Desired=$DESIRED (${ELAPSED}s elapsed)"

  # Check if all tasks are running
  if [ "$RUNNING" = "$DESIRED" ] && [ "$DESIRED" -gt 0 ]; then
    log_success "All tasks are running!"
    break
  fi

  # Wait before checking again
  sleep 5
done

echo ""

# Step 6: Display final status
log_info "Retrieving final service status..."

FINAL_STATUS=$(aws ecs describe-services \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME" \
  --region "$REGION" \
  --query 'services[0]' \
  --output json)

FINAL_RUNNING=$(echo "$FINAL_STATUS" | grep -o '"runningCount":[0-9]*' | grep -o '[0-9]*')
FINAL_DESIRED=$(echo "$FINAL_STATUS" | grep -o '"desiredCount":[0-9]*' | grep -o '[0-9]*')
FINAL_PENDING=$(echo "$FINAL_STATUS" | grep -o '"pendingCount":[0-9]*' | grep -o '[0-9]*')

echo ""
echo "═══════════════════════════════════════════════════════════════"
log_success "Service Startup Status"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Cluster:        $CLUSTER_NAME"
echo "Service:        $SERVICE_NAME"
echo "Region:         $REGION"
echo ""
echo "Task Status:"
echo "  Running:      $FINAL_RUNNING"
echo "  Pending:      $FINAL_PENDING"
echo "  Desired:      $FINAL_DESIRED"
echo ""

if [ "$FINAL_RUNNING" = "$FINAL_DESIRED" ]; then
  log_success "Service is running successfully!"
  echo ""
  log_info "To get the load balancer URL:"
  echo "  aws elbv2 describe-load-balancers --region $REGION --query 'LoadBalancers[].DNSName'"
  echo ""
else
  log_warning "Service is not fully running yet"
  echo ""
  log_info "Check task logs:"
  echo "  aws logs tail /ecs/backend-learning --follow --region $REGION"
  echo ""
fi
