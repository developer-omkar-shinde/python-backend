"""Use case: Send verification email."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def send_verification_email(
    user_id: str,
    email_service: Any,
    verification_type: str = "email",
) -> dict[str, Any]:
    """Send verification email.

    Args:
        user_id: User ID
        email_service: Injected email service adapter
        verification_type: Type of verification (email, phone, kyc)

    Returns:
        Result dict with success status
    """
    try:
        logger.info(
            f"Sending {verification_type} verification for user {user_id}"
        )

        # Would call email_service method here
        # For now, just log

        return {
            "success": True,
            "user_id": user_id,
            "verification_type": verification_type,
        }

    except Exception as exc:
        logger.error(f"Failed to send verification email: {exc}")
        return {"success": False, "user_id": user_id, "error": str(exc)}
