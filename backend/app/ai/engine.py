"""AI Engine - Orchestrates code generation using multiple providers."""
import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional

from ..core.config import settings
from ..core.logging import logger
from .providers.base import AIProvider
from .providers.gemini import GeminiProvider
from .providers.groq import GroqProvider
from .providers.cerebras import CerebrasProvider
from .providers.openrouter import OpenRouterProvider
from .prompts import SYSTEM_PROMPT, get_generation_prompt
from .router import ModelRouter
from .agents import AgentOrchestrator, TaskType, create_orchestrator_with_providers


class AIEngine:
    """
    Intelligent AI Engine with multi-provider routing and multi-agent collaboration.
    
    Architecture (Priority Order):
    1. Gemini (PRIMARY) - 1500 free/day, best for UI/text
    2. Groq (CODE) - 14,400 free/day, fastest for code
    3. Cerebras (REASONING) - ~500 free/day, ultra-fast reasoning
    4. OpenRouter (BACKUP) - 50 free/day, multiple models
    5. Template fallback (always works)
    
    Task-Based Model Selection:
    - Code Generation → Groq (LLAMA 3.3 70B, fastest)
    - Reasoning/Planning → Cerebras (Llama 3.1 70B, ultra-fast)
    - UI/Text → Gemini (best quality)
    
    Features:
    - Smart routing (picks best available provider)
    - Multi-agent collaboration (5 specialist agents)
    - Circuit breaker (skips failing providers)
    - Success rate tracking
    - Task-based model selection
    """
    
    def __init__(self):
        self.providers: List[AIProvider] = []
        self.router: Optional[ModelRouter] = None
        self.orchestrator: Optional[AgentOrchestrator] = None
        self.use_agents = settings.DEBUG  # Use agents in dev mode
        self._setup_providers()
    
    def _setup_providers(self):
        """Initialize available providers in priority order."""
        # Gemini - PRIMARY for UI/Text (1500 free/day per key)
        gemini = GeminiProvider()
        if gemini.is_available():
            self.providers.append(gemini)
            logger.info(f"✅ Gemini enabled: {gemini.model} (1500 free/day)")
        
        # Groq - Best for CODE (14,400 free/day, fastest)
        groq = GroqProvider()
        if groq.is_available():
            self.providers.append(groq)
            logger.info(f"✅ Groq enabled: {groq.model} (14,400 free/day)")
        
        # Cerebras - Best for REASONING (~500 free/day, ultra-fast)
        cerebras = CerebrasProvider()
        if cerebras.is_available():
            self.providers.append(cerebras)
            logger.info(f"✅ Cerebras enabled: {cerebras.model} (reasoning specialist)")
        
        # OpenRouter - BACKUP (multiple models, 50 free/day)
        openrouter = OpenRouterProvider(
            use_free_only=True  # Use free models
        )
        if openrouter.is_available():
            self.providers.append(openrouter)
            logger.info(f"✅ OpenRouter enabled: {openrouter.model} (50 free/day)")
        
        if not self.providers:
            logger.warning("⚠️  No AI providers available - will use template fallback")
        else:
            # Initialize intelligent router
            self.router = ModelRouter(self.providers)
            # Initialize multi-agent orchestrator with task-based providers
            self.orchestrator = create_orchestrator_with_providers(self.providers)
            logger.info(f"🚀 AI Engine ready: {len(self.providers)} providers available")
    
    async def generate_project(
        self,
        spec: Dict[str, Any],
        project_name: str,
    ) -> Dict[str, str]:
        """
        Generate a complete project based on the specification.
        
        Uses intelligent routing and optional multi-agent collaboration.
        
        Args:
            spec: Project specification (parsed from user input)
            project_name: Name of the project
            
        Returns:
            Dictionary mapping file paths to file contents
        """
        # Use multi-agent collaboration if enabled and orchestrator available
        if self.use_agents and self.orchestrator:
            try:
                logger.info("🤖 Using multi-agent collaboration mode (5 agents)")
                files = await self.orchestrator.generate_project(spec, project_name)
                if files and len(files) > 0:
                    logger.info(f"✅ Multi-agent generated {len(files)} files")
                    return files
            except Exception as e:
                logger.error(f"❌ Multi-agent failed: {e}, falling back to single model")
        
        # Standard generation with intelligent routing
        if not self.router or not self.providers:
            logger.info("Using template fallback generation (no providers)")
            return self._generate_fallback(spec, project_name)
        
        prompt = get_generation_prompt(spec, project_name)
        
        # Try providers in order of priority/success rate
        max_attempts = min(3, len(self.providers))
        
        for attempt in range(max_attempts):
            provider, reason = self.router.select_provider()
            
            if not provider:
                break
            
            try:
                start_time = time.time()
                logger.info(f"🔄 Attempt {attempt + 1}: Using {provider.name}")
                
                response = provider.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    max_tokens=settings.LLM_MAX_TOKENS,
                    temperature=0.3,  # Lower for more deterministic code
                )
                
                if response:
                    files = self._parse_response(response)
                    if files and len(files) > 0:
                        duration = time.time() - start_time
                        self.router.record_success(provider.name, duration)
                        logger.info(f"✅ Generated {len(files)} files with {provider.name} in {duration:.2f}s")
                        return files
                    else:
                        raise ValueError("No valid files parsed from response")
                    
            except Exception as e:
                self.router.record_failure(provider.name, str(e))
                logger.error(f"❌ Provider {provider.name} failed: {e}")
                continue
        
        # Fallback to template generation
        logger.info("📝 Using template fallback generation")
        return self._generate_fallback(spec, project_name)
    
    def _parse_response(self, response: str) -> Optional[Dict[str, str]]:
        """Parse AI response to extract file contents."""
        # Try direct JSON parse
        try:
            files = json.loads(response)
            if isinstance(files, dict):
                return files
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response)
            for match in matches:
                try:
                    data = json.loads(match if isinstance(match, str) else match)
                    if isinstance(data, dict) and len(data) > 0:
                        # Validate it looks like file paths
                        if any('/' in k or '.' in k for k in data.keys()):
                            return data
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _generate_fallback(
        self,
        spec: Dict[str, Any],
        project_name: str
    ) -> Dict[str, str]:
        """Generate a template project when AI is unavailable."""
        app_desc = spec.get("raw", spec.get("description", project_name))
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name.lower())
        
        return {
            "README.md": f"""# {project_name}

{app_desc}

## Project Structure

```
├── backend/           # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── frontend/          # React frontend
│   ├── src/
│   ├── package.json
│   └── ...
└── README.md
```

## Getting Started

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\\Scripts\\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
""",
            "backend/main.py": f'''"""FastAPI backend for {project_name}."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(
    title="{project_name}",
    description="{app_desc}",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ Models ============

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ In-Memory Storage ============

items_db: List[dict] = []
item_counter = 0

# ============ Endpoints ============

@app.get("/")
def root():
    return {{"message": "Welcome to {project_name}", "docs": "/docs"}}

@app.get("/health")
def health():
    return {{"status": "ok"}}

@app.get("/items", response_model=List[Item])
def list_items():
    return items_db

@app.post("/items", response_model=Item)
def create_item(item: ItemCreate):
    global item_counter
    item_counter += 1
    new_item = {{
        "id": item_counter,
        "title": item.title,
        "description": item.description,
        "created_at": datetime.utcnow()
    }}
    items_db.append(new_item)
    return new_item

@app.get("/items/{{item_id}}", response_model=Item)
def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{{item_id}}")
def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return {{"message": "Item deleted"}}
    raise HTTPException(status_code=404, detail="Item not found")
''',
            "backend/requirements.txt": """fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.0.0
python-multipart>=0.0.9
""",
            "frontend/package.json": json.dumps({
                "name": safe_name,
                "version": "1.0.0",
                "type": "module",
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                    "preview": "vite preview"
                },
                "dependencies": {
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "axios": "^1.6.0"
                },
                "devDependencies": {
                    "vite": "^5.0.0",
                    "@vitejs/plugin-react": "^4.2.0"
                }
            }, indent=2),
            "frontend/index.html": f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{project_name}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; background: #f5f5f5; }}
  </style>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
''',
            "frontend/vite.config.js": '''import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\\/api/, '')
      }
    }
  }
});
''',
            "frontend/src/main.jsx": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
''',
            "frontend/src/App.jsx": f'''import React, {{ useState, useEffect }} from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

export default function App() {{
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    fetchItems();
  }}, []);

  const fetchItems = async () => {{
    try {{
      const res = await axios.get(`${{API_URL}}/items`);
      setItems(res.data);
    }} catch (err) {{
      console.error('Error fetching items:', err);
    }} finally {{
      setLoading(false);
    }}
  }};

  const addItem = async (e) => {{
    e.preventDefault();
    if (!title.trim()) return;
    
    try {{
      await axios.post(`${{API_URL}}/items`, {{ title, description }});
      setTitle('');
      setDescription('');
      fetchItems();
    }} catch (err) {{
      console.error('Error adding item:', err);
    }}
  }};

  const deleteItem = async (id) => {{
    try {{
      await axios.delete(`${{API_URL}}/items/${{id}}`);
      fetchItems();
    }} catch (err) {{
      console.error('Error deleting item:', err);
    }}
  }};

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '1.5rem', color: '#333' }}>{project_name}</h1>
      
      <form onSubmit={{addItem}} style={{ marginBottom: '2rem', padding: '1rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <input
          type="text"
          value={{title}}
          onChange={{(e) => setTitle(e.target.value)}}
          placeholder="Title"
          style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
        />
        <input
          type="text"
          value={{description}}
          onChange={{(e) => setDescription(e.target.value)}}
          placeholder="Description (optional)"
          style={{ width: '100%', padding: '0.5rem', marginBottom: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
        />
        <button type="submit" style={{ padding: '0.5rem 1rem', background: '#0070f3', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
          Add Item
        </button>
      </form>

      {{loading ? (
        <p>Loading...</p>
      ) : items.length === 0 ? (
        <p style={{ color: '#666' }}>No items yet. Add one above!</p>
      ) : (
        <ul style={{ listStyle: 'none' }}>
          {{items.map(item => (
            <li key={{item.id}} style={{ padding: '1rem', marginBottom: '0.5rem', background: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>{{item.title}}</strong>
                {{item.description && <p style={{ color: '#666', fontSize: '0.9rem' }}>{{item.description}}</p>}}
              </div>
              <button onClick={{() => deleteItem(item.id)}} style={{ padding: '0.25rem 0.5rem', background: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
                Delete
              </button>
            </li>
          ))}}
        </ul>
      )}}
    </div>
  );
}}
''',
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI engine status with provider statistics."""
        status = {
            "providers": [p.get_model_info() for p in self.providers],
            "provider_count": len(self.providers),
            "available": len(self.providers) > 0,
            "fallback_enabled": True,
            "multi_agent_enabled": self.use_agents,
            "task_routing": {
                "code": "Groq (LLAMA 3.3 70B)" if any("groq" in p.name.lower() for p in self.providers) else "Best available",
                "reasoning": "Cerebras (Llama 3.1 70B)" if any("cerebras" in p.name.lower() for p in self.providers) else "Best available",
                "ui_text": "Gemini (gemini-2.0-flash)" if any("gemini" in p.name.lower() for p in self.providers) else "Best available"
            }
        }
        
        # Add router statistics if available
        if self.router:
            status["statistics"] = self.router.get_stats()
        
        return status


# Singleton instance
_engine: Optional[AIEngine] = None


def get_ai_engine() -> AIEngine:
    """Get or create the AI engine singleton."""
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine


# Sync wrapper for backward compatibility
def call_llm_and_generate(spec: dict) -> Dict[str, str]:
    """Synchronous wrapper for project generation."""
    engine = get_ai_engine()
    project_name = spec.get("name", spec.get("raw", "GeneratedApp"))
    if isinstance(project_name, str) and len(project_name) > 50:
        project_name = project_name[:50]
    
    # Run async generation in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(engine.generate_project(spec, project_name))
    finally:
        loop.close()
