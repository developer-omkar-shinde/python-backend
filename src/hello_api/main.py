from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Hello World API",
    version="0.1.0",
    description="Learning backend API",
)


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/hello")
async def hello_world():
    """Returns a hello world message."""
    return JSONResponse(status_code=200, content={"message": "Hello World"})

@app.get("/thankspy")
async def thanks_world():
    """Returns a hello world message."""
    return JSONResponse(status_code=200, content={"message": "Thanks World"})



@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(status_code=200, content={"status": "API is running"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
