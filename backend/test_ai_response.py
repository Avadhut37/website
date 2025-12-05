"""Test AI response parsing"""
import asyncio
import json
from app.ai.engine import AIEngine
from app.core.config import settings

async def test_generation():
    engine = AIEngine()
    
    spec = {
        "raw": "Build a simple todo app with add, edit, delete features",
        "name": "TodoApp"
    }
    
    print("🧪 Testing AI Generation...")
    print(f"Spec: {spec['raw']}\n")
    
    try:
        files = await engine.generate_project(spec, "TodoApp")
        
        print(f"\n✅ Generated {len(files)} files:")
        for path in files.keys():
            print(f"  📄 {path}")
        
        # Show a sample file
        if "frontend/src/App.jsx" in files:
            print(f"\n📝 Sample: frontend/src/App.jsx (first 500 chars)")
            print(files["frontend/src/App.jsx"][:500])
            print("...")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generation())
