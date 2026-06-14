from datetime import UTC, datetime

from fastapi import FastAPI

from helper.eks_request_middleware import register_eks_request_correlation_middleware
from helper.utilities import get_logger
from onboarding.routes import register_routes

logger = get_logger(__name__, service_name="onboarding-service")

app = FastAPI(title="Onboarding Service")

register_eks_request_correlation_middleware(app, logger)
register_routes(app)


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}

@app.get("/ready")
def ready():
    return {"status": "ready"}
