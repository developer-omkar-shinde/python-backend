"""Use case: Send welcome email to new user."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def send_welcome_email(
    user_id: str,
    email_service: Any,
    first_name: str,
    last_name: str,
    email: str,
) -> dict[str, Any]:
    """Send welcome email after user creation.

    Pure business logic — no AWS types.
    Can be tested independently.

    Args:
        user_id: User ID
        email_service: Injected email service adapter
        first_name: User's first name
        last_name: User's last name
        email: User's email address

    Returns:
        Result dict with success status
    """
    try:
        email_service.send_welcome_email(
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        logger.info(f"Welcome email sent to {email} for user {user_id}")
        return {"success": True, "user_id": user_id, "email": email}

    except Exception as exc:
        logger.error(f"Failed to send welcome email to {email}: {exc}")
        return {"success": False, "user_id": user_id, "error": str(exc)}
