import asyncio
import json
import sys
import os

# Add backend to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import AsyncMock, MagicMock
from backend.app.ai.agents import AgentOrchestrator, AgentRole, TaskType, AgentContext, AgentMessage
from backend.app.ai.providers.base import AIProvider

async def test_feedback_loop():
    print("Starting Feedback Loop Test...")
    
    # 1. Setup Mock Provider
    broken_code = "def foo() \n    pass"
    fixed_code = "def foo():\n    pass"
    
    mock_provider = AsyncMock(spec=AIProvider)
    mock_provider.is_available.return_value = True
    mock_provider.name = "Mock"
    
    async def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt', '')
        
        if "Fix these code issues" in prompt:
            print("DEBUG: Mock LLM fixing code...")
            return json.dumps({"bad.py": fixed_code})
            
        if "Generate the FastAPI backend" in prompt:
            print("DEBUG: Mock LLM generating backend...")
            return json.dumps({"bad.py": broken_code})
            
        if "Generate the React frontend" in prompt:
            return json.dumps({})
            
        # Default for CORE/ARCH
        return "{}"

    mock_provider.generate.side_effect = mock_generate
    
    providers = {
        TaskType.CODE: mock_provider,
        TaskType.REASONING: mock_provider,
        TaskType.UI_TEXT: mock_provider
    }
    
    orchestrator = AgentOrchestrator(providers)
    
    # 2. Run generate_project
    print("Running orchestrator...")
    final_files = await orchestrator.generate_project({}, "Test")
    
    # 3. Verify Results
    if "bad.py" not in final_files:
        print("❌ bad.py was not generated")
        exit(1)
        
    print(f"Final file content: {repr(final_files['bad.py'])}")
    
    if final_files["bad.py"] == fixed_code:
        print("✅ File was successfully fixed")
    else:
        print("❌ File was NOT fixed")
        exit(1)

    print("Test Passed!")

if __name__ == "__main__":
    asyncio.run(test_feedback_loop())
