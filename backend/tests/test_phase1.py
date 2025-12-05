"""Tests for Phase 1: DeepSeek + Manifest Schemas."""
import pytest
from app.ai.providers.deepseek import DeepSeekProvider
from app.schemas import ProjectManifest, validate_manifest, AppType, create_default_manifest
from pydantic import ValidationError


class TestDeepSeekProvider:
    """Test DeepSeek provider integration."""
    
    @pytest.mark.asyncio
    async def test_deepseek_available(self):
        """Test DeepSeek provider availability."""
        provider = DeepSeekProvider()
        # Should be available if OPENROUTER_API_KEY is set
        assert isinstance(provider.is_available(), bool)
    
    @pytest.mark.asyncio
    async def test_deepseek_generation(self):
        """Test DeepSeek text generation."""
        provider = DeepSeekProvider()
        
        if not provider.is_available():
            pytest.skip("DeepSeek API key not configured")
        
        response = await provider.generate(
            prompt="Explain the MVC architecture pattern in 2 sentences.",
            system_prompt="You are a software architecture expert.",
            max_tokens=100,
            temperature=0.5
        )
        
        assert response is not None
        assert len(response) > 20
        assert "MVC" in response or "Model" in response or "pattern" in response


class TestManifestSchemas:
    """Test manifest schema validation."""
    
    def test_valid_manifest(self):
        """Test valid manifest creation."""
        data = {
            "analysis": "Building a todo app with user auth",
            "app_type": "todo",
            "features": ["Add todos", "Mark complete", "User auth"],
            "models": [
                {
                    "name": "Todo",
                    "fields": {"id": "int", "title": "str", "completed": "bool"},
                    "relationships": []
                }
            ],
            "endpoints": [
                {
                    "path": "/todos",
                    "method": "GET",
                    "description": "List todos",
                    "response_model": "List[Todo]"
                }
            ],
            "files_to_generate": [
                {"path": "backend/main.py", "description": "FastAPI app", "dependencies": []},
                {"path": "backend/requirements.txt", "description": "Deps", "dependencies": []},
                {"path": "frontend/src/App.jsx", "description": "React", "dependencies": []},
                {"path": "frontend/package.json", "description": "NPM", "dependencies": []},
                {"path": "frontend/index.html", "description": "HTML", "dependencies": []},
                {"path": "frontend/vite.config.js", "description": "Vite", "dependencies": []},
                {"path": "frontend/src/main.jsx", "description": "Entry", "dependencies": []}
            ],
            "agents_needed": ["ARCH", "BACKEND", "UIX"],
            "priority": "Basic CRUD first"
        }
        
        manifest = validate_manifest(data)
        assert manifest.app_type == AppType.TODO
        assert len(manifest.features) == 3
        assert len(manifest.models) == 1
        assert manifest.models[0].name == "Todo"
    
    def test_invalid_manifest_missing_files(self):
        """Test manifest validation fails without required files."""
        data = {
            "analysis": "Test",
            "app_type": "crud",
            "features": ["Feature1"],
            "files_to_generate": [
                {"path": "backend/main.py", "description": "Test", "dependencies": []}
            ],
            "agents_needed": ["ARCH"],
            "priority": "Test"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_manifest(data)
        
        assert "Missing required files" in str(exc_info.value)
    
    def test_invalid_manifest_bad_app_type(self):
        """Test manifest validation fails with invalid app type."""
        data = {
            "analysis": "Test",
            "app_type": "invalid_type",
            "features": ["Feature1"],
            "files_to_generate": [],
            "agents_needed": ["ARCH"],
            "priority": "Test"
        }
        
        with pytest.raises(ValidationError):
            validate_manifest(data)
    
    def test_create_default_manifest(self):
        """Test default manifest creation."""
        manifest = create_default_manifest("TestApp", "A test application")
        
        assert manifest.app_type == AppType.CRUD
        assert len(manifest.features) >= 3
        assert len(manifest.models) >= 1
        assert len(manifest.endpoints) >= 2
        assert len(manifest.files_to_generate) >= 7
        
        # Check required files are present
        file_paths = [f.path for f in manifest.files_to_generate]
        assert "backend/main.py" in file_paths
        assert "frontend/src/App.jsx" in file_paths
        assert "frontend/package.json" in file_paths


# Run tests with:
# cd backend
# pytest tests/test_phase1.py -v
