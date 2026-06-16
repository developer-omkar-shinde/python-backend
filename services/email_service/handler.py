"""Email service event handlers.

Each handler is registered with @registry.register_queue_event() at import time.
The Lambda entry point dispatches to handlers via registry.get_queue_handler().

Mirrors onboarding/handler.py pattern.
"""

from __future__ import annotations

from . import logger
from .dependencies import container
from .registry import registry
from .use_cases.send_verification_email import send_verification_email
from .use_cases.send_welcome_email import send_welcome_email


@registry.register_queue_event("UserCreated")
def handle_user_created(data: dict) -> None:
    """Handle UserCreated — send welcome email via SES."""
    user_id = data.get("user_id", "")
    email = data.get("email", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")

    logger.info("Sending welcome email — user_id=%s email=%s", user_id, email)

    send_welcome_email(
        user_id=user_id,
        email_service=container.get_email_service(),
        first_name=first_name,
        last_name=last_name,
        email=email,
    )


@registry.register_queue_event("UserVerified")
def handle_user_verified(data: dict) -> None:
    """Handle UserVerified — send verification confirmation email."""
    user_id = data.get("user_id", "")
    verification_type = data.get("verification_type", "email")

    logger.info(
        "Sending verification email — user_id=%s verification_type=%s",
        user_id,
        verification_type,
    )

    send_verification_email(
        user_id=user_id,
        email_service=container.get_email_service(),
        verification_type=verification_type,
    )
