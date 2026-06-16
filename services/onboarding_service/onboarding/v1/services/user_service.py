"""Business logic for user operations."""

from __future__ import annotations

from dataclasses import dataclass

from helper.event_publisher import EventPublisher
from helper.domain_events import UserCreated
from onboarding.v1.repositories.user_repository import UserRepository
from onboarding.v1.schemas.responses.user_response import UserResponse


@dataclass
class UserServiceDeps:
    """Dependencies for UserService — avoids long __init__ signatures as the service grows."""

    user_repo: UserRepository
    event_publisher: EventPublisher


class UserService:
    def __init__(self, *, deps: UserServiceDeps) -> None:
        self._user_repo = deps.user_repo
        self._event_publisher = deps.event_publisher

    def create_user(self, first_name: str, last_name: str) -> UserResponse:
        """Create a new user and publish UserCreated event.

        Flow:
        1. Save user to DynamoDB
        2. Publish UserCreated event to SNS
        3. Other services react (send email, initialize features, etc.)
        """
        user_data = self._user_repo.create(first_name, last_name)

        # Publish flat domain event — consumers read fields directly
        self._event_publisher.publish(
            UserCreated(
                user_id=user_data["user_id"],
                first_name=first_name,
                last_name=last_name,
            )
        )

        return UserResponse(**user_data)

    def get_user(self, user_id: str) -> UserResponse:
        """Raises UserNotFoundError if user does not exist."""
        user_data = self._user_repo.get_by_id(user_id)
        return UserResponse(**user_data)
