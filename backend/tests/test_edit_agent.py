import asyncio
import json
import sys
import os

# Add backend to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import AsyncMock
from backend.app.ai.agents import AgentOrchestrator, AgentRole, TaskType, AgentContext
from backend.app.ai.providers.base import AIProvider

async def test_edit_agent():
    print("Starting Edit Agent Test...")
    
    # 1. Setup Mock Provider
    original_code = "def hello():\n    print('Hello')"
    modified_code = "def hello():\n    print('Hello World')"
    
    mock_provider = AsyncMock(spec=AIProvider)
    mock_provider.is_available.return_value = True
    mock_provider.name = "Mock"
    
    async def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt', '')
        
        if "Apply this modification" in prompt:
            print("DEBUG: Mock LLM applying edit...")
            return json.dumps({"main.py": modified_code})
            
        if "Fix these code issues" in prompt:
            print("DEBUG: Mock LLM checking for errors...")
            return json.dumps({}) # No errors
            
        return "{}"

    mock_provider.generate.side_effect = mock_generate
    
    providers = {
        TaskType.CODE: mock_provider,
        TaskType.REASONING: mock_provider,
        TaskType.UI_TEXT: mock_provider
    }
    
    orchestrator = AgentOrchestrator(providers)
    
    # 2. Run edit_project
    print("Running orchestrator.edit_project...")
    current_files = {"main.py": original_code}
    instruction = "Change Hello to Hello World"
    
    final_files = await orchestrator.edit_project(current_files, instruction, "TestEdit")
    
    # 3. Verify Results
    print(f"Final file content: {repr(final_files.get('main.py'))}")
    
    if final_files.get("main.py") == modified_code:
        print("✅ Edit was successfully applied")
    else:
        print("❌ Edit was NOT applied")
        exit(1)

    print("Test Passed!")

if __name__ == "__main__":
    asyncio.run(test_edit_agent())
