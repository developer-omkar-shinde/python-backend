"""Request schemas for user operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel, str_strip_whitespace=True):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
