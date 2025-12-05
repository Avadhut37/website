"""Tests for Phase 4: Project Memory/RAG."""
import pytest
from pathlib import Path

from app.services.memory import (
    ProjectMemory,
    get_project_memory,
    clear_project_memory,
    get_embedding_model,
    get_chroma_client,
)


class TestEmbeddingModel:
    """Test embedding model initialization."""
    
    def test_embedding_model_singleton(self):
        """Test embedding model is singleton."""
        model1 = get_embedding_model()
        model2 = get_embedding_model()
        
        assert model1 is model2
        assert model1 is not None
    
    def test_embedding_dimensions(self):
        """Test embedding dimensions."""
        model = get_embedding_model()
        text = "This is a test string for embeddings"
        embedding = model.encode(text)
        
        # all-MiniLM-L6-v2 produces 384-dimensional embeddings
        assert embedding.shape[0] == 384


class TestChromaDB:
    """Test ChromaDB client initialization."""
    
    def test_chroma_client_singleton(self):
        """Test ChromaDB client is singleton."""
        client1 = get_chroma_client()
        client2 = get_chroma_client()
        
        assert client1 is client2
        assert client1 is not None
    
    def test_chroma_collections(self):
        """Test ChromaDB collections creation."""
        client = get_chroma_client()
        collections = client.list_collections()
        
        assert collections is not None


class TestProjectMemory:
    """Test ProjectMemory class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and teardown for each test."""
        # Clear memory before each test
        clear_project_memory(999)
        yield
        # Cleanup after test
        clear_project_memory(999)
    
    def test_memory_initialization(self):
        """Test memory initialization."""
        memory = ProjectMemory(project_id=999)
        
        assert memory.project_id == 999
        assert memory.embedding_model is not None
        assert memory.client is not None
        assert memory.code_collection is not None
        assert memory.decisions_collection is not None
        assert memory.preferences_collection is not None
        assert memory.constraints_collection is not None
    
    def test_store_code(self):
        """Test storing code snippets."""
        memory = ProjectMemory(project_id=999)
        
        code = """
def hello_world():
    print("Hello, World!")
"""
        
        memory.store_code(
            filepath="main.py",
            code=code,
            language="python",
            description="Simple hello world function"
        )
        
        # Search for the code
        results = memory.search_code("hello world function", n_results=1)
        
        assert len(results) > 0
        assert "hello_world" in results[0]["content"]
        assert results[0]["metadata"]["filepath"] == "main.py"
        assert results[0]["metadata"]["language"] == "python"
    
    def test_store_decision(self):
        """Test storing development decisions."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_decision(
            decision="Use FastAPI for backend",
            reasoning="FastAPI provides automatic API docs, type checking, and async support",
            context={"alternatives": ["Flask", "Django"], "priority": "high"}
        )
        
        # Search for the decision
        results = memory.search_decisions("backend framework", n_results=1)
        
        assert len(results) > 0
        assert "FastAPI" in results[0]["content"]
        assert results[0]["metadata"]["decision"] == "Use FastAPI for backend"
    
    def test_store_preference(self):
        """Test storing project preferences."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_preference("ui_framework", "React", category="frontend")
        memory.store_preference("styling", "Tailwind CSS", category="frontend")
        memory.store_preference("database", "PostgreSQL", category="backend")
        
        # Get all preferences
        preferences = memory.get_all_preferences()
        
        assert "ui_framework" in preferences
        assert preferences["ui_framework"] == "React"
        assert "styling" in preferences
        assert preferences["styling"] == "Tailwind CSS"
    
    def test_store_constraint(self):
        """Test storing project constraints."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_constraint(
            "Must support dark mode",
            severity="must",
            scope="frontend"
        )
        memory.store_constraint(
            "Should use environment variables for secrets",
            severity="should",
            scope="backend"
        )
        
        # Get must constraints
        must_constraints = memory.get_all_constraints(severity="must")
        assert len(must_constraints) > 0
        assert "Must support dark mode" in must_constraints
        
        # Get should constraints
        should_constraints = memory.get_all_constraints(severity="should")
        assert len(should_constraints) > 0
        assert "Should use environment variables for secrets" in should_constraints
    
    def test_search_code_with_language_filter(self):
        """Test searching code with language filter."""
        memory = ProjectMemory(project_id=999)
        
        # Store Python code
        memory.store_code(
            "main.py",
            "def process_data(data): return data.upper()",
            "python"
        )
        
        # Store JavaScript code
        memory.store_code(
            "app.js",
            "function processData(data) { return data.toUpperCase(); }",
            "javascript"
        )
        
        # Search for Python only
        python_results = memory.search_code("process data", n_results=5, language="python")
        
        assert len(python_results) > 0
        assert all(r["metadata"]["language"] == "python" for r in python_results)
    
    def test_search_preferences_by_category(self):
        """Test searching preferences by category."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_preference("framework", "React", category="frontend")
        memory.store_preference("styling", "Tailwind", category="frontend")
        memory.store_preference("server", "FastAPI", category="backend")
        
        # Search frontend preferences
        frontend_results = memory.search_preferences(
            "user interface",
            n_results=10,
            category="frontend"
        )
        
        assert len(frontend_results) > 0
        assert all(r["metadata"]["category"] == "frontend" for r in frontend_results)
    
    def test_search_constraints_by_severity(self):
        """Test searching constraints by severity."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_constraint("Must be accessible", severity="must")
        memory.store_constraint("Should be fast", severity="should")
        memory.store_constraint("Nice to have animations", severity="nice-to-have")
        
        # Search must constraints
        must_results = memory.search_constraints("requirements", severity="must")
        
        assert len(must_results) > 0
        assert all(r["metadata"]["severity"] == "must" for r in must_results)
    
    def test_get_context_for_generation(self):
        """Test getting comprehensive context."""
        memory = ProjectMemory(project_id=999)
        
        # Add various memory types
        memory.store_code("utils.py", "def helper(): pass", "python")
        memory.store_decision("Use async/await", "Better performance")
        memory.store_preference("theme", "dark", category="ui")
        memory.store_constraint("Must be secure", severity="must")
        memory.store_constraint("Should be tested", severity="should")
        
        # Get context
        context = memory.get_context_for_generation("build a secure app", max_results=10)
        
        assert "similar_code" in context
        assert "past_decisions" in context
        assert "preferences" in context
        assert "constraints" in context
        assert "suggestions" in context
        
        assert "theme" in context["preferences"]
        assert "Must be secure" in context["constraints"]
        assert "Should be tested" in context["suggestions"]
    
    def test_clear_memory_specific_type(self):
        """Test clearing specific memory type."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_code("test.py", "print('test')", "python")
        memory.store_preference("key", "value")
        
        # Clear only code
        memory.clear_memory("code")
        
        # Code should be gone
        code_results = memory.search_code("test", n_results=10)
        assert len(code_results) == 0
        
        # Preferences should remain
        prefs = memory.get_all_preferences()
        assert "key" in prefs
    
    def test_clear_memory_all(self):
        """Test clearing all memory."""
        memory = ProjectMemory(project_id=999)
        
        memory.store_code("test.py", "print('test')", "python")
        memory.store_decision("Test decision", "Test reasoning")
        memory.store_preference("key", "value")
        memory.store_constraint("Test constraint", "must")
        
        # Clear all
        memory.clear_memory()
        
        # Everything should be gone
        assert len(memory.search_code("test", n_results=10)) == 0
        assert len(memory.search_decisions("test", n_results=10)) == 0
        assert len(memory.get_all_preferences()) == 0
        assert len(memory.get_all_constraints()) == 0
    
    def test_similarity_scoring(self):
        """Test similarity scoring in search results."""
        memory = ProjectMemory(project_id=999)
        
        # Store related and unrelated code
        memory.store_code(
            "auth.py",
            "def login_user(username, password): return authenticate(username, password)",
            "python",
            "User authentication function"
        )
        memory.store_code(
            "math.py",
            "def calculate_sum(a, b): return a + b",
            "python",
            "Simple math function"
        )
        
        # Search for authentication
        results = memory.search_code("user login authentication", n_results=2)
        
        assert len(results) > 0
        # auth.py should have higher similarity
        assert results[0]["similarity"] > 0.5
        assert "auth.py" in results[0]["metadata"]["filepath"]


class TestMemoryService:
    """Test memory service singleton."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and teardown."""
        clear_project_memory(888)
        yield
        clear_project_memory(888)
    
    def test_get_project_memory_singleton(self):
        """Test project memory singleton per project."""
        memory1 = get_project_memory(888)
        memory2 = get_project_memory(888)
        
        assert memory1 is memory2
        assert memory1.project_id == 888
    
    def test_multiple_project_memories(self):
        """Test multiple projects have separate memories."""
        memory_a = get_project_memory(100)
        memory_b = get_project_memory(200)
        
        assert memory_a is not memory_b
        assert memory_a.project_id == 100
        assert memory_b.project_id == 200
        
        # Cleanup
        clear_project_memory(100)
        clear_project_memory(200)


class TestMemoryIntegration:
    """Integration tests for memory system."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup and teardown."""
        clear_project_memory(777)
        yield
        clear_project_memory(777)
    
    def test_full_project_workflow(self):
        """Test complete project memory workflow."""
        memory = get_project_memory(777)
        
        # 1. Store initial project setup
        memory.store_preference("framework", "FastAPI", category="backend")
        memory.store_preference("frontend", "React", category="frontend")
        memory.store_constraint("Must use TypeScript", severity="must", scope="frontend")
        memory.store_constraint("Should have tests", severity="should", scope="global")
        
        # 2. Store development decisions
        memory.store_decision(
            "Use Pydantic for validation",
            "Provides automatic validation and serialization",
            context={"integration": "FastAPI"}
        )
        
        # 3. Store generated code
        backend_code = """
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
"""
        memory.store_code("backend/main.py", backend_code, "python", "FastAPI app")
        
        frontend_code = """
function App() {
  return <div>Hello World</div>
}
"""
        memory.store_code("frontend/App.jsx", frontend_code, "javascript", "React component")
        
        # 4. Get context for next iteration
        context = memory.get_context_for_generation("add authentication to app")
        
        # Verify we have all the context
        assert "framework" in context["preferences"]
        assert context["preferences"]["framework"] == "FastAPI"
        assert "Must use TypeScript" in context["constraints"]
        assert len(context["similar_code"]) > 0
        assert len(context["past_decisions"]) > 0
        
        # 5. Search for specific code
        results = memory.search_code("FastAPI application", n_results=5)
        assert len(results) > 0
        assert any("FastAPI" in r["content"] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
