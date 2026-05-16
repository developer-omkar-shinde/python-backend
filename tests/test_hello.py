from fastapi.testclient import TestClient

from src.hello_api.main import app

client = TestClient(app)


def test_hello_world():
    """Test the /hello endpoint."""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "API is running"
