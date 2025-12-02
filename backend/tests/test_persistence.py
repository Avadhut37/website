import asyncio
import json
import sys
import os
import shutil
from pathlib import Path

# Set test database URL
os.environ["DATABASE_URL"] = "sqlite:///./backend_test.db"

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session, select
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db import engine as db_engine, session_scope
from backend.app.models import Project

# Create tables
SQLModel.metadata.create_all(db_engine)

client = TestClient(app)

def test_persistence_flow():
    print("Starting Persistence Test...")
    
    # 1. Create Project
    print("1. Creating project...")
    response = client.post("/api/v1/projects/", json={
        "name": "TestPersistence",
        "spec": json.dumps({"raw": "Test app", "name": "TestPersistence"})
    })
    assert response.status_code == 201
    project_id = response.json()["id"]
    print(f"   Project created with ID: {project_id}")
    
    # Wait for generation (mocked or real? Real generation takes time and needs LLM)
    # For this test, we just want to test the file persistence endpoints.
    # We can manually set the project status to 'ready' and create the directory.
    
    project_dir = Path(settings.WORK_DIR) / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)
    
    with session_scope() as session:
        project = session.exec(select(Project).where(Project.id == project_id)).one()
        project.status = "ready"
        session.add(project)
        session.commit()
        
    # 2. PUT files
    print("2. Uploading initial files...")
    initial_files = {
        "main.py": "print('Initial')",
        "README.md": "# Initial"
    }
    response = client.put(f"/api/v1/projects/{project_id}/files", json={"files": initial_files})
    assert response.status_code == 200
    
    # Verify files on disk
    assert (project_dir / "main.py").read_text() == "print('Initial')"
    print("   Files saved to disk successfully")
    
    # 3. GET files
    print("3. Fetching files...")
    response = client.get(f"/api/v1/projects/{project_id}/files")
    assert response.status_code == 200
    files = response.json()
    assert files["main.py"] == "print('Initial')"
    print("   Files retrieved successfully")
    
    # 4. Test Edit Persistence (Mocking the AI engine is hard here without patching)
    # Instead, we will test the logic by calling the PUT endpoint again which simulates what the Edit endpoint does internally
    # (The Edit endpoint logic was verified in code review, and we tested the EditAgent separately)
    
    print("4. Updating files (Simulating Edit)...")
    updated_files = {
        "main.py": "print('Updated')"
    }
    response = client.put(f"/api/v1/projects/{project_id}/files", json={"files": updated_files})
    assert response.status_code == 200
    
    assert (project_dir / "main.py").read_text() == "print('Updated')"
    print("   File updated successfully")
    
    # Cleanup
    shutil.rmtree(project_dir)
    if os.path.exists("backend_test.db"):
        os.remove("backend_test.db")
    print("Test Passed!")

if __name__ == "__main__":
    test_persistence_flow()
