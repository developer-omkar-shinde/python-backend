"""FastAPI middleware for request correlation on EKS HTTP services.

Mirrors the trivelta helper.eks_request_middleware interface exactly.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request

from helper.log_sampling import set_request_sampled
from helper.request_context import (
    REQUEST_ID_RESPONSE_HEADER,
    reset_request_id,
    resolve_request_id_from_headers,
    set_request_id,
)


async def bind_request_id_middleware(request: Request, call_next):
    """Set request_id for the request scope; echo it on the response."""
    request_id = resolve_request_id_from_headers(request.headers)
    token = set_request_id(request_id)
    set_request_sampled(request_id)
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_RESPONSE_HEADER] = request_id
        return response
    finally:
        reset_request_id(token)


async def request_access_log_middleware(
    request: Request, call_next, logger: logging.Logger
):
    """Log one line per HTTP request."""
    start = datetime.now(UTC)
    try:
        response = await call_next(request)
    except Exception:
        duration = (datetime.now(UTC) - start).total_seconds()
        logger.exception(
            "Request: %s %s - failed - Duration: %ss",
            request.method,
            request.url.path,
            duration,
        )
        raise
    duration = (datetime.now(UTC) - start).total_seconds()
    logger.info(
        "Request: %s %s - Status: %s - Duration: %ss",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


def register_eks_request_correlation_middleware(
    app: FastAPI,
    logger: logging.Logger,
    *,
    access_log: bool = True,
) -> None:
    """Register HTTP middleware for request_id correlation.

    FastAPI applies middleware LIFO — last registered runs first.
    bind_request_id is always registered last so request_id is set
    before any log line fires.
    """
    if access_log:

        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            return await request_access_log_middleware(request, call_next, logger)

    @app.middleware("http")
    async def bind_request_id(request: Request, call_next):
        return await bind_request_id_middleware(request, call_next)
