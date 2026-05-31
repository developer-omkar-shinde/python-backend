FROM python:3.11-slim

USER root
WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "src.hello_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
