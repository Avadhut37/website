import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.ai.engine import AIEngine
from backend.app.ai.providers.gemini import GeminiProvider

async def test_vision_flow():
    print("Starting Vision Flow Test...")
    
    # 1. Setup Mock Provider
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.name = "gemini-1.5-flash"
    mock_gemini.is_available.return_value = True
    
    async def mock_generate(*args, **kwargs):
        prompt = kwargs.get('prompt', '')
        image_data = kwargs.get('image_data')
        
        if image_data:
            print("✅ Image data received by provider")
            if "base64" in image_data:
                print("✅ Image data looks like base64")
            return json.dumps({"main.py": "print('Vision Generated')"})
        else:
            print("❌ No image data received")
            return "{}"

    mock_gemini.generate.side_effect = mock_generate
    
    # 2. Setup Engine
    engine = AIEngine()
    engine.providers = [mock_gemini] # Force use of mock
    
    # Manually init router since it wasn't created in __init__ if no providers were found
    from backend.app.ai.router import ModelRouter
    engine.router = ModelRouter([mock_gemini])
    
    # 3. Test Generate with Image
    print("\nTesting generate_project with image...")
    spec = {"raw": "Make this app"}
    image_data = "data:image/png;base64,fakeimagebytes"
    
    files = await engine.generate_project(spec, "VisionApp", image_data=image_data)
    
    if files.get("main.py") == "print('Vision Generated')":
        print("✅ Generation successful")
    else:
        print("❌ Generation failed")
        
    # 4. Test Edit with Image
    print("\nTesting edit_project with image...")
    current_files = {"main.py": "print('Old')"}
    instruction = "Make it look like this"
    
    files = await engine.edit_project(current_files, instruction, "VisionApp", image_data=image_data)
    
    if files.get("main.py") == "print('Vision Generated')":
        print("✅ Edit successful")
    else:
        print("❌ Edit failed")

if __name__ == "__main__":
    asyncio.run(test_vision_flow())
