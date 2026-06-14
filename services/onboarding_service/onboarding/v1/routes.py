"""V1 route registrations."""

from __future__ import annotations

from fastapi import FastAPI

from onboarding.v1.dependencies import container
from onboarding.v1.schemas.requests.user_request import CreateUserRequest
from onboarding.v1.schemas.responses.user_response import UserResponse


def register_v1_routes(app: FastAPI) -> None:
    controller = container.get_user_controller()

    @app.post("/api/v1/create-test-user", response_model=UserResponse, status_code=201, tags=["users"])
    async def create_test_user(payload: CreateUserRequest) -> UserResponse:
        return controller.create_test_user(payload)

    @app.get("/api/v1/users/{user_id}", response_model=UserResponse, tags=["users"])
    async def get_user(user_id: str) -> UserResponse:
        return controller.get_user(user_id)
