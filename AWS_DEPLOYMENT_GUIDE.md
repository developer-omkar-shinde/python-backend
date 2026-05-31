# FastAPI to AWS — Complete Deployment Guide

This guide walks you through everything needed to take a Python FastAPI application from local development to a live AWS deployment using Docker, ECR, and ECS Fargate. No prior knowledge of Docker or AWS required.

---

## Table of Contents

1. [Project Overview](#s1)
2. [Project Structure](#s2)
3. [The Application Code](#s3)
4. [What is Docker?](#s4)
5. [Install Docker](#s5)
6. [Prepare Files for Docker](#s6)
7. [Build and Run Docker Locally](#s7)
8. [AWS Key Concepts](#s8)
9. [Create AWS Account and IAM User](#s9)
10. [Install and Configure AWS CLI](#s10)
11. [Push Docker Image to ECR](#s11)
12. [Deploy to ECS Fargate](#s12)
13. [Day-to-Day Workflow](#s13)
14. [Resources and URLs](#s14)

---

<a id="s1"></a>
## 1. Project Overview

We have a small Python FastAPI application that exposes a few HTTP endpoints. The goal is to:

- Run it locally for development
- Package it in Docker
- Push the Docker image to AWS ECR
- Run it on AWS ECS Fargate behind a Load Balancer
- Access it via a public URL from anywhere in the world

The architecture looks like this:

```
Your Code
    ↓
Docker Image (built locally)
    ↓
ECR (stores the image on AWS)
    ↓
ECS Task Definition (blueprint: which image, how much CPU/memory, which port)
    ↓
ECS Service (keeps the task always running)
    ↓
Fargate (AWS-managed servers that run the container)
    ↓
Application Load Balancer (public URL → routes traffic to your container)
```

---

<a id="s2"></a>
## 2. Project Structure

```
python-backend-learning/
├── src/
│   └── hello_api/
│       └── main.py          ← FastAPI application
├── tests/
│   └── test_hello.py        ← Tests
├── Dockerfile               ← How to build the Docker image
├── .dockerignore            ← Files to exclude from Docker image
├── requirements.txt         ← Python dependencies for Docker
├── pyproject.toml           ← Python project config
└── task-definition.json     ← ECS task blueprint (generated during setup)
```

---

<a id="s3"></a>
## 3. The Application Code

**`src/hello_api/main.py`**

```python
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Hello World API",
    version="0.1.0",
    description="Learning backend API",
)


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/hello")
async def hello_world():
    """Returns a hello world message."""
    return JSONResponse(status_code=200, content={"message": "Hello World"})


@app.get("/thanks")
async def thanks_world():
    """Returns a thanks world message."""
    return JSONResponse(status_code=200, content={"message": "Thanks World"})


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(status_code=200, content={"status": "API is running"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

> **Note:** `/health` and `/ready` are required by ECS for health checks. Always include them in production services.

---

<a id="s4"></a>
## 4. What is Docker?

Docker packages your application and everything it needs to run (Python version, OS libraries, dependencies) into a single unit called an **image**. When you run that image it becomes a **container**.

- **Image** = a recipe / blueprint (built once, stored in ECR)
- **Container** = a running instance of that image

The key benefit: the container runs **identically** on your laptop, a teammate's machine, and AWS. No more "works on my machine" problems.

The `Dockerfile` is the instruction file that tells Docker:
- What base OS/Python version to use
- What files to copy in
- What dependencies to install
- How to start the app

---

<a id="s5"></a>
## 5. Install Docker

### Check if Docker is already installed

```bash
docker --version
```

If you see a version number, Docker is installed. Skip to the next section.

### Install Docker Desktop on Mac (via Homebrew)

```bash
brew install --cask docker
```

> **Note:** This command requires `sudo` (your Mac password) when Homebrew runs an internal script. Run this in your terminal directly — not through any automated tool.

After installation completes:

1. Open **Docker Desktop** from your Applications folder (or Spotlight search)
2. Accept the license agreement
3. Wait for the Docker icon to appear in the menu bar at the top of your screen
4. When the icon is steady (not animated), Docker is running

### Verify Docker is running

```bash
docker --version
docker ps
```

`docker ps` should return an empty list (no error). If you see `Cannot connect to the Docker daemon`, Docker Desktop is not running — open it from Applications.

---

<a id="s6"></a>
## 6. Prepare Files for Docker

These files are needed before you can build a Docker image.

### 6.1 `requirements.txt`

This is the list of Python packages Docker will install inside the container. Create it in the project root:

```
fastapi>=0.115.0
uvicorn>=0.30.0
```

> **Why separate from `pyproject.toml`?** The reference production project installs dependencies per-service using `requirements.txt` inside Docker. It keeps the Docker layer cache efficient and avoids installing dev tools inside the container.

### 6.2 `Dockerfile`

Create this in the project root:

```dockerfile
FROM python:3.11-slim

USER root
WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "src.hello_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**What each line does:**

| Line | Explanation |
|------|-------------|
| `FROM python:3.11-slim` | Start from an official lightweight Python 3.11 image |
| `USER root` | Run as root to install packages |
| `WORKDIR /app` | All subsequent commands run from `/app` |
| `RUN apt-get install -y curl` | Install `curl` — required for health checks |
| `COPY requirements.txt` | Copy dependency list into the image |
| `RUN pip install` | Install Python dependencies |
| `COPY src/` | Copy your application code |
| `ENV PYTHONPATH=/app` | So Python can find `src.hello_api.main` |
| `EXPOSE 8000` | Document that the container listens on port 8000 |
| `CMD [...]` | Command to start the app when the container runs |

### 6.3 `.dockerignore`

Create this in the project root to exclude unnecessary files from the Docker image:

```
.git
.pytest_cache
.venv
__pycache__
*.pyc
```

---

<a id="s7"></a>
## 7. Build and Run Docker Locally

### 7.1 Build the Docker image

> **Important for Mac with Apple Silicon (M1/M2/M3):** Always build with `--platform linux/amd64` because AWS ECS Fargate runs on `linux/amd64`. Without this flag, the image will fail to run on AWS.

```bash
docker build --platform linux/amd64 -t backend-learning:latest .
```

- `--platform linux/amd64` — build for AWS-compatible architecture
- `-t backend-learning:latest` — name and tag the image
- `.` — use the current directory as build context (where Dockerfile is)

First build takes 1-3 minutes (downloads the base image). Subsequent builds are faster due to caching.

### 7.2 Verify the image was created

```bash
docker images
```

You should see `backend-learning` in the list.

### 7.3 Run the container locally

```bash
docker run -p 8000:8000 backend-learning
```

- `-p 8000:8000` — map port 8000 on your machine to port 8000 inside the container

You should see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 7.4 Test the endpoints

Open a new terminal tab and test:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/hello
curl http://localhost:8000/thanks
```

Or open in your browser:
- http://localhost:8000/health
- http://localhost:8000/hello

### 7.5 Stop the container

```bash
docker stop $(docker ps -q)
```

Or press `Ctrl+C` in the terminal where the container is running.

### 7.6 Useful Docker commands

```bash
docker ps                    # list running containers
docker ps -a                 # list all containers (including stopped)
docker images                # list all local images
docker logs <container-id>   # view container logs
docker stop <container-id>   # stop a container
docker rm <container-id>     # remove a stopped container
docker rmi backend-learning  # remove a local image
```

---

<a id="s8"></a>
## 8. AWS Key Concepts

Before creating any AWS resources, understand what each one is. This will make the setup steps much easier to follow.

### What is ECR (Elastic Container Registry)?

**ECR** is AWS's private Docker image registry — like GitHub but for Docker images.

- **GitHub** → stores source code
- **ECR** → stores Docker images

When ECS Fargate runs your container, it pulls the image from ECR over AWS's internal network (fast, free, private).

Every image in ECR has a URI like:
```
<account-id>.dkr.ecr.<region>.amazonaws.com/<repo-name>:<tag>
```

Example:
```
088971275490.dkr.ecr.eu-north-1.amazonaws.com/repo-learning:latest
```

**ECR Repository (`repo-learning`)**
A private storage bucket for your Docker images on AWS. Every time you push a new version of your image, it goes here. ECS pulls the image from here when starting your container.

---

### What is ECS (Elastic Container Service)?

**ECS** is AWS's service for running and managing Docker containers. You tell it which image to run, how many copies, and how much CPU/memory. ECS handles the rest.

**Fargate** is the compute engine behind ECS. With Fargate you never touch a server — AWS manages the underlying machines entirely.

| ECS + EC2 | ECS + Fargate |
|-----------|---------------|
| You manage the EC2 servers | You manage nothing |
| More control, more complexity | Simple, pay per task |
| Good for high-traffic cost optimization | Good for most use cases |

---

### Key ECS Components

**ECS Cluster (`backend-learning-cluster`)**
A logical grouping that holds your services. Think of it as a folder that organises all the running services for a project. It does not provision servers itself — with Fargate, AWS does that.

**ECS Task Definition (`backend-learning-task:1`)**
A versioned blueprint that tells ECS exactly how to run your container:
- Which Docker image to use (from ECR)
- How much CPU and memory to give it (`256` units = 0.25 vCPU, `512` MB RAM)
- Which port to open (`8000`)
- Where to send logs (CloudWatch)
- How to health check the container (`curl /health`)

Every time you change these settings, ECS creates a new revision (`:1`, `:2`, `:3`...).

**ECS Service (`backend-learning-service`)**
Keeps your container always running. You tell it "I always want 1 copy of this task running". If the container crashes or fails a health check, the service automatically starts a new one. It also handles rolling deployments — starts the new version before stopping the old one.

---

### What is a Load Balancer?

**Application Load Balancer (`backend-learning-alb`)**
The public entry point of your application. It has a fixed public DNS name and receives all incoming HTTP traffic on port 80. It then routes that traffic to whichever container is healthy.

Without a load balancer, your container would have no stable public address — container IPs change every time ECS starts a new task.

```
Internet
    ↓
Load Balancer (fixed public DNS, port 80)
    ↓
Target Group (tracks which containers are healthy)
    ↓
ECS Task (your running container, port 8000)
```

**Target Group (`backend-learning-targets`)**
Sits between the load balancer and your containers. It continuously health checks each container by hitting `/health`. Only healthy containers receive traffic.

---

### What is a Security Group?

**Security Group (`backend-learning-sg`)**
A virtual firewall that controls what network traffic is allowed in and out of your AWS resources. Think of it as a list of rules:

- "Allow TCP port 80 from anywhere" → so the load balancer accepts HTTP traffic
- "Allow TCP port 8000 from anywhere" → so the load balancer can reach your container

Without the port 80 rule, the load balancer cannot receive public traffic. This was one of the real issues encountered during this setup.

---

### What is CloudWatch?

**CloudWatch Log Group (`/ecs/backend-learning`)**
Where your container's console output is stored on AWS. Every `print()` statement, every uvicorn `INFO:` log line, every error — it all goes here automatically.

View live logs with:
```bash
aws logs tail /ecs/backend-learning --follow --region eu-north-1
```

---

<a id="s9"></a>
## 9. Create AWS Account and IAM User

### 9.1 Create AWS Account

1. Go to https://aws.amazon.com/
2. Click **"Create an AWS Account"**
3. Enter your email, password, account name
4. Enter credit card details (required, but free tier covers most basics for 12 months)
5. Verify your phone number
6. Choose **Basic Support** (free)
7. Sign in to the AWS Console

### 9.2 Create an IAM User for CLI Access

Using your root account to run CLI commands is insecure. Create a dedicated IAM user instead.

1. In the AWS Console search bar, type `IAM` and click on it
2. In the left sidebar, click **Users**
3. Click **Create user**
4. Username: `dev-cli` (or any name you prefer)
5. Click **Next**
6. Under "Permissions options", select **Attach policies directly**
7. Search for `AdministratorAccess` and check the box next to it
8. Click **Next** → **Create user**

### 9.3 Generate Access Keys

1. Click on the user you just created (`dev-cli`)
2. Go to the **Security credentials** tab
3. Scroll down to **Access keys**
4. Click **Create access key**
5. Select **Local code** as the use case
6. Click **Next** → **Create access key**
7. **IMPORTANT:** Copy and save both:
   - **Access Key ID** (looks like `AKIA...`)
   - **Secret Access Key** (shown only once — if you lose it, you must create a new key)

> Never share these keys or commit them to git. They give full access to your AWS account.

---

<a id="s10"></a>
## 10. Install and Configure AWS CLI

### 10.1 Install AWS CLI

```bash
brew install awscli
```

Verify:
```bash
aws --version
```

### 10.2 Configure AWS CLI

```bash
aws configure
```

Enter when prompted:
```
AWS Access Key ID [None]: <paste your Access Key ID>
AWS Secret Access Key [None]: <paste your Secret Access Key>
Default region name [None]: eu-north-1
Default output format [None]: json
```

> Use whatever region is closest to you. This guide uses `eu-north-1` (Stockholm). Common alternatives: `us-east-1`, `ap-south-1`, `eu-west-1`.

### 10.3 Verify the configuration

```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDA...",
    "Account": "088971275490",
    "Arn": "arn:aws:iam::088971275490:user/dev-cli"
}
```

If you see your account ID, everything is configured correctly.

---

<a id="s11"></a>
## 11. Push Docker Image to ECR

### 11.1 Create an ECR Repository

```bash
aws ecr create-repository --repository-name repo-learning --region eu-north-1
```

The output will show the `repositoryUri`. Note your AWS Account ID from the URI.

> If you see `RepositoryAlreadyExistsException`, the repo already exists — that's fine, continue.

### 11.2 Log in to ECR

Docker needs to authenticate with AWS before it can push images. Run:

```bash
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 088971275490.dkr.ecr.eu-north-1.amazonaws.com
```

> Replace `088971275490` with your AWS Account ID.

You should see: `Login Succeeded`

### 11.3 Tag the image with the ECR URI

```bash
docker tag backend-learning:latest 088971275490.dkr.ecr.eu-north-1.amazonaws.com/repo-learning:latest
```

### 11.4 Push the image to ECR

```bash
docker push 088971275490.dkr.ecr.eu-north-1.amazonaws.com/repo-learning:latest
```

This uploads all image layers to ECR. First push takes 1-2 minutes. Subsequent pushes are faster because unchanged layers are skipped.

### 11.5 Verify the image is in ECR

```bash
aws ecr list-images --repository-name repo-learning --region eu-north-1
```

---

<a id="s12"></a>
## 12. Deploy to ECS Fargate

### 12.1 Get networking information

Get your default VPC ID:
```bash
aws ec2 describe-vpcs --region eu-north-1 --query 'Vpcs[0].VpcId' --output text
```

Get two subnet IDs from that VPC:
```bash
aws ec2 describe-subnets --region eu-north-1 \
  --filters "Name=vpc-id,Values=<your-vpc-id>" \
  --query 'Subnets[0:2].[SubnetId]' \
  --output text
```

Save the values — you'll need them below.

### 12.2 Create an ECS Cluster

```bash
aws ecs create-cluster --cluster-name backend-learning-cluster --region eu-north-1
```

### 12.3 Create CloudWatch Log Group

ECS sends container logs here:

```bash
aws logs create-log-group --log-group-name /ecs/backend-learning --region eu-north-1
```

### 12.4 Create the ECS Task Execution Role

This IAM role gives ECS permission to pull images from ECR and write logs to CloudWatch:

```bash
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'
```

Attach the required AWS managed policy:

```bash
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

### 12.5 Create the Task Definition file

Create `task-definition.json` in your project root:

```json
{
  "family": "backend-learning-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "backend-learning",
      "image": "088971275490.dkr.ecr.eu-north-1.amazonaws.com/repo-learning:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/backend-learning",
          "awslogs-region": "eu-north-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::088971275490:role/ecsTaskExecutionRole"
}
```

> Replace `088971275490` with your AWS Account ID.

**Explanation of key fields:**

| Field | Value | Explanation |
|-------|-------|-------------|
| `cpu` | `256` | 0.25 vCPU |
| `memory` | `512` | 512 MB RAM |
| `containerPort` | `8000` | Port your FastAPI app listens on |
| `healthCheck.command` | `curl /health` | ECS uses this to check if your container is alive |
| `startPeriod` | `60` | Give the container 60s to start before failing health checks |

### 12.6 Register the Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region eu-north-1
```

### 12.7 Create a Security Group

```bash
aws ec2 create-security-group \
  --group-name backend-learning-sg \
  --description "Security group for backend-learning app" \
  --vpc-id <your-vpc-id> \
  --region eu-north-1
```

Save the `GroupId` from the output (looks like `sg-0a7ce263c158af519`).

Allow inbound traffic on ports 80 and 8000:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <security-group-id> \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0 \
  --region eu-north-1

aws ec2 authorize-security-group-ingress \
  --group-id <security-group-id> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 \
  --region eu-north-1
```

> **Important:** Port 80 is for the Load Balancer (public traffic). Port 8000 is for the Load Balancer to reach your container internally. Both are required.

### 12.8 Create an Application Load Balancer

```bash
aws elbv2 create-load-balancer \
  --name backend-learning-alb \
  --subnets <subnet-1> <subnet-2> \
  --security-groups <security-group-id> \
  --region eu-north-1
```

Save the `LoadBalancerArn` from the output.

### 12.9 Create a Target Group

> **Important:** Use `--target-type ip` (not `instance`) — Fargate requires IP-based targets. Using `instance` will cause a deployment error.

```bash
aws elbv2 create-target-group \
  --name backend-learning-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id <your-vpc-id> \
  --target-type ip \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --region eu-north-1
```

Save the `TargetGroupArn` from the output.

### 12.10 Create an ALB Listener

This tells the load balancer to forward port 80 traffic to your containers:

```bash
aws elbv2 create-listener \
  --load-balancer-arn <load-balancer-arn> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<target-group-arn> \
  --region eu-north-1
```

### 12.11 Create the ECS Service

```bash
aws ecs create-service \
  --cluster backend-learning-cluster \
  --service-name backend-learning-service \
  --task-definition backend-learning-task:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet-1>,<subnet-2>],securityGroups=[<security-group-id>],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=<target-group-arn>,containerName=backend-learning,containerPort=8000 \
  --region eu-north-1
```

### 12.12 Get your public URL

```bash
aws elbv2 describe-load-balancers \
  --load-balancer-arns <load-balancer-arn> \
  --region eu-north-1 \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

This gives you a DNS name like:
```
backend-learning-alb-1264963434.eu-north-1.elb.amazonaws.com
```

### 12.13 Wait and test

Wait 1-2 minutes for ECS to pull the image and start the container, then test:

```bash
curl http://<your-alb-dns>/health
curl http://<your-alb-dns>/ready
curl http://<your-alb-dns>/hello
```

### 12.14 Check service status

```bash
aws ecs describe-services \
  --cluster backend-learning-cluster \
  --services backend-learning-service \
  --region eu-north-1 \
  --query 'services[0].[runningCount,desiredCount]' \
  --output text
```

Should show `1  1` (1 running, 1 desired).

### 12.15 Check target health

```bash
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn> \
  --region eu-north-1
```

Should show `"State": "healthy"`.

### 12.16 View live logs

```bash
aws logs tail /ecs/backend-learning --follow --region eu-north-1
```

---

<a id="s13"></a>
## 13. Day-to-Day Workflow

### Local Development (fast, no Docker)

During active development, don't use Docker. Run the app directly:

```bash
# From project root
uv run uvicorn src.hello_api.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the venv:
```bash
.venv/bin/uvicorn src.hello_api.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag auto-restarts the server every time you save a file. No rebuilds needed. Test instantly at `http://localhost:8000`.

### Test with Docker Locally

Once happy with your changes, verify the Docker container works before pushing to AWS:

```bash
# Stop any existing container
docker stop $(docker ps -q) 2>/dev/null

# Rebuild with new code
docker build --platform linux/amd64 -t backend-learning:latest .

# Run
docker run -p 8000:8000 backend-learning
```

### Deploy to AWS

After verifying the Docker container works locally:

```bash
# 1. Tag for ECR
docker tag backend-learning:latest 088971275490.dkr.ecr.eu-north-1.amazonaws.com/repo-learning:latest

# 2. Push to ECR
docker push 088971275490.dkr.ecr.eu-north-1.amazonaws.com/repo-learning:latest

# 3. Force ECS to redeploy with the new image
aws ecs update-service \
  --cluster backend-learning-cluster \
  --service backend-learning-service \
  --force-new-deployment \
  --region eu-north-1

# 4. Wait ~60 seconds, then test
curl http://backend-learning-alb-1264963434.eu-north-1.elb.amazonaws.com/health
```

### Check if ECS picked up the new image

```bash
aws ecs describe-services \
  --cluster backend-learning-cluster \
  --services backend-learning-service \
  --region eu-north-1 \
  --query 'services[0].[runningCount,desiredCount]' \
  --output text
# Should output: 1  1
```

### Full Pipeline Summary

```
Edit code
    ↓
uv run uvicorn --reload   ← fast local testing (no Docker needed)
    ↓
docker build              ← when ready to deploy
    ↓
docker run                ← verify Docker image works locally
    ↓
docker push               ← upload new image to ECR
    ↓
aws ecs update-service    ← trigger redeployment on AWS
    ↓
curl <alb-url>/health     ← verify live on AWS
```

---

<a id="s14"></a>
## 14. Resources and URLs

### Your AWS Resources (from this setup)

| Resource | Type | Name / Value |
|----------|------|--------------|
| AWS Account ID | Account | `088971275490` |
| Region | Config | `eu-north-1` (Stockholm) |
| IAM User | Identity | `dev-cli` |
| ECR Repository | Image storage | `repo-learning` |
| ECS Cluster | Container grouping | `backend-learning-cluster` |
| ECS Task Definition | Container blueprint | `backend-learning-task:1` |
| ECS Service | Container manager | `backend-learning-service` |
| Load Balancer | Public entry point | `backend-learning-alb` |
| Security Group | Firewall rules | `backend-learning-sg` |
| CloudWatch Log Group | Logs storage | `/ecs/backend-learning` |

### Your Live API Endpoints

```
http://backend-learning-alb-1264963434.eu-north-1.elb.amazonaws.com/health
http://backend-learning-alb-1264963434.eu-north-1.elb.amazonaws.com/ready
http://backend-learning-alb-1264963434.eu-north-1.elb.amazonaws.com/hello
http://backend-learning-alb-1264963434.eu-north-1.elb.amazonaws.com/thanks
```

### Your Local API Endpoints

```
http://localhost:8000/health
http://localhost:8000/ready
http://localhost:8000/hello
http://localhost:8000/thanks
```

### Helpful AWS Console Links

- ECR: https://eu-north-1.console.aws.amazon.com/ecr/repositories
- ECS: https://eu-north-1.console.aws.amazon.com/ecs/v2/clusters
- CloudWatch Logs: https://eu-north-1.console.aws.amazon.com/cloudwatch/home#logsV2:log-groups
- Load Balancers: https://eu-north-1.console.aws.amazon.com/ec2/home#LoadBalancers

---

## What's Next?

Now that your app is live, here are natural next steps:

1. **Add more endpoints** — keep building your API
2. **Add a database** — use AWS RDS (PostgreSQL) or DynamoDB
3. **Add authentication** — JWT tokens, AWS Cognito
4. **Add environment variables** — store secrets in AWS Secrets Manager
5. **Set up CI/CD** — automate the deploy pipeline with GitHub Actions
6. **Add HTTPS** — attach an SSL certificate via AWS Certificate Manager
7. **Custom domain** — use Route 53 to point a domain to your ALB
