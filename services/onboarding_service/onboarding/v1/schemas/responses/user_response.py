"""Response schemas for user operations."""

from __future__ import annotations

from pydantic import BaseModel


class UserResponse(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    created_at: str
