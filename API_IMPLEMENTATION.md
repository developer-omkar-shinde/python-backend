# Onboarding Service - User API Implementation

## Overview
Created a `/create-test-user` API endpoint that integrates with DynamoDB to store user data.

## Architecture

The implementation follows a **clean, layered architecture**:

```
HTTP Request
    ↓
Controller (user_controller.py)
    ↓
Service (user_service.py)
    ↓
Repository (user_repository.py)
    ↓
DynamoDB (test_users table)
```

### Layer Responsibilities

1. **Controller** (`controllers/user_controller.py`)
   - Handles HTTP requests/responses
   - Validates input using Pydantic schemas
   - Returns appropriate HTTP status codes
   - Catches errors and returns error responses

2. **Service** (`services/user_service.py`)
   - Contains business logic
   - Orchestrates repository calls
   - Transforms data between layers
   - Can be tested independently

3. **Repository** (`repositories/user_repository.py`)
   - Handles all DynamoDB operations
   - Manages database connection
   - Pure data access layer
   - Easy to mock for testing

4. **Schemas** (`schemas/user_schema.py`)
   - Pydantic models for request/response validation
   - Type hints and field constraints
   - Auto-generated API documentation

## API Endpoints

### Create Test User
```
POST /api/v1/create-test-user
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe"
}

Response (201 Created):
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2026-06-14T14:30:00+00:00"
}
```

### Get User
```
GET /api/v1/users/{user_id}

Response (200 OK):
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2026-06-14T14:30:00+00:00"
}
```

## DynamoDB Table Structure

**Table Name**: `test_users`

| Attribute | Type | Description |
|-----------|------|-------------|
| user_id | String (PK) | Unique user identifier (UUID) |
| first_name | String | User's first name |
| last_name | String | User's last name |
| created_at | String | ISO 8601 timestamp |

## Setup Instructions

### 1. Install Dependencies
```bash
cd services/onboarding_service
pip install -r onboarding/requirements.txt
```

### 2. Create DynamoDB Table (Local Development)
Using AWS CLI or local DynamoDB:

```bash
aws dynamodb create-table \
  --table-name test_users \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Or for local DynamoDB (Docker):
```bash
docker run -p 8000:8000 amazon/dynamodb-local
```

Then create table with local endpoint:
```bash
aws dynamodb create-table \
  --table-name test_users \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:8000
```

### 3. Run the Service
```bash
cd /Users/prometteur/Documents/Leaning/python-backend-learning
PYTHONPATH=".:services/onboarding_service" uvicorn onboarding.main:app --reload --port 8001
```

### 4. Test the API
```bash
# Create a user
curl -X POST http://localhost:8001/api/v1/create-test-user \
  -H "Content-Type: application/json" \
  -d '{"first_name": "John", "last_name": "Doe"}'

# Get a user
curl http://localhost:8001/api/v1/users/550e8400-e29b-41d4-a716-446655440000
```

## Key Features

✅ **Clean Architecture** - Separation of concerns (controller, service, repository)
✅ **Type Safety** - Full TypeScript-like typing with Pydantic
✅ **Validation** - Input validation with constraints
✅ **Error Handling** - Proper HTTP status codes and error messages
✅ **Scalability** - Easy to add new endpoints and services
✅ **Testability** - Each layer can be tested independently
✅ **AWS Ready** - Uses boto3, works with real DynamoDB

## Files Created/Modified

- ✅ `requirements.txt` - Added boto3 and pydantic
- ✅ `v1/schemas/user_schema.py` - Request/response models
- ✅ `v1/repositories/user_repository.py` - DynamoDB operations
- ✅ `v1/services/user_service.py` - Business logic
- ✅ `v1/controllers/user_controller.py` - HTTP handlers
- ✅ `v1/routes.py` - Route registration
