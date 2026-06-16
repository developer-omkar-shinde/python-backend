"""Email service — processes onboarding domain events from SQS (via SNS)."""

from __future__ import annotations

from helper.utilities import get_logger

logger = get_logger(__name__)
