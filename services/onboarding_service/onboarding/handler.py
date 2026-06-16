"""Onboarding domain event handlers.

Each handler is registered with @registry.register_queue_event() at import time.
The Lambda entry point dispatches to handlers via registry.get_queue_handler().

Adding a new event type: add a function here with the decorator. Zero other files change.

Mirrors bonus_platform_service/bonus_service_v2/modules/referral/handlers/referral_handler.py
"""

from __future__ import annotations

from . import logger
from .registry import registry


@registry.register_queue_event("UserCreated")
def handle_user_created(data: dict) -> None:
    """Handle UserCreated domain event.

    In production this would:
    - Send welcome email
    - Initialize user preferences
    - Log analytics
    """
    user_id = data.get("user_id", "")
    email = data.get("email", "")
    first_name = data.get("first_name", "")

    logger.info(
        "Processing UserCreated — user_id=%s email=%s first_name=%s",
        user_id,
        email,
        first_name,
    )

    # TODO: wire in email service use case
    # TODO: initialize user preferences


@registry.register_queue_event("UserVerified")
def handle_user_verified(data: dict) -> None:
    """Handle UserVerified domain event.

    In production this would:
    - Send verification confirmation email
    - Unlock premium features
    """
    user_id = data.get("user_id", "")
    verification_type = data.get("verification_type", "")

    logger.info(
        "Processing UserVerified — user_id=%s verification_type=%s",
        user_id,
        verification_type,
    )

    # TODO: send verification confirmation email
    # TODO: unlock premium features


@registry.register_queue_event("UserDeleted")
def handle_user_deleted(data: dict) -> None:
    """Handle UserDeleted domain event.

    In production this would:
    - Archive user data
    - Clean up resources
    """
    user_id = data.get("user_id", "")
    reason = data.get("reason", "")

    logger.info(
        "Processing UserDeleted — user_id=%s reason=%s",
        user_id,
        reason,
    )

    # TODO: archive user data
    # TODO: clean up resources
