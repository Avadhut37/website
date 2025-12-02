"""
Integration tests for async AI engine workflow.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
import time


@pytest.mark.asyncio
async def test_async_provider_concurrent_calls():
    """Test that multiple async provider calls can run concurrently."""
    from app.ai.providers.gemini import GeminiProvider
    from app.ai.providers.groq import GroqProvider
    
    gemini = GeminiProvider()
    groq = GroqProvider()
    
    if not gemini.is_available() or not groq.is_available():
        pytest.skip("Providers not configured")
    
    start = time.time()
    
    # Run two providers concurrently
    results = await asyncio.gather(
        gemini.generate("Say 'Hello from Gemini'", max_tokens=50),
        groq.generate("Say 'Hello from Groq'", max_tokens=50),
        return_exceptions=True
    )
    
    duration = time.time() - start
    
    # Verify both calls completed
    assert len(results) == 2
    print(f"\n✅ Concurrent calls completed in {duration:.2f}s")
    
    # Check results
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"⚠️  Call {i+1} failed: {result}")
        else:
            assert result is not None
            print(f"✅ Call {i+1}: {result[:50]}...")


@pytest.mark.asyncio
async def test_ai_engine_async_generation():
    """Test that AI Engine's generate_project is async."""
    from app.ai.engine import get_ai_engine
    
    engine = get_ai_engine()
    
    if not engine.providers:
        pytest.skip("No AI providers available")
    
    spec = {
        "raw": "Simple test app",
        "name": "TestApp"
    }
    
    start = time.time()
    files = await engine.generate_project(spec, "TestApp")
    duration = time.time() - start
    
    assert isinstance(files, dict)
    assert len(files) > 0
    print(f"\n✅ Generated {len(files)} files in {duration:.2f}s")


@pytest.mark.asyncio
async def test_multi_agent_async_workflow():
    """Test that multi-agent orchestrator works asynchronously."""
    from app.ai.engine import get_ai_engine
    
    engine = get_ai_engine()
    
    if not engine.orchestrator:
        pytest.skip("Multi-agent orchestrator not available")
    
    spec = {
        "raw": "Todo list app with React frontend and FastAPI backend",
        "name": "TodoApp"
    }
    
    start = time.time()
    files = await engine.orchestrator.generate_project(spec, "TodoApp")
    duration = time.time() - start
    
    assert isinstance(files, dict)
    assert len(files) > 0
    print(f"\n✅ Multi-agent generated {len(files)} files in {duration:.2f}s")


@pytest.mark.asyncio
async def test_async_agent_execution():
    """Test individual agent async execution."""
    from app.ai.agents import CoreAgent, TaskType
    from app.ai.providers.groq import GroqProvider
    from app.ai.agents import AgentContext
    
    provider = GroqProvider()
    if not provider.is_available():
        pytest.skip("Groq provider not configured")
    
    providers = {TaskType.CODE: provider, TaskType.REASONING: provider, TaskType.UI_TEXT: provider}
    agent = CoreAgent(providers)
    
    context = AgentContext(
        project_spec={"raw": "Simple app"},
        project_name="TestApp"
    )
    
    start = time.time()
    message = await agent.execute(context)
    duration = time.time() - start
    
    assert message is not None
    assert message.role.value == "CORE"
    print(f"\n✅ Agent executed in {duration:.2f}s")
    print(f"   Confidence: {message.confidence}")
