"""Business logic for user operations."""

from __future__ import annotations

from dataclasses import dataclass

from onboarding.v1.repositories.user_repository import UserRepository
from onboarding.v1.schemas.responses.user_response import UserResponse


@dataclass
class UserServiceDeps:
    """Dependencies for UserService — avoids long __init__ signatures as the service grows."""

    user_repo: UserRepository


class UserService:
    def __init__(self, *, deps: UserServiceDeps) -> None:
        self._user_repo = deps.user_repo

    def create_user(self, first_name: str, last_name: str) -> UserResponse:
        user_data = self._user_repo.create(first_name, last_name)
        return UserResponse(**user_data)

    def get_user(self, user_id: str) -> UserResponse:
        """Raises UserNotFoundError if user does not exist."""
        user_data = self._user_repo.get_by_id(user_id)
        return UserResponse(**user_data)
