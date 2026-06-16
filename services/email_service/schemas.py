"""Pydantic schemas for email service requests/responses."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SendEmailRequest(BaseModel):
    """Request to send email."""

    user_id: str = Field(..., description="User ID")
    email: EmailStr = Field(..., description="Recipient email")
    template: str = Field(..., description="Email template name")
    data: dict = Field(default_factory=dict, description="Template variables")


class SendEmailResponse(BaseModel):
    """Response from email send."""

    success: bool
    user_id: str
    email: str
    message_id: str | None = None
    error: str | None = None


class EmailEvent(BaseModel):
    """Domain event for email sending."""

    event_type: str = Field(..., description="Event type (UserCreated, etc)")
    aggregate_id: str = Field(..., description="User ID")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    data: dict = Field(..., description="Event data")
