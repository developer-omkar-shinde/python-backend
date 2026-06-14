"""Top-level route aggregator.

Registers all versioned routes onto the shared FastAPI app instance.
New versions (v2, v3 …) are added here without touching main.py.
"""

from __future__ import annotations

from fastapi import FastAPI

from onboarding.v1.routes import register_v1_routes


def register_routes(app: FastAPI) -> None:
    register_v1_routes(app)
