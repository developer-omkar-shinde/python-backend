"""DynamoDB repository for user operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from botocore.exceptions import ClientError

from onboarding.v1.domain.exceptions import UserNotFoundError


class UserRepository:
    """Handles all DynamoDB operations for users.

    The DynamoDB table is injected — not created here.
    The ServiceContainer owns the boto3 resource and wires it in.
    """

    def __init__(self, table: object) -> None:
        self._table = table

    def create(self, first_name: str, last_name: str) -> dict:
        user_id = str(uuid.uuid4())
        created_at = datetime.now(UTC).isoformat()

        item = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": created_at,
        }

        try:
            self._table.put_item(Item=item)
            return item
        except ClientError as exc:
            raise Exception(f"DynamoDB put_item failed: {exc}") from exc

    def get_by_id(self, user_id: str) -> dict:
        try:
            response = self._table.get_item(Key={"user_id": user_id})
        except ClientError as exc:
            raise Exception(f"DynamoDB get_item failed: {exc}") from exc

        item = response.get("Item")
        if not item:
            raise UserNotFoundError("error.user_not_found")
        return item
