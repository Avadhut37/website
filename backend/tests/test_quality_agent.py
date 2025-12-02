import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.ai.agents import AgentOrchestrator, AgentRole, TaskType, AgentContext
from backend.app.ai.providers.base import AIProvider

async def test_quality_and_test_agents():
    print("Starting Quality & Test Agent Verification...")
    
    # Mock Provider
    mock_provider = AsyncMock(spec=AIProvider)
    mock_provider.is_available.return_value = True
    mock_provider.name = "Mock"
    
    # Scenario:
    # 1. Backend generates code with a secret
    # 2. Quality Agent fixes it
    # 3. Test Agent generates tests
    
    unsafe_code = 'API_KEY = "12345"'
    safe_code = 'API_KEY = os.getenv("API_KEY")'
    test_code = 'def test_api(): assert True'
    
    async def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt', '')
        
        # CORE/ARCH/BACKEND/UIX/DEBUG responses
        if "Analyze this app request" in prompt:
            return json.dumps({"analysis": "plan"})
        if "Design the architecture" in prompt:
            return json.dumps({"files": {"main.py": "..."}})
        if "Generate the FastAPI backend" in prompt:
            return json.dumps({"backend/main.py": unsafe_code})
        if "Generate the React frontend" in prompt:
            return json.dumps({"frontend/App.jsx": "// frontend"})
        if "Fix these code issues" in prompt:
            return json.dumps({}) # Debug agent finds nothing
            
        # QUALITY Agent Response
        if "Review and fix quality/security issues" in prompt:
            print("DEBUG: Quality Agent invoked")
            return json.dumps({"backend/main.py": safe_code})
            
        # TEST Agent Response
        if "Generate unit tests" in prompt:
            print("DEBUG: Test Agent invoked")
            return json.dumps({"backend/tests/test_main.py": test_code})
            
        return "{}"

    mock_provider.generate.side_effect = mock_generate
    
    providers = {
        TaskType.CODE: mock_provider,
        TaskType.REASONING: mock_provider,
        TaskType.UI_TEXT: mock_provider
    }
    
    orchestrator = AgentOrchestrator(providers)
    
    # Run generation
    print("Running orchestrator...")
    final_files = await orchestrator.generate_project({"raw": "Secure App"}, "SecureApp")
    
    # Verify Quality Agent
    if final_files.get("backend/main.py") == safe_code:
        print("✅ Quality Agent fixed the code")
    else:
        print(f"❌ Quality Agent failed. Content: {final_files.get('backend/main.py')}")
        exit(1)
        
    # Verify Test Agent
    if "backend/tests/test_main.py" in final_files:
        print("✅ Test Agent generated tests")
    else:
        print("❌ Test Agent failed to generate tests")
        exit(1)
        
    print("All checks passed!")

if __name__ == "__main__":
    asyncio.run(test_quality_and_test_agents())
