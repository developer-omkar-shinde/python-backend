"""Request-scoped context variables for correlation IDs."""

from __future__ import annotations

import uuid
from contextvars import ContextVar

REQUEST_ID_RESPONSE_HEADER = "X-Request-Id"

_request_id: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(request_id: str) -> object:
    return _request_id.set(request_id)


def reset_request_id(token: object) -> None:
    _request_id.reset(token)  # type: ignore[arg-type]


def resolve_request_id_from_headers(headers: object) -> str:
    raw = getattr(headers, "get", lambda k, d=None: d)(REQUEST_ID_RESPONSE_HEADER)
    return str(raw) if raw else str(uuid.uuid4())
