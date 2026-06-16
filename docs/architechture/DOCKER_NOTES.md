# Docker Complete Guide for Beginners to Advanced

## Table of Contents
1. [Why Docker?](#why-docker)
2. [Prerequisites & Installation](#prerequisites--installation)
3. [Core Concepts](#core-concepts)
4. [Your First Docker Container](#your-first-docker-container)
5. [Building Your Own Image](#building-your-own-image)
6. [Docker Compose](#docker-compose)
7. [Networking & Storage](#networking--storage)
8. [Best Practices & Production](#best-practices--production)
9. [AWS Integration](#aws-integration)
10. [Troubleshooting](#troubleshooting)
11. [Next Steps](#next-steps)

---

## Why Docker?

### The Problem Docker Solves

Imagine you build an application on your laptop:
- You have Python 3.11, PostgreSQL 14, Node.js 18 installed
- Your app runs perfectly
- You send it to a colleague. They have Python 3.9 and PostgreSQL 12
- Their environment is different → app breaks ("It works on my machine!")
- You send it to production. Different OS, different versions
- Deployment chaos

### The Docker Solution

Docker packages your **entire application** with:
- OS environment
- Runtime (Python, Node, Java, etc.)
- All dependencies
- Configuration
- Everything needed to run

This package (called an **image**) runs the **same way** everywhere:
- Your laptop ✓
- Your colleague's laptop ✓
- Production server ✓
- Cloud (AWS, GCP, Azure) ✓

### When to Use Docker

**Use Docker when:**
- Building applications that will run on multiple machines
- Working in a team (standardize environments)
- Deploying to production or cloud
- Running multiple services (databases, cache, APIs)
- Need consistent dev/test/prod environments
- Using microservices architecture

**Don't need Docker for:**
- Simple scripts you run once
- Web apps that run only on your machine forever
- Learning a language (but it's good practice)

---

## Prerequisites & Installation

### System Requirements
- **Mac**: macOS 11 or newer
- **Windows**: Windows 10 Pro/Enterprise (or Windows 11) with WSL 2
- **Linux**: Any modern distribution

### Install Docker

#### Mac
```bash
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
# Or via Homebrew
brew install docker docker-compose

# Start Docker Desktop application
# Verify installation
docker --version
docker run hello-world
```

#### Windows
```bash
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
# Ensure WSL 2 is enabled
wsl --update

# Verify in PowerShell
docker --version
docker run hello-world
```

#### Linux (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Allow non-root user
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker run hello-world
```

### Verify Installation
```bash
docker --version              # Shows Docker version
docker ps                     # Lists running containers (should be empty)
docker images                 # Lists available images
```

---

## Core Concepts

### 1. Images vs Containers

Think of it like **classes vs objects in programming**:

```
Image = Blueprint/Template (read-only)
Container = Running instance (has state, can be modified)
```

**Image Example:**
- File: `Dockerfile`
- Built once
- Never changes (unless you rebuild)
- Can create multiple containers from one image

**Container Example:**
- Running process
- Each container is independent
- Starts, runs, stops, or crashes
- Can be deleted and restarted

### 2. Dockerfile

A `Dockerfile` is a recipe to build an image. Each line is an instruction.

**Simple Example:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

**What each line does:**
- `FROM python:3.11-slim` — Start from Python 3.11 base image
- `WORKDIR /app` — Set the working directory inside container to `/app`
- `COPY requirements.txt .` — Copy `requirements.txt` from your computer to `/app` in container
- `RUN pip install -r requirements.txt` — Install Python dependencies
- `COPY . .` — Copy everything from current directory to `/app` in container
- `CMD ["python", "app.py"]` — Default command when container starts

### 3. Layers & Caching

Each Dockerfile instruction creates a **layer** (like a sheet in a stack):

```
Layer 1: FROM python:3.11-slim          (OS + Python runtime)
Layer 2: WORKDIR /app                   (directory setup)
Layer 3: COPY requirements.txt .         (copy file)
Layer 4: RUN pip install ...             (install dependencies)
Layer 5: COPY . .                        (copy app code)
Layer 6: CMD ["python", "app.py"]        (default command)
```

**Why layers matter:**
- Docker caches layers. If nothing changed, it reuses the cached layer (faster builds)
- **Order matters**: Put things that change frequently at the bottom
- Changing app code (Layer 5) won't rebuild layers 1-4

**Good Dockerfile ordering:**
```dockerfile
FROM python:3.11-slim                           # Rarely changes
RUN apt-get update && apt-get install -y ...   # System dependencies (rarely change)
COPY requirements.txt .                         # Dependencies file
RUN pip install -r requirements.txt             # Install dependencies (cached if file unchanged)
COPY . .                                        # App code (changes frequently)
CMD ["python", "app.py"]
```

### 4. Key Dockerfile Instructions

| Instruction | Purpose | Example |
|---|---|---|
| `FROM` | Base image | `FROM python:3.11-slim` |
| `WORKDIR` | Working directory | `WORKDIR /app` |
| `COPY` | Copy from host to container | `COPY . /app` |
| `RUN` | Execute command during build | `RUN pip install -r requirements.txt` |
| `ENV` | Environment variable | `ENV DEBUG=false` |
| `EXPOSE` | Document port (doesn't map) | `EXPOSE 8000` |
| `CMD` | Default command on start | `CMD ["python", "app.py"]` |
| `ENTRYPOINT` | Configure as executable | `ENTRYPOINT ["python"]` |
| `ARG` | Build-time variable | `ARG VERSION=1.0` |
| `VOLUME` | Define data volume | `VOLUME /data` |
| `USER` | Run as non-root user | `USER appuser` |

### 5. Base Images

Start with a minimal base image. Smaller = faster downloads and better security.

**Popular Base Images:**
```dockerfile
FROM python:3.11-slim              # 150 MB - minimal Python
FROM python:3.11                   # 1 GB - Python with build tools
FROM node:18-alpine                # 150 MB - Node.js minimal
FROM node:18                        # 900 MB - Node.js with tools
FROM ubuntu:22.04                  # 70 MB - Bare OS
FROM alpine:3.18                   # 7 MB - Ultra-minimal Linux
```

**Alpine vs Slim:**
- **Alpine**: Super tiny, minimal tools (good for production)
- **Slim**: Smaller than full, includes essentials (good for dev)
- **Full**: Includes development tools (largest)

---

## Your First Docker Container

### Step 1: Run a Pre-built Image

Try running a container without building anything:

```bash
docker run hello-world
```

**What happened:**
1. Docker checked if `hello-world` image exists locally
2. It didn't, so Docker downloaded it from Docker Hub (registry)
3. Created a container from the image
4. Ran the default command (print "Hello from Docker")
5. Container exited

### Step 2: Run an Interactive Container

```bash
docker run -it ubuntu:22.04 /bin/bash
```

**Flags:**
- `-it` means interactive terminal (you can type commands)
- `/bin/bash` is the command to run (bash shell)

**Inside the container:**
```bash
# You're now inside the container!
pwd                    # /
ls                     # Shows container's filesystem (not your computer's)
cat /etc/os-release    # Shows Ubuntu version
echo "Hello Docker"
exit                   # Exit the container
```

### Step 3: Run a Web Server

```bash
docker run -d -p 8080:80 nginx
```

**Flags:**
- `-d` means detached (runs in background)
- `-p 8080:80` means map port 8080 on your computer to port 80 in container

**Test it:**
```bash
curl http://localhost:8080
# Or open http://localhost:8080 in browser
# You'll see default nginx welcome page
```

**Stop the container:**
```bash
docker ps                  # List running containers
docker stop <container_id>
```

### Key Commands to Know

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop a running container
docker stop <container_id_or_name>

# Start a stopped container
docker start <container_id_or_name>

# Remove a container
docker rm <container_id_or_name>

# View container logs
docker logs <container_id>
docker logs -f <container_id>    # Follow logs (like tail -f)

# Execute command in running container
docker exec -it <container_id> /bin/bash

# Inspect container details
docker inspect <container_id>
```

---

## Building Your Own Image

### Step 1: Create a Simple Application

Create a file `app.py`:
```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from Docker!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Create `requirements.txt`:
```
Flask==2.3.0
```

### Step 2: Create a Dockerfile

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
```

### Step 3: Build the Image

```bash
docker build -t my-app:1.0 .
```

**What happens:**
1. Reads `Dockerfile`
2. Executes each instruction
3. Tags the final image as `my-app:1.0`
4. Output shows each step

**See your image:**
```bash
docker images          # Your `my-app:1.0` should be listed
```

### Step 4: Run Your Image

```bash
docker run -d -p 5000:5000 --name my-app-container my-app:1.0
```

**Test it:**
```bash
curl http://localhost:5000
# Output: Hello from Docker!

# View logs
docker logs my-app-container

# Stop it
docker stop my-app-container
```

### Debugging During Build

If your build fails, check the error:

```bash
docker build -t my-app:1.0 .
# Look at the error message
# Fix Dockerfile
# Rebuild
```

**Common errors:**
- `COPY failed`: File doesn't exist or wrong path
- `RUN command not found`: Command isn't installed
- `Port already in use`: Change `-p` mapping

### Tagging Images

Tags are like version labels:

```bash
docker tag my-app:1.0 my-app:latest
docker tag my-app:1.0 my-app:prod
docker images          # See all tags
```

---

## Docker Compose

### What is Compose?

Instead of running multiple `docker run` commands, define everything in `docker-compose.yml` and start all services with one command.

**Before Compose (annoying):**
```bash
docker run -d -p 5000:5000 --name app my-app:1.0
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=pass --name db postgres:14
docker network create app-network
docker network connect app-network app
docker network connect app-network db
```

**With Compose (simple):**
```bash
docker-compose up
```

### Step 1: Create docker-compose.yml

Create a file `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .                    # Build from ./Dockerfile
    ports:
      - "5000:5000"            # Map port 5000
    environment:
      DATABASE_URL: postgresql://db:5432/mydb
    depends_on:
      - db                      # Wait for db service first

  db:
    image: postgres:14         # Use pre-built image
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    volumes:
      - db_data:/var/lib/postgresql/data  # Persistent storage
    ports:
      - "5432:5432"
```

### Step 2: Run Everything

```bash
docker-compose up               # Start in foreground (see logs)
docker-compose up -d            # Start in background
docker-compose ps               # See running services
docker-compose logs -f app      # Follow app logs
docker-compose stop             # Stop all services
docker-compose down             # Stop and remove containers
docker-compose down -v          # Also remove volumes
```

### Service Discovery

Services can communicate by name:

```python
# Inside 'app' service, connect to database
import psycopg2

conn = psycopg2.connect(
    dbname="mydb",
    user="user",
    password="password",
    host="db",           # Service name from docker-compose.yml
    port=5432
)
```

### Volumes in Compose

**Two types:**

1. **Named volume** (managed by Docker, survives deletion)
```yaml
volumes:
  db_data:               # Define at top level

services:
  db:
    volumes:
      - db_data:/var/lib/postgresql/data
```

2. **Bind mount** (maps host directory, for development)
```yaml
services:
  app:
    volumes:
      - ./src:/app/src   # Changes on host appear in container
```

**Real example for development:**
```yaml
version: '3.8'

services:
  app:
    build: .
    volumes:
      - ./src:/app/src        # Live code reload
      - ./tests:/app/tests
    environment:
      DEBUG: "true"

  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Environment Variables in Compose

**Option 1: Inline**
```yaml
services:
  app:
    environment:
      DEBUG: "true"
      LOG_LEVEL: info
```

**Option 2: .env file**

Create `.env`:
```
DEBUG=true
LOG_LEVEL=info
DB_PASSWORD=secret
```

In `docker-compose.yml`:
```yaml
services:
  db:
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
```

Run:
```bash
docker-compose up
# Values from .env are substituted
```

---

## Networking & Storage

### Networking

By default, Compose creates a network and all services connect to it.

**Services communicate by name:**
```yaml
services:
  app:
    environment:
      DATABASE_URL: postgresql://db:5432/mydb   # "db" is service name
  db:
    image: postgres:14
```

### Storage: Volumes vs Bind Mounts

| Feature | Volume | Bind Mount |
|---------|--------|------------|
| Managed by | Docker | You |
| Created | `docker volume create` | Directory already exists |
| Persists | Yes (survives deletion) | Depends on directory |
| Performance | Optimized | Slower on Mac/Windows |
| Use case | Databases, data | Development, code |

**Volumes:**
```bash
docker volume create my-data
docker run -v my-data:/data my-image
docker volume inspect my-data   # See where it's stored
docker volume rm my-data
```

**Bind Mounts:**
```bash
docker run -v $(pwd)/data:/app/data my-image
```

### Health Checks

Ensure service is ready before others start:

```yaml
services:
  db:
    image: postgres:14
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "user"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  app:
    build: .
    depends_on:
      db:
        condition: service_healthy   # Wait for db to be healthy
```

---

## Best Practices & Production

### 1. Keep Images Small

**Bad:**
```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y build-essential
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```
Result: 500+ MB image

**Good:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . /app
CMD ["python", "app.py"]
```
Result: ~200 MB image

**Better (Multi-stage):**
```dockerfile
# Stage 1: Build dependencies
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --target /build/libs -r requirements.txt

# Stage 2: Runtime (slim)
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /build/libs /app/libs
COPY app.py .
ENV PYTHONPATH=/app/libs
CMD ["python", "app.py"]
```
Result: ~150 MB image (smallest)

### 2. Security: Run as Non-Root

**Bad (runs as root):**
```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
CMD ["python", "app.py"]
```

**Good (non-root user):**
```dockerfile
FROM python:3.11-slim
RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY --chown=appuser:appuser . .
USER appuser
CMD ["python", "app.py"]
```

### 3. Don't Store Secrets in Images

**Bad:**
```dockerfile
ENV DB_PASSWORD=supersecret
```
Problem: Anyone who has the image has the password. Use `docker history` to see it.

**Good:**
Pass secrets at runtime:
```bash
docker run -e DB_PASSWORD=supersecret my-image
```

Or use AWS Secrets Manager, which we'll cover.

### 4. Use .dockerignore

Like `.gitignore`, exclude unnecessary files:

```
.git
.gitignore
__pycache__
*.pyc
node_modules
.env
.env.local
.DS_Store
build/
dist/
.pytest_cache/
.coverage
.venv
venv
```

### 5. Logging: Output to Stdout

Docker captures container logs. Write logs to stdout/stderr:

**Good:**
```python
import sys

print("Application started", file=sys.stdout)
print("Error occurred", file=sys.stderr)
```

**Better (structured logging):**
```python
import json
import sys

log = {"level": "INFO", "message": "App started"}
print(json.dumps(log), file=sys.stdout)
```

View logs:
```bash
docker logs my-container
docker logs -f my-container      # Follow
```

### 6. Health Checks

Tell Docker how to check if service is healthy:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

Check status:
```bash
docker ps
# STATUS column shows: Up 5 minutes (healthy)
```

### 7. Resource Limits

Prevent container from consuming all resources:

```yaml
services:
  app:
    mem_limit: 512m
    cpus: '1.0'
```

Or with `docker run`:
```bash
docker run -m 512m --cpus 1.0 my-image
```

### 8. Use Official Images

```dockerfile
FROM python:3.11          # Official, well-maintained
FROM my-random-image:1.0  # Unknown, possibly outdated/malicious
```

Check at [hub.docker.com](https://hub.docker.com) for official images.

---

## AWS Integration

### Elastic Container Registry (ECR)

**What it is:** AWS's private Docker registry. Store your images securely.

#### Step 1: Create Repository

```bash
aws ecr create-repository --repository-name my-app --region us-east-1
```

Response includes URL: `123456789.dkr.ecr.us-east-1.amazonaws.com/my-app`

#### Step 2: Login to ECR

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
```

#### Step 3: Tag & Push Image

```bash
# Build locally
docker build -t my-app:1.0 .

# Tag with ECR URL
docker tag my-app:1.0 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0

# Push to ECR
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0

# View in AWS Console or CLI
aws ecr describe-images --repository-name my-app
```

#### Step 4: Pull & Run

```bash
# Anyone with AWS access can pull
docker pull 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0
docker run 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0
```

### Elastic Container Service (ECS) - Run on AWS

**What it is:** AWS service to run containers at scale. Like Docker Compose but for cloud.

#### Concepts

- **Task Definition**: Describes your container (like docker-compose service definition)
- **Task**: Running instance of task definition
- **Service**: Keeps desired number of tasks running
- **Cluster**: Where tasks run

#### Step 1: Create Task Definition

Create `task-definition.json`:
```json
{
  "family": "my-app",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "my-app",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0",
      "portMappings": [
        {
          "containerPort": 5000,
          "hostPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENV",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/my-app",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register it:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### Step 2: Create Cluster

```bash
aws ecs create-cluster --cluster-name my-cluster
```

#### Step 3: Create Service

```bash
aws ecs create-service \
  --cluster my-cluster \
  --service-name my-service \
  --task-definition my-app:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### Step 4: Deploy Updates

When you build a new image:
```bash
# Push new version
docker tag my-app:2.0 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:2.0
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:2.0

# Update ECS service
aws ecs update-service \
  --cluster my-cluster \
  --service my-service \
  --force-new-deployment
```

#### View Status

```bash
aws ecs list-tasks --cluster my-cluster
aws ecs describe-tasks --cluster my-cluster --tasks <task_arn>
```

### LocalStack: Test AWS Locally

**What it is:** Simulates AWS services on your machine. Build/test without AWS account.

#### Docker Compose with LocalStack

```yaml
version: '3.8'

services:
  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      SERVICES: ecr,s3,dynamodb
      DEBUG: 1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  app:
    build: .
    environment:
      AWS_ENDPOINT_URL: http://localstack:4566
      AWS_ACCESS_KEY_ID: test
      AWS_SECRET_ACCESS_KEY: test
      AWS_REGION: us-east-1
    depends_on:
      - localstack
    ports:
      - "5000:5000"
```

#### Use LocalStack in Code

```python
import boto3

# Point to LocalStack instead of real AWS
s3 = boto3.client(
    "s3",
    endpoint_url="http://localstack:4566",
    region_name="us-east-1"
)

# Create bucket
s3.create_bucket(Bucket="test-bucket")
```

---

## Troubleshooting

### Common Problems & Solutions

#### 1. Container Exits Immediately

```bash
docker run my-image
docker ps -a          # See the stopped container
docker logs <container_id>
```

**Causes:**
- Command failed and exited
- Application crashed
- Missing dependencies

**Fix:**
```bash
docker run -it my-image /bin/bash   # Interactive shell to debug
```

#### 2. "Address already in use" Error

```
docker: Error response from daemon: driver failed programming external connectivity 
on endpoint: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Fix:**
```bash
# Use different port
docker run -p 9000:8000 my-image

# Or find what's using port 8000
lsof -i :8000
kill -9 <pid>
```

#### 3. "Cannot connect to database" (from app)

App can't reach database container:

```bash
# Check if db container is running
docker ps

# Check networking
docker network ls
docker network inspect <network_name>

# Test from app container
docker exec -it app-container ping db
```

**Fix:**
- Ensure services are on same network
- Use service name (not localhost)
- With Compose, this is automatic

#### 4. Build Cache Not Working

You change code, rebuild, but old version still runs:

```bash
# Force rebuild (ignore cache)
docker build --no-cache -t my-app:1.0 .
```

**Better:** Order Dockerfile correctly (see Best Practices section)

#### 5. Image Won't Push to ECR

```bash
docker push my-app:1.0
# Error: Denied: User is not authorized
```

**Fix:**
```bash
# Ensure you're logged in
aws ecr get-login-password | docker login ...

# Tag with full ECR URL
docker tag my-app:1.0 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:1.0
```

#### 6. Seeing "WARNING: Python running in container without unbuffered output"

Your app's output isn't showing in logs:

**Fix:**
```dockerfile
ENV PYTHONUNBUFFERED=1
```

#### 7. Volume Permissions Issues

```
PermissionError: [Errno 13] Permission denied: '/app/data/file.txt'
```

**Fix:**
```dockerfile
RUN useradd -m -u 1000 appuser
COPY --chown=appuser:appuser . /app
USER appuser
```

---

## Next Steps

### You've Learned
✓ Why Docker exists  
✓ How to build images  
✓ How to run containers  
✓ Multi-service apps with Compose  
✓ Storage and networking  
✓ Production best practices  
✓ AWS integration  

### Practice Projects (Do These!)

#### Project 1: Node.js Web App
1. Create simple Express app
2. Write Dockerfile
3. Build and run locally
4. Deploy to ECR
5. Run on ECS

#### Project 2: Python API + Database
1. Flask API with PostgreSQL
2. Write docker-compose.yml
3. Persist data with volumes
4. Add health checks
5. Test local deployment

#### Project 3: Microservices
1. Build 3+ services (API, worker, database)
2. Define in docker-compose.yml
3. Services communicate by name
4. Scale to multiple instances
5. Add load balancing

### Learn More
- [Docker Official Docs](https://docs.docker.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Docker Security](https://docs.docker.com/engine/security/)

### Quick Commands Cheat Sheet

```bash
# Build
docker build -t my-app:1.0 .

# Run
docker run -d -p 8080:8000 --name app my-app:1.0

# Containers
docker ps
docker stop <id>
docker logs <id>
docker exec -it <id> /bin/bash

# Images
docker images
docker push <image>
docker rm <id>

# Compose
docker-compose up -d
docker-compose down
docker-compose logs -f

# Clean up
docker system prune -a
docker volume prune
```

### Questions to Ask Yourself

When learning a new concept:
- **Why** would I use this? (volumes vs bind mounts)
- **When** would I use this? (Compose vs single containers)
- **What happens** if this fails? (no health check, network down)
- **How do I debug** this? (logs, exec, inspect)

---

**Learning Docker takes time. Build things. Make mistakes. Fix them. That's how you learn.**

Happy containerizing! 🐳

---

**Last Updated:** May 30, 2026
**For:** Complete beginners through intermediate users
