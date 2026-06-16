"""Dependency Injection Container for the onboarding service.

Singleton that lazily creates infrastructure adapters on first access.
Mirrors bonus_platform_service/bonus_service_v2/dependencies.py from the reference repo.

Each get_*() method initializes its dependency once and caches it for the
lifetime of the warm Lambda container.
"""

from __future__ import annotations

import os

import boto3

from helper.event_publisher import EventPublisher, make_user_events_publisher
from helper.utilities import get_logger
from onboarding.v1.controllers.user_controller import UserController
from onboarding.v1.repositories.user_repository import UserRepository
from onboarding.v1.services.user_service import UserService, UserServiceDeps

logger = get_logger(__name__)

TABLE_NAME = os.environ.get("USERS_TABLE_NAME", "test_users")


class ServiceContainer:
    _instance: ServiceContainer | None = None

    def __new__(cls) -> ServiceContainer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        logger.info("Initializing onboarding ServiceContainer")

        self._dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self._users_table = self._dynamodb.Table(TABLE_NAME)

        # Lazily initialized — None until first get_*() call
        self._user_repo: UserRepository | None = None
        self._event_publisher: EventPublisher | None = None
        self._user_service: UserService | None = None
        self._user_controller: UserController | None = None

        self._initialized = True
        logger.info("Onboarding ServiceContainer initialized")

    def get_user_repository(self) -> UserRepository:
        if self._user_repo is None:
            self._user_repo = UserRepository(table=self._users_table)
        return self._user_repo

    def get_event_publisher(self) -> EventPublisher:
        if self._event_publisher is None:
            self._event_publisher = make_user_events_publisher()
        return self._event_publisher

    def get_user_service(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(
                deps=UserServiceDeps(
                    user_repo=self.get_user_repository(),
                    event_publisher=self.get_event_publisher(),
                )
            )
        return self._user_service

    def get_user_controller(self) -> UserController:
        if self._user_controller is None:
            self._user_controller = UserController(
                user_service=self.get_user_service()
            )
        return self._user_controller

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton. Only for tests."""
        cls._instance = None


container = ServiceContainer()
