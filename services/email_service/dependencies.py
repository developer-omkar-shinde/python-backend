"""Dependency injection for email service.

Lazy singleton — mirrors bonus_platform_service/bonus_service_v2/dependencies.py.
"""

from __future__ import annotations

import boto3

from helper.utilities import get_logger

logger = get_logger(__name__)


class ServiceContainer:
    _instance: ServiceContainer | None = None

    def __new__(cls) -> ServiceContainer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        logger.info("Initializing email ServiceContainer")

        self._ses_client = boto3.client("ses", region_name="us-east-1")
        self._ddb_resource = boto3.resource("dynamodb", region_name="us-east-1")

        # Lazily initialized
        self._email_adapter = None

        self._initialized = True
        logger.info("Email ServiceContainer initialized")

    def get_email_service(self):
        if self._email_adapter is None:
            from email_service.adapters.email_adapter import EmailAdapter  # noqa: PLC0415
            self._email_adapter = EmailAdapter(
                ses_client=self._ses_client,
                ddb_resource=self._ddb_resource,
            )
        return self._email_adapter

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton. Only for tests."""
        cls._instance = None


container = ServiceContainer()
