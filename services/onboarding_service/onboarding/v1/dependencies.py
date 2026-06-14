"""Dependency wiring for the onboarding service v1.

ServiceContainer is a singleton that builds and holds all layers:
  infrastructure → repositories → services → controllers

This mirrors the trivelta onboarding v2 pattern exactly.
Routes call container.get_*_controller() to obtain pre-wired instances.
"""

from __future__ import annotations

import boto3

from onboarding.v1.controllers.user_controller import UserController
from onboarding.v1.repositories.user_repository import UserRepository
from onboarding.v1.services.user_service import UserService, UserServiceDeps

TABLE_NAME = "test_users"


class ServiceContainer:
    _instance: ServiceContainer | None = None

    def __new__(cls) -> ServiceContainer:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialize()
            cls._instance = instance
        return cls._instance

    def _initialize(self) -> None:
        self._init_infrastructure()
        self._init_repositories()
        self._init_services()
        self._init_controllers()

    def _init_infrastructure(self) -> None:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self._users_table = dynamodb.Table(TABLE_NAME)

    def _init_repositories(self) -> None:
        self._user_repo = UserRepository(table=self._users_table)

    def _init_services(self) -> None:
        self._user_service = UserService(
            deps=UserServiceDeps(user_repo=self._user_repo)
        )

    def _init_controllers(self) -> None:
        self._user_controller = UserController(user_service=self._user_service)

    def get_user_controller(self) -> UserController:
        return self._user_controller


container = ServiceContainer()
