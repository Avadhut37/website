"""
Test all AI providers to verify they are responding correctly.

Run with: pytest tests/test_ai_providers.py -v
Or standalone: python tests/test_ai_providers.py
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestAIProviders:
    """Test suite for all AI provider APIs."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        from app.core.config import settings
        self.settings = settings
    
    # ==================== GEMINI ====================
    
    def test_gemini_api_key_exists(self):
        """Test that Gemini API key is configured."""
        from app.core.config import settings
        assert settings.GEMINI_API_KEY, "GEMINI_API_KEY not configured"
        assert settings.GEMINI_API_KEY.startswith("AIza"), "Invalid Gemini API key format"
    
    def test_gemini_provider_available(self):
        """Test that Gemini provider is available."""
        from app.ai.providers.gemini import GeminiProvider
        provider = GeminiProvider()
        assert provider.is_available(), "Gemini provider not available"
    
    @pytest.mark.asyncio
    async def test_gemini_generation(self):
        """Test Gemini can generate a response."""
        from app.ai.providers.gemini import GeminiProvider
        provider = GeminiProvider()
        
        if not provider.is_available():
            pytest.skip("Gemini API key not configured")
        
        start = time.time()
        response = await provider.generate(
            prompt="Say 'Hello, I am Gemini!' in exactly those words.",
            max_tokens=50,
            temperature=0.1
        )
        duration = time.time() - start
        
        assert response is not None, "Gemini returned no response"
        assert len(response) > 0, "Gemini returned empty response"
        assert "gemini" in response.lower() or "hello" in response.lower(), f"Unexpected response: {response}"
        print(f"\n✅ Gemini responded in {duration:.2f}s: {response[:100]}...")
    
    # ==================== GROQ ====================
    
    def test_groq_api_key_exists(self):
        """Test that Groq API key is configured."""
        from app.core.config import settings
        assert settings.GROQ_API_KEY, "GROQ_API_KEY not configured"
        assert settings.GROQ_API_KEY.startswith("gsk_"), "Invalid Groq API key format"
    
    def test_groq_provider_available(self):
        """Test that Groq provider is available."""
        from app.ai.providers.groq import GroqProvider
        provider = GroqProvider()
        assert provider.is_available(), "Groq provider not available"
    
    @pytest.mark.asyncio
    async def test_groq_generation(self):
        """Test Groq can generate a response."""
        from app.ai.providers.groq import GroqProvider
        provider = GroqProvider()
        
        if not provider.is_available():
            pytest.skip("Groq API key not configured")
        
        start = time.time()
        response = await provider.generate(
            prompt="Say 'Hello, I am Groq!' in exactly those words.",
            max_tokens=50,
            temperature=0.1
        )
        duration = time.time() - start
        
        assert response is not None, "Groq returned no response"
        assert len(response) > 0, "Groq returned empty response"
        print(f"\n✅ Groq responded in {duration:.2f}s: {response[:100]}...")
    
    @pytest.mark.asyncio
    async def test_groq_code_generation(self):
        """Test Groq can generate code (its specialty)."""
        from app.ai.providers.groq import GroqProvider
        provider = GroqProvider()
        
        if not provider.is_available():
            pytest.skip("Groq API key not configured")
        
        start = time.time()
        response = await provider.generate(
            prompt="Write a Python function that adds two numbers. Return only the code.",
            max_tokens=200,
            temperature=0.1
        )
        duration = time.time() - start
        
        assert response is not None, "Groq returned no response"
        assert "def " in response, f"Groq didn't generate Python code: {response}"
        print(f"\n✅ Groq code generation in {duration:.2f}s")
    
    # ==================== CEREBRAS ====================
    
    def test_cerebras_api_key_exists(self):
        """Test that Cerebras API key is configured."""
        from app.core.config import settings
        assert settings.CEREBRAS_API_KEY, "CEREBRAS_API_KEY not configured"
        assert settings.CEREBRAS_API_KEY.startswith("csk-"), "Invalid Cerebras API key format"
    
    def test_cerebras_provider_available(self):
        """Test that Cerebras provider is available."""
        from app.ai.providers.cerebras import CerebrasProvider
        provider = CerebrasProvider()
        assert provider.is_available(), "Cerebras provider not available"
    
    @pytest.mark.asyncio
    async def test_cerebras_generation(self):
        """Test Cerebras can generate a response."""
        from app.ai.providers.cerebras import CerebrasProvider
        provider = CerebrasProvider()
        
        if not provider.is_available():
            pytest.skip("Cerebras API key not configured")
        
        start = time.time()
        response = await provider.generate(
            prompt="Say 'Hello, I am Cerebras!' in exactly those words.",
            max_tokens=50,
            temperature=0.1
        )
        duration = time.time() - start
        
        assert response is not None, "Cerebras returned no response"
        assert len(response) > 0, "Cerebras returned empty response"
        print(f"\n✅ Cerebras responded in {duration:.2f}s: {response[:100]}...")
    
    # ==================== OPENROUTER ====================
    
    def test_openrouter_api_key_exists(self):
        """Test that OpenRouter API key is configured."""
        from app.core.config import settings
        assert settings.OPENROUTER_API_KEY, "OPENROUTER_API_KEY not configured"
        assert settings.OPENROUTER_API_KEY.startswith("sk-or-"), "Invalid OpenRouter API key format"
    
    def test_openrouter_provider_available(self):
        """Test that OpenRouter provider is available."""
        from app.ai.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()
        assert provider.is_available(), "OpenRouter provider not available"
    
    @pytest.mark.asyncio
    async def test_openrouter_generation(self):
        """Test OpenRouter can generate a response."""
        from app.ai.providers.openrouter import OpenRouterProvider
        provider = OpenRouterProvider(use_free_only=True)
        
        if not provider.is_available():
            pytest.skip("OpenRouter API key not configured")
        
        start = time.time()
        response = await provider.generate(
            prompt="Say 'Hello, I am OpenRouter!' in exactly those words.",
            max_tokens=50,
            temperature=0.1
        )
        duration = time.time() - start
        
        assert response is not None, "OpenRouter returned no response"
        assert len(response) > 0, "OpenRouter returned empty response"
        print(f"\n✅ OpenRouter responded in {duration:.2f}s: {response[:100]}...")


class TestAIEngine:
    """Test the AI Engine and multi-agent system."""
    
    def test_ai_engine_initialization(self):
        """Test AI Engine initializes correctly."""
        from app.ai.engine import get_ai_engine
        engine = get_ai_engine()
        
        assert engine is not None, "AI Engine failed to initialize"
        assert len(engine.providers) > 0, "No providers available"
        print(f"\n✅ AI Engine initialized with {len(engine.providers)} providers")
    
    def test_ai_engine_status(self):
        """Test AI Engine status endpoint."""
        from app.ai.engine import get_ai_engine
        engine = get_ai_engine()
        status = engine.get_status()
        
        assert "providers" in status, "Status missing providers"
        assert "available" in status, "Status missing available flag"
        assert status["available"], "AI Engine reports not available"
        print(f"\n✅ AI Engine status: {len(status['providers'])} providers active")
    
    def test_multi_agent_orchestrator(self):
        """Test multi-agent orchestrator initialization."""
        from app.ai.engine import get_ai_engine
        engine = get_ai_engine()
        
        assert engine.orchestrator is not None, "Orchestrator not initialized"
        assert len(engine.orchestrator.agents) == 5, f"Expected 5 agents, got {len(engine.orchestrator.agents)}"
        print(f"\n✅ Multi-agent orchestrator ready with {len(engine.orchestrator.agents)} agents")


class TestAPIEndpoints:
    """Test the API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("\n✅ Health endpoint OK")
    
    def test_ai_status_endpoint(self, client):
        """Test AI status endpoint."""
        response = client.get("/api/v1/ai/status")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert data["available"] == True
        print(f"\n✅ AI Status: {data['provider_count']} providers")
    
    def test_ai_preview_endpoint(self, client):
        """Test AI preview generation endpoint."""
        response = client.post(
            "/api/v1/ai/preview",
            json={"spec": {"raw": "Simple hello world app"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert len(data["files"]) > 0
        print(f"\n✅ AI Preview generated {data.get('file_count', len(data['files']))} files")


# ==================== STANDALONE RUNNER ====================

async def run_all_provider_tests():
    """Run all provider tests standalone (without pytest)."""
    print("\n" + "="*60)
    print("🧪 AI PROVIDER API TEST SUITE")
    print("="*60)
    
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Test configurations
    tests = [
        ("Gemini", test_gemini),
        ("Groq", test_groq),
        ("Cerebras", test_cerebras),
        ("OpenRouter", test_openrouter),
    ]
    
    for name, test_func in tests:
        print(f"\n{'─'*40}")
        print(f"Testing {name}...")
        try:
            await test_func()
            results["passed"] += 1
        except Exception as e:
            if "not configured" in str(e).lower() or "skip" in str(e).lower():
                print(f"⏭️  {name}: SKIPPED - {e}")
                results["skipped"] += 1
            else:
                print(f"❌ {name}: FAILED - {e}")
                results["failed"] += 1
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    print(f"✅ Passed:  {results['passed']}")
    print(f"❌ Failed:  {results['failed']}")
    print(f"⏭️  Skipped: {results['skipped']}")
    print("="*60)
    
    return results["failed"] == 0


@pytest.mark.asyncio
async def test_gemini():
    """Standalone Gemini test."""
    from app.ai.providers.gemini import GeminiProvider
    provider = GeminiProvider()
    
    if not provider.is_available():
        raise Exception("Gemini API key not configured")
    
    start = time.time()
    response = await provider.generate(
        prompt="Respond with only: 'Gemini OK'",
        max_tokens=100,  # Gemini 2.5 needs more tokens for thinking
        temperature=0.1
    )
    duration = time.time() - start
    
    if not response:
        raise Exception("No response from Gemini")
    
    print(f"✅ Gemini: {duration:.2f}s - {response.strip()[:50]}")


@pytest.mark.asyncio
async def test_groq():
    """Standalone Groq test."""
    from app.ai.providers.groq import GroqProvider
    provider = GroqProvider()
    
    if not provider.is_available():
        raise Exception("Groq API key not configured")
    
    start = time.time()
    response = await provider.generate(
        prompt="Respond with only: 'Groq OK'",
        max_tokens=20,
        temperature=0.1
    )
    duration = time.time() - start
    
    if not response:
        raise Exception("No response from Groq")
    
    print(f"✅ Groq: {duration:.2f}s - {response.strip()[:50]}")


@pytest.mark.asyncio
async def test_cerebras():
    """Standalone Cerebras test."""
    from app.ai.providers.cerebras import CerebrasProvider
    provider = CerebrasProvider()
    
    if not provider.is_available():
        raise Exception("Cerebras API key not configured")
    
    start = time.time()
    response = await provider.generate(
        prompt="Respond with only: 'Cerebras OK'",
        max_tokens=20,
        temperature=0.1
    )
    duration = time.time() - start
    
    if not response:
        raise Exception("No response from Cerebras")
    
    print(f"✅ Cerebras: {duration:.2f}s - {response.strip()[:50]}")


@pytest.mark.asyncio
async def test_openrouter():
    """Standalone OpenRouter test."""
    from app.ai.providers.openrouter import OpenRouterProvider
    provider = OpenRouterProvider(use_free_only=True)
    
    if not provider.is_available():
        raise Exception("OpenRouter API key not configured")
    
    start = time.time()
    response = await provider.generate(
        prompt="Respond with only: 'OpenRouter OK'",
        max_tokens=20,
        temperature=0.1
    )
    duration = time.time() - start
    
    if not response:
        raise Exception("No response from OpenRouter")
    
    print(f"✅ OpenRouter: {duration:.2f}s - {response.strip()[:50]}")


if __name__ == "__main__":
    # Run standalone tests
    success = asyncio.run(run_all_provider_tests())
    sys.exit(0 if success else 1)
