FROM python:3.11-slim

# Create non-root user matching the trivelta base image convention
RUN groupadd -r appuser && useradd -r -g appuser appuser

USER root

WORKDIR /app

# Copy shared helper code from repo root
COPY helper/ /app/helper/

# Copy service code
COPY services/onboarding_service/onboarding/ /app/onboarding/

# Install service deps and fix ownership
RUN pip install --no-cache-dir -r /app/onboarding/requirements.txt && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "onboarding.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
