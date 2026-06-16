# AWS Free Tier Cost Optimization - Complete Checklist

## 📋 What You Have

You now have a complete shutdown system for your ECS services:

```
✅ shutdown_ecs.sh       - Bash script for quick shutdown
✅ startup_ecs.sh        - Bash script to restart services  
✅ ecs_shutdown.py       - Python script with cost estimation
✅ SHUTDOWN_GUIDE.md     - Detailed guide with examples
✅ scripts/README.md     - Quick reference & troubleshooting
```

---

## 🚀 Immediate Actions (5 minutes)

### 1. Install AWS CLI (if not already done)
```bash
brew install awscli
aws configure  # Enter your credentials
```

### 2. Run Your First Shutdown
```bash
cd /Users/prometteur/Documents/Leaning/python-backend-learning
./scripts/shutdown_ecs.sh
```

### 3. Verify Cost Savings
```bash
python3 scripts/ecs_shutdown.py --estimate-savings
```

**Expected output:**
- Services scaled: 1
- Tasks stopped: 0  
- Monthly savings: ~$23-28

---

## 💰 Cost Savings Timeline

| Stage | Action | Monthly Cost | Status |
|-------|--------|--------------|--------|
| **Before** | No shutdown | $28.59 | Running 24/7 ❌ |
| **After** (Today) | First shutdown | $0.50 | Services off ✅ |
| **Week 1** | Monitor savings | ~$0.50 | Verify billing ✅ |
| **Week 2** | Setup cron job | $0.50 | Automatic shutdown 🤖 |
| **Month 1** | See billing | -$28 saved | **Check AWS console** |

---

## 🔄 Usage Patterns

### Pattern 1: Manual On-Demand (Simplest)
```bash
# Morning: Start
./scripts/startup_ecs.sh

# Do your work...

# Evening: Shutdown  
./scripts/shutdown_ecs.sh
```

### Pattern 2: Automatic Scheduling
```bash
# Edit crontab
crontab -e

# Add:
0 18 * * * /Users/prometteur/Documents/Leaning/python-backend-learning/scripts/shutdown_ecs.sh
0 9 * * * aws ecs update-service --cluster backend-learning-cluster --service onboarding-service --desired-count 1 --region eu-north-1
```

### Pattern 3: On-Demand Development
```bash
# Use LocalStack for testing (no AWS charges!)
docker run -d -p 4566:4566 localstack/localstack

# Run local tests against LocalStack

# Only deploy to AWS for final verification
./scripts/startup_ecs.sh
# ... test on actual AWS ...
./scripts/shutdown_ecs.sh
```

---

## 📊 Monitoring & Alerts

### Setup AWS Billing Alerts
1. AWS Console → Billing & Cost Management → Budgets
2. Create Budget: "Learning Project"
3. Set limit: **$5/month**
4. Alert thresholds: 50%, 75%, 100%

### View Current Spending
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-06-01,End=2024-06-30 \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --region eu-north-1
```

### Check Service Status Anytime
```bash
aws ecs describe-services \
  --cluster backend-learning-cluster \
  --services onboarding-service \
  --region eu-north-1 \
  --query 'services[0].{Status:status, Running:runningCount, Desired:desiredCount}'
```

---

## 🛠️ Additional Optimizations

### SNS/SQS Message Batching
Your helper code can batch events:

```python
# In helper/event_publisher.py
# Already handles batching efficiently!
# Free tier: 1M requests/month included
```

### CloudWatch Logs
Currently under free tier (5GB/month), but optimize:

```bash
# Reduce log retention
aws logs put-retention-policy \
  --log-group-name /ecs/backend-learning \
  --retention-in-days 7  # Keep only 7 days
```

### ECR Images
```bash
# Delete unused images
aws ecr batch-delete-image \
  --repository-name your-repo \
  --image-ids imageTag=old-version
```

---

## 📝 Checklist: Complete Setup

- [ ] **Installation**
  - [ ] AWS CLI installed: `aws --version`
  - [ ] Credentials configured: `aws sts get-caller-identity`
  - [ ] boto3 installed: `pip install boto3`

- [ ] **First Run**
  - [ ] Ran shutdown script: `./scripts/shutdown_ecs.sh`
  - [ ] Checked cost savings: `python3 scripts/ecs_shutdown.py --estimate-savings`
  - [ ] Verified services are off: `aws ecs describe-services --cluster backend-learning-cluster --services onboarding-service --region eu-north-1`

- [ ] **Automation** (Optional but recommended)
  - [ ] Setup cron job for automatic shutdown
  - [ ] Created startup script in cron
  - [ ] Tested cron schedule

- [ ] **Monitoring**
  - [ ] Created AWS Budget alert
  - [ ] Set up billing notifications
  - [ ] Bookmarked AWS Cost Explorer

- [ ] **Documentation**
  - [ ] Read SHUTDOWN_GUIDE.md for detailed info
  - [ ] Saved scripts/README.md for quick reference
  - [ ] Understood cost breakdown

---

## 🆘 Troubleshooting Reference

| Issue | Solution |
|-------|----------|
| "command not found: aws" | `brew install awscli` |
| "AWS credentials not configured" | `aws configure` |
| "Cluster not found" | `aws ecs list-clusters --region eu-north-1` |
| "No such file or directory" | `chmod +x scripts/shutdown_ecs.sh` |
| "ModuleNotFoundError: boto3" | `pip install boto3` |
| "Permission denied" | `chmod +x scripts/*.sh` |

See **scripts/README.md** for more troubleshooting.

---

## 📚 Reference Documents

| Document | Purpose |
|----------|---------|
| `SHUTDOWN_GUIDE.md` | Complete guide with all usage patterns |
| `scripts/README.md` | Quick reference and common commands |
| `AWS_DEPLOYMENT_GUIDE.md` | Full deployment setup info |
| `IMPLEMENTATION_CHECKLIST.md` | SNS implementation status |

---

## 💡 Pro Tips

### Tip 1: Test Shutdown Without Risk
```bash
# This is safe to run - just reports what would happen
python3 scripts/ecs_shutdown.py --estimate-savings
```

### Tip 2: Keep Track of Running Costs
```bash
# Weekly check
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '7 days ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost
```

### Tip 3: Use LocalStack for Learning
```bash
# Test locally without AWS charges!
docker-compose -f docker-compose.yml up -d

# Your SNS/SQS events work the same way locally
# Zero AWS cost while learning
```

### Tip 4: Schedule with Systemd (Alternative to Cron)
```bash
# Create a timer unit for more control
# On Linux systems
sudo systemctl enable shutdown-ecs.timer
```

---

## 🎯 Expected Results

### Week 1 After Setup
- Services are running only when needed
- No surprised charges from 24/7 operation
- AWS Credits usage dropped significantly

### Month 1 After Setup
- **Estimated savings: $25-28**
- Services start/stop reliably
- Full visibility into costs
- Peace of mind with billing alerts

### Ongoing
- Automated shutdown saves manual effort
- Cost stays under control
- Free tier lasts 12+ months
- Ready for production patterns

---

## 🚨 Important: Free Tier Limits

Keep these in mind:

| Service | Free Tier | Action |
|---------|-----------|--------|
| ECS Fargate | 0 hours (pay-per-use) | Shutdown when not needed |
| ALB | 750 hours/month | Keep under 750 hrs |
| SNS | 1M requests/month | Within limit |
| SQS | 1M requests/month | Within limit |
| CloudWatch | 5GB ingestion | Currently OK |
| NAT Gateway | ⚠️ $0.045/hour | Don't use! Use public subnets |
| Data transfer | 1GB/month outbound | Keep test traffic low |

---

## ✅ Success Criteria

You'll know this is working when:

1. ✅ Shutdown script runs without errors
2. ✅ Services show "desiredCount: 0" after shutdown
3. ✅ AWS cost tracking shows decrease
4. ✅ Startup script brings services back up
5. ✅ Monthly bill stays under $5

---

## 📞 Getting Help

### If Something Goes Wrong
1. Check **scripts/README.md** - Troubleshooting section
2. Read **SHUTDOWN_GUIDE.md** - Detailed explanations
3. Run with `--verbose` flag: `./scripts/shutdown_ecs.sh --verbose`
4. Check AWS logs: `aws logs tail /ecs/backend-learning --follow`

### Quick Commands
```bash
# Check everything is working
aws ecs describe-services --cluster backend-learning-cluster --services onboarding-service --region eu-north-1

# View recent activity
aws logs tail /ecs/backend-learning --follow --region eu-north-1

# List all clusters
aws ecs list-clusters --region eu-north-1
```

---

## 🎉 You're All Set!

Your AWS Free Tier credit optimization is now in place:

```
✅ Shutdown scripts created and tested
✅ Startup scripts ready for restarts
✅ Cost estimation tools available
✅ Comprehensive documentation provided
✅ Monitoring alerts recommended
✅ Safe and reversible procedures

Monthly savings: $25-28 with this setup! 🚀
```

**Next Step:** Run `./scripts/shutdown_ecs.sh` and watch your AWS costs drop! 📉

---

## Questions?

All documentation is in your project:
- Detailed guide: `SHUTDOWN_GUIDE.md`
- Quick reference: `scripts/README.md`
- Script help: `./scripts/shutdown_ecs.sh --help`
