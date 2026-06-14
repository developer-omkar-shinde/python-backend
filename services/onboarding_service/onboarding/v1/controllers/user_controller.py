"""HTTP controllers for user operations."""

from __future__ import annotations

import traceback

from fastapi import HTTPException, status

from helper.utilities import get_logger
from onboarding.v1.domain.exceptions import UserNotFoundError
from onboarding.v1.schemas.requests.user_request import CreateUserRequest
from onboarding.v1.schemas.responses.user_response import UserResponse
from onboarding.v1.services.user_service import UserService

logger = get_logger(__name__, service_name="onboarding-service")


class UserController:
    def __init__(self, *, user_service: UserService) -> None:
        self._service = user_service

    def create_test_user(self, payload: CreateUserRequest) -> UserResponse:
        try:
            return self._service.create_user(payload.first_name, payload.last_name)
        except Exception as exc:
            logger.error(f"Failed to create user: {exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {exc}",
            ) from exc

    def get_user(self, user_id: str) -> UserResponse:
        try:
            return self._service.get_user(user_id)
        except UserNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve user: {exc}",
            ) from exc
