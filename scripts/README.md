# ECS Shutdown Scripts - Quick Reference

## Files Created

```
scripts/
├── shutdown_ecs.sh      ← Shutdown all services & tasks (Bash)
├── startup_ecs.sh       ← Start services (Bash)
├── ecs_shutdown.py      ← Advanced shutdown with cost estimation (Python)
└── README.md            ← This file
```

---

## Quick Start (Copy & Paste)

### Step 1: Install Dependencies
```bash
# AWS CLI
brew install awscli           # macOS
sudo apt install awscli       # Linux

# Configure credentials
aws configure

# Python dependencies (optional)
pip install boto3
```

### Step 2: Shutdown Services
```bash
cd /Users/prometteur/Documents/Leaning/python-backend-learning

# Bash version (simple, fast)
./scripts/shutdown_ecs.sh

# Python version (with cost info)
python3 scripts/ecs_shutdown.py --estimate-savings
```

### Step 3: Restart Services Later
```bash
./scripts/startup_ecs.sh
```

---

## Common Commands

### Shutdown

| Command | Purpose |
|---------|---------|
| `./scripts/shutdown_ecs.sh` | Stop all services (default cluster) |
| `./scripts/shutdown_ecs.sh --cluster my-cluster` | Stop specific cluster |
| `./scripts/shutdown_ecs.sh --region us-east-1` | Shutdown in different region |
| `./scripts/shutdown_ecs.sh --verbose` | Show detailed output |

### Startup

| Command | Purpose |
|---------|---------|
| `./scripts/startup_ecs.sh` | Start onboarding-service |
| `./scripts/startup_ecs.sh --desired-count 2` | Start 2 task instances |
| `./scripts/startup_ecs.sh --service my-service` | Start different service |

### Python Script (Advanced)

| Command | Purpose |
|---------|---------|
| `python3 scripts/ecs_shutdown.py` | Shutdown with detailed logging |
| `python3 scripts/ecs_shutdown.py --estimate-savings` | Show cost savings WITHOUT shutting down |
| `python3 scripts/ecs_shutdown.py --verbose` | Enable debug logging |

### Manual AWS CLI (When Needed)

```bash
# See all services
aws ecs list-services --cluster backend-learning-cluster --region eu-north-1

# Scale down one service
aws ecs update-service --cluster backend-learning-cluster \
  --service onboarding-service --desired-count 0 --region eu-north-1

# Scale up one service
aws ecs update-service --cluster backend-learning-cluster \
  --service onboarding-service --desired-count 1 --region eu-north-1

# See service status
aws ecs describe-services --cluster backend-learning-cluster \
  --services onboarding-service --region eu-north-1

# View logs
aws logs tail /ecs/backend-learning --follow --region eu-north-1

# Get load balancer URL
aws elbv2 describe-load-balancers --region eu-north-1 \
  --query 'LoadBalancers[].{Name:LoadBalancerName,URL:DNSName}'
```

---

## Automation Ideas

### Schedule Daily Shutdown (Cron)
```bash
# Edit crontab
crontab -e

# Add this line (shutdown at 6 PM daily)
0 18 * * * /Users/prometteur/Documents/Leaning/python-backend-learning/scripts/shutdown_ecs.sh >> /tmp/ecs_shutdown.log 2>&1

# Add this line (startup at 9 AM daily)
0 9 * * * aws ecs update-service --cluster backend-learning-cluster --service onboarding-service --desired-count 1 --region eu-north-1
```

### Monitor with CloudWatch Alerts
1. Go to AWS Console → Billing & Cost Management
2. Create Budget with $5 limit
3. Alert at 50%, 75%, 100%

---

## Cost Saving Impact

### Before Shutdown (24/7)
```
ECS Fargate:        $4.89/month
ALB:               $16.20/month
CloudWatch:         $2.50/month
Data Transfer:      ~$5/month
─────────────────────────────
Total:            ~$28.59/month ❌
```

### After Shutdown
```
ECS Fargate:        $0/month
ALB:                $0/month (if deleted)
CloudWatch:        $0.50/month (free tier)
Data Transfer:      $0/month
─────────────────────────────
Total:             $0.50/month ✅ (12+ months of free tier)
```

### With Smart Scheduling (2 hrs/day)
```
ECS Fargate:       $0.33/month
ALB:               $1.08/month
CloudWatch:        $2.50/month
─────────────────────────────
Total:             $3.91/month ✅ (still within free tier)
```

---

## Troubleshooting

### "command not found: aws"
```bash
brew install awscli  # or sudo apt install awscli
```

### "AWS credentials not configured"
```bash
aws configure
# Enter Access Key ID and Secret Access Key from AWS IAM
```

### "Cluster not found"
```bash
aws ecs list-clusters --region eu-north-1
# Use correct cluster name from output
```

### "ModuleNotFoundError: No module named 'boto3'"
```bash
pip install boto3
```

### Scripts don't seem to do anything
```bash
# Enable verbose output to see what's happening
./scripts/shutdown_ecs.sh --verbose
python3 scripts/ecs_shutdown.py --verbose

# Verify services exist
aws ecs list-services --cluster backend-learning-cluster --region eu-north-1
```

---

## Safety & Recovery

### ✅ Safe to Run
- Can run multiple times (won't break)
- Won't delete data or resources
- Fully reversible

### ✅ To Reverse Shutdown
```bash
./scripts/startup_ecs.sh
# Wait 2-3 minutes for tasks to start
```

### ✅ Data Safety
- Databases are separate (not stopped by these scripts)
- Configuration preserved
- Task definitions unchanged

---

## Documentation

For detailed information, see:
- **`SHUTDOWN_GUIDE.md`** - Complete guide with patterns and examples
- **`AWS_DEPLOYMENT_GUIDE.md`** - Full deployment setup
- **Script headers** - Built-in comments

---

## Getting Help

```bash
# Show help for any script
./scripts/shutdown_ecs.sh --help
./scripts/startup_ecs.sh --help
python3 scripts/ecs_shutdown.py --help

# Or read the script source
cat scripts/shutdown_ecs.sh
cat scripts/ecs_shutdown.py
```

---

## Next Steps

1. ✅ Run one of the scripts to shutdown your services
2. ✅ Monitor costs for a few days
3. ✅ Setup cron job for automatic shutdown if desired
4. ✅ Check AWS billing dashboard to see savings

**Estimated time to save $28/month: ~2 minutes of setup!**



# Shutdown
./scripts/shutdown_ecs.sh

# Startup
./scripts/startup_ecs.sh

# Check status
aws ecs describe-services --cluster python-backend --services onboarding-service --region us-east-1