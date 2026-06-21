# AWS Documentation Index

## Core Integration Guide

**`SNS_SQS_LAMBDA_INTEGRATION.md`** — **START HERE**

Comprehensive single source of truth covering:
- ✅ Why SNS → SQS → Lambda (not direct)
- ✅ Step-by-step setup (AWS Console + CLI)
- ✅ Code patterns (Publisher + Consumer)
- ✅ Deployment workflow
- ✅ Our reference implementation
- ✅ Troubleshooting

## Event-Driven Routing

- `EVENTBRIDGE_GUIDE.md` — Content-based event routing with EventBridge (bus, rules, SQS targets)

## Deployment & Infrastructure

- `LAMBDA_AUTO_DEPLOYMENT.md` — GitHub Actions auto-deploy on every push to main
- `AWS_DEPLOYMENT_GUIDE.md` — Infrastructure setup, EKS, databases, monitoring
- `AWS_CREDIT_OPTIMIZATION.md` — Cost optimization tips

## Quick Navigation

| Need | Read |
|------|------|
| **How to set up SNS, SQS, Lambda?** | `SNS_SQS_LAMBDA_INTEGRATION.md` |
| **How to route events by content (EventBridge)?** | `EVENTBRIDGE_GUIDE.md` |
| **How to auto-deploy Lambda on push?** | `LAMBDA_AUTO_DEPLOYMENT.md` |
| **How to deploy to AWS?** | `AWS_DEPLOYMENT_GUIDE.md` |
| **How to optimize costs?** | `AWS_CREDIT_OPTIMIZATION.md` |
| **How does our code work?** | `SNS_SQS_LAMBDA_INTEGRATION.md` → Reference Implementation section |

## What We Removed

The following docs were consolidated into `SNS_SQS_LAMBDA_INTEGRATION.md`:

- ❌ `docs/sqs/SNS_LEARNING_SUMMARY.md` (learning notes)
- ❌ `docs/sqs/SNS_LEARNING_INDEX.md` (index)
- ❌ `docs/sqs/SNS_QUICK_REFERENCE.md` (quick ref)
- ❌ `docs/sqs/SNS_REAL_WORLD_EXAMPLE.md` (examples)
- ❌ `docs/sqs/SNS_SQS_INTEGRATION.md` (architecture)
- ❌ `docs/sqs/AWS_SNS_GUIDE.md` (guide)
- ❌ `docs/sqs/IMPLEMENTATION_CHECKLIST.md` (checklist)
- ❌ `docs/SNS_SQS_LAMBDA_SETUP_CHECKLIST.md`
- ❌ `docs/LAMBDA_DEPLOYMENT_GUIDE.md`
- ❌ `docs/LAMBDA_HANDLERS_GIT_VS_CONSOLE.md`
- ❌ `docs/LAMBDA_QUICK_REFERENCE.md`
- ❌ `docs/SNS_SQS_LAMBDA_INTEGRATION.md`

## Why One Document?

| Before | After |
|--------|-------|
| 11 scattered docs | 1 complete guide |
| Redundant info | Single source of truth |
| Hard to navigate | Clear structure |
| Learning context | Production patterns |
| Outdated patterns | Latest `bonus_platform_service` architecture |

## Our Architecture

All docs now reference the same implementation:

```
SNS Topic (user-events)
    ↓
SQS Queues (onboarding, email, fraud, etc.)
    ↓
Lambda Functions
    ├── onboarding_service/lambda_function.py
    ├── email_service/lambda_function.py
    └── (more consumers)
```

Each Lambda follows:
- Handler registry pattern (`@registry.register_queue_event`)
- Lazy ServiceContainer DI
- Flat domain events (no nested wrappers)
- SNS envelope unwrap
- Exception handling (raise on failure for SQS retries)

See `SNS_SQS_LAMBDA_INTEGRATION.md` → Reference Implementation section.
