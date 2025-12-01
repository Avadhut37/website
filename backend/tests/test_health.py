"""API health and basic endpoint tests."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.main import app, create_db_and_tables  # noqa: E402


create_db_and_tables()


def test_app_starts():
    """Test that the app starts and responds to requests."""
    client = TestClient(app)
    response = client.get("/api/v1/projects/9999")
    assert response.status_code in {200, 404}


def test_root_endpoint():
    """Test the root endpoint returns API info."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "endpoints" in data
    assert "api_version" in data


def test_health_endpoint():
    """Test the health check endpoint."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_status():
    """Test the API status endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ai" in data


def test_create_project():
    """Test project creation endpoint."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/projects/",
        json={"name": "TestApp", "spec": '{"description": "test app"}'}
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "status" in data
    assert data["status"] == "pending"
    assert "message" in data


def test_create_project_legacy():
    """Test legacy project creation endpoint."""
    client = TestClient(app)
    response = client.post(
        "/projects/",
        json={"name": "LegacyTest", "spec": '{"description": "legacy test"}'}
    )
    assert response.status_code == 201


def test_create_project_validation():
    """Test project creation validation."""
    client = TestClient(app)
    # Missing name
    response = client.post("/api/v1/projects/", json={"spec": "test"})
    assert response.status_code == 422
    
    # Empty name
    response = client.post("/api/v1/projects/", json={"name": "", "spec": "test"})
    assert response.status_code == 422
    
    # Missing spec
    response = client.post("/api/v1/projects/", json={"name": "Test"})
    assert response.status_code == 422


def test_get_nonexistent_project():
    """Test getting a project that doesn't exist."""
    client = TestClient(app)
    response = client.get("/api/v1/projects/99999")
    assert response.status_code == 404


def test_list_projects():
    """Test listing projects with pagination."""
    client = TestClient(app)
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data


def test_ai_models():
    """Test AI models endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai/models")
    assert response.status_code == 200
    data = response.json()
    assert "openrouter" in data
    assert "current" in data


def test_ai_status():
    """Test AI status endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/ai/status")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "available" in data
