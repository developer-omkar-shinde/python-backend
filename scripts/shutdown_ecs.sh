#!/bin/bash

################################################################################
# ECS Shutdown Script
# Purpose: Stop all running ECS services and tasks to save AWS credits
# Usage: ./shutdown_ecs.sh [--cluster CLUSTER_NAME] [--region REGION]
################################################################################

set -e

# Default values
CLUSTER_NAME="python-backend"
REGION="us-east-1"
VERBOSE=false
DELETE_ALB=false
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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
    --region)
      REGION="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --delete-alb)
      DELETE_ALB=true
      shift
      ;;
    --help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --cluster CLUSTER_NAME   ECS cluster name (default: backend-learning-cluster)"
      echo "  --region REGION          AWS region (default: eu-north-1)"
      echo "  --verbose                Enable verbose output"
      echo "  --delete-alb             Delete load balancer and save config for later restore (saves ~\$0.008/hr)"
      echo "  --help                   Show this help message"
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

log_info "Starting ECS shutdown process..."
log_info "Cluster: $CLUSTER_NAME"
log_info "Region: $REGION"
echo ""

# Step 1: Check if cluster exists
if ! aws ecs describe-clusters --clusters "$CLUSTER_NAME" --region "$REGION" 2>/dev/null | grep -q "$CLUSTER_NAME"; then
  log_warning "Cluster '$CLUSTER_NAME' not found."
  exit 0
fi

log_success "Cluster found: $CLUSTER_NAME"
echo ""

# Step 2: Get all services in the cluster
log_info "Fetching services from cluster..."
SERVICES=$(aws ecs list-services --cluster "$CLUSTER_NAME" --region "$REGION" --query 'serviceArns[]' --output text)

if [ -z "$SERVICES" ]; then
  log_warning "No services found in cluster."
else
  log_success "Found services: $(echo $SERVICES | wc -w) service(s)"
  echo ""
  
  # Step 3: Scale down each service to 0
  log_info "Scaling down services to 0 desired count..."
  for SERVICE_ARN in $SERVICES; do
    SERVICE_NAME=$(echo "$SERVICE_ARN" | awk -F'/' '{print $NF}')
    
    log_info "Scaling down service: $SERVICE_NAME"
    
    aws ecs update-service \
      --cluster "$CLUSTER_NAME" \
      --service "$SERVICE_ARN" \
      --desired-count 0 \
      --region "$REGION" \
      --output json > /dev/null
    
    log_success "Service scaled down: $SERVICE_NAME"
  done
  
  echo ""
  log_success "All services scaled down successfully!"
fi

echo ""

# Step 4: List any running tasks
log_info "Checking for running tasks..."
RUNNING_TASKS=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --region "$REGION" --query 'taskArns[]' --output text)

if [ -z "$RUNNING_TASKS" ]; then
  log_success "No running tasks found."
else
  log_warning "Found $(echo $RUNNING_TASKS | wc -w) running task(s)."
  log_info "Stopping all running tasks..."
  
  for TASK_ARN in $RUNNING_TASKS; do
    TASK_ID=$(echo "$TASK_ARN" | awk -F'/' '{print $NF}')
    
    aws ecs stop-task \
      --cluster "$CLUSTER_NAME" \
      --task "$TASK_ARN" \
      --reason "Manual shutdown via script" \
      --region "$REGION" \
      --output json > /dev/null
    
    if [ "$VERBOSE" = true ]; then
      log_success "Task stopped: $TASK_ID"
    fi
  done
  
  log_success "All running tasks stopped!"
fi

echo ""

# Step 5: Handle Application Load Balancers
log_info "Checking for Application Load Balancers..."

LOAD_BALANCERS=$(aws elbv2 describe-load-balancers \
  --region "$REGION" \
  --query "LoadBalancers[?contains(LoadBalancerName, 'backend-learning')].LoadBalancerArn" \
  --output text)

ALB_DELETED=false

if [ -z "$LOAD_BALANCERS" ]; then
  log_info "No load balancers found with pattern 'backend-learning'."
else
  for LB_ARN in $LOAD_BALANCERS; do
    LB_NAME=$(aws elbv2 describe-load-balancers \
      --load-balancer-arns "$LB_ARN" \
      --region "$REGION" \
      --query 'LoadBalancers[0].LoadBalancerName' \
      --output text)

    log_info "Found load balancer: $LB_NAME"

    if [ "$DELETE_ALB" = true ]; then
      # Save full ALB config so startup_ecs.sh can recreate it
      log_info "Saving ALB config to: $SCRIPT_DIR/alb-config.json"

      LB_DETAIL=$(aws elbv2 describe-load-balancers \
        --load-balancer-arns "$LB_ARN" \
        --region "$REGION" \
        --query 'LoadBalancers[0]' \
        --output json)

      LISTENERS=$(aws elbv2 describe-listeners \
        --load-balancer-arn "$LB_ARN" \
        --region "$REGION" \
        --output json)

      python3 -c "
import json, sys
lb = json.loads(sys.argv[1])
listeners = json.loads(sys.argv[2])
config = {'LoadBalancer': lb, 'Listeners': listeners['Listeners']}
with open('$SCRIPT_DIR/alb-config.json', 'w') as f:
    json.dump(config, f, indent=2, default=str)
print('Config saved.')
" "$LB_DETAIL" "$LISTENERS"

      log_success "Config saved to: $SCRIPT_DIR/alb-config.json"

      log_info "Deleting load balancer: $LB_NAME"
      aws elbv2 delete-load-balancer \
        --load-balancer-arn "$LB_ARN" \
        --region "$REGION" > /dev/null

      log_success "Load balancer deleted: $LB_NAME"
      log_info "Note: Target groups are kept (free when empty) so ECS service config stays intact."
      ALB_DELETED=true
    else
      # Just deregister targets — ALB keeps running (still billed per hour)
      TARGET_GROUPS=$(aws elbv2 describe-target-groups \
        --load-balancer-arn "$LB_ARN" \
        --region "$REGION" \
        --query 'TargetGroups[].TargetGroupArn' \
        --output text)

      for TG_ARN in $TARGET_GROUPS; do
        TG_NAME=$(echo "$TG_ARN" | awk -F'/' '{print $NF}')
        TARGETS=$(aws elbv2 describe-target-health \
          --target-group-arn "$TG_ARN" \
          --region "$REGION" \
          --query 'TargetHealthDescriptions[].Target.Id' \
          --output text)

        if [ ! -z "$TARGETS" ]; then
          log_info "Deregistering targets from: $TG_NAME"
          for TARGET_ID in $TARGETS; do
            aws elbv2 deregister-targets \
              --target-group-arn "$TG_ARN" \
              --targets Id="$TARGET_ID" \
              --region "$REGION" \
              --output json > /dev/null
          done
          log_success "Targets deregistered from: $TG_NAME"
        fi
      done

      echo ""
      log_warning "Load balancer '$LB_NAME' is still running and billing at ~\$0.008/hr (~\$5.76/mo)."
      log_info "To delete it and save costs, rerun with: ./shutdown_ecs.sh --delete-alb"
    fi
  done
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
log_success "ECS Shutdown Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  • All services scaled to 0 desired count"
echo "  • All running tasks stopped"
if [ "$ALB_DELETED" = true ]; then
  echo "  • Load balancer deleted (config saved to scripts/alb-config.json)"
  echo "  • Target groups kept intact (no cost when empty)"
else
  echo "  • Targets deregistered from load balancers (ALB still billing)"
  echo "  • Tip: use --delete-alb flag to also delete the load balancer"
fi
echo ""
