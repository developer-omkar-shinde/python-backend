"""Domain exceptions for user operations.

Services raise these; controllers catch them and map to HTTP responses.
This keeps HTTP concerns out of the service layer.
"""

from __future__ import annotations


class UserError(Exception):
    """Base exception for user domain errors."""

    def __init__(self, code: str, details: dict | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.details = details


class UserAlreadyExistsError(UserError):
    pass


class UserNotFoundError(UserError):
    pass
