"""
Professional Multi-Agent System for App Generation.

Architecture (per blueprint):
- CORE: Orchestrator - decides which agents to activate
- ARCH: Architecture & planning specialist  
- BACKEND: FastAPI/Python specialist
- UIX: Frontend/React specialist
- DEBUG: Error fixing & code optimization

Task-Based Model Selection:
- Code Generation → Groq (LLAMA 3.3 70B, fastest)
- Reasoning/Planning → DeepSeek (R1 671B, ultra-fast reasoning)
- UI/Text → Gemini (best quality)
"""
import asyncio
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import settings
from ..core.logging import logger
from ..schemas import ProjectManifest, create_default_manifest, validate_manifest, AppType
from ..services.ast_patcher import generate_patch, apply_patch
from ..services.validation import get_validation_service
from ..services.memory import get_project_memory
from .providers.base import AIProvider
from pydantic import ValidationError


class AgentRole(str, Enum):
    """Agent roles per blueprint specification."""
    CORE = "CORE"      # Orchestrator
    ARCH = "ARCH"      # Architecture specialist
    BACKEND = "BACKEND"  # Backend specialist
    UIX = "UIX"        # Frontend specialist  
    DEBUG = "DEBUG"    # Error fixing specialist
    EDIT = "EDIT"      # Iterative refinement specialist
    QUALITY = "QUALITY" # Code quality & security specialist
    TEST = "TEST"      # Test generation specialist


class TaskType(str, Enum):
    """Task types for model selection."""
    CODE = "code"           # → Groq
    REASONING = "reasoning"  # → DeepSeek
    UI_TEXT = "ui_text"     # → Gemini


@dataclass
class AgentMessage:
    """Message from an agent."""
    role: AgentRole
    content: str
    artifacts: Dict[str, str] = field(default_factory=dict)  # filename -> content
    reasoning: str = ""
    confidence: float = 0.0


@dataclass  
class AgentContext:
    """Shared context between agents."""
    project_spec: Dict[str, Any]
    project_name: str
    project_id: Optional[int] = None
    image_data: Optional[str] = None
    messages: List[AgentMessage] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    iteration: int = 0


class BaseAgent:
    """Base class for all agents."""
    
    ROLE: AgentRole = AgentRole.CORE
    TASK_TYPE: TaskType = TaskType.REASONING
    
    # Agent-specific prompts
    SYSTEM_PROMPT: str = ""
    
    def __init__(self, providers: Dict[TaskType, AIProvider]):
        self.providers = providers
        self._provider: Optional[AIProvider] = None
    
    @property
    def provider(self) -> Optional[AIProvider]:
        """Get the appropriate provider for this agent's task type."""
        if self._provider is None:
            self._provider = self.providers.get(self.TASK_TYPE)
            if not self._provider:
                # Fallback to any available provider
                for p in self.providers.values():
                    if p and p.is_available():
                        self._provider = p
                        break
        return self._provider
    
    def format_output(self, content: str, artifacts: Dict[str, str] = None) -> str:
        """Format agent output per blueprint spec."""
        output = f"[AGENT: {self.ROLE.value}]\n{content}"
        if artifacts:
            output += f"\n[ARTIFACTS: {len(artifacts)} files]"
        return output
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Execute agent logic. Override in subclasses."""
        raise NotImplementedError
    
    async def _call_llm(self, prompt: str, max_tokens: int = 4096, **kwargs) -> Optional[str]:
        """Call the LLM with the prompt."""
        if not self.provider:
            logger.warning(f"[{self.ROLE}] No provider available")
            return None
        
        try:
            return await self.provider.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=max_tokens,
                temperature=0.3,
                **kwargs
            )
        except Exception as e:
            logger.error(f"[{self.ROLE}] LLM call failed: {e}")
            return None
    
    def _fix_json_string(self, json_str: str) -> str:
        """
        Fix common JSON formatting issues from LLM responses.
        
        LLMs often return JSON with unescaped newlines, quotes, and control characters.
        """
        result = []
        in_string = False
        escape_next = False
        
        for char in json_str:
            if escape_next:
                result.append(char)
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                result.append(char)
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                result.append(char)
                continue
            
            if in_string:
                if char == '\n':
                    result.append('\\n')
                elif char == '\r':
                    result.append('\\r')
                elif char == '\t':
                    result.append('\\t')
                elif ord(char) < 32:  # Other control characters
                    result.append(f'\\u{ord(char):04x}')
                else:
                    result.append(char)
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _extract_file_blocks(self, response: str) -> Dict[str, str]:
        """
        Alternative extraction: Find file blocks marked with filename patterns.
        
        Handles responses like:
        ```backend/main.py
        code here
        ```
        """
        files = {}
        
        # Pattern for markdown code blocks with filenames
        block_pattern = r'```(?:python|javascript|jsx|json|html|txt|md)?\s*\n?([a-zA-Z0-9_/.-]+\.[a-z]+)\s*\n([\s\S]*?)```'
        
        for match in re.finditer(block_pattern, response):
            filename = match.group(1).strip()
            content = match.group(2).strip()
            if filename and content:
                files[filename] = content
        
        # Also try pattern: "filename.ext": "content" or filename.ext:\n```\ncontent\n```
        if not files:
            alt_pattern = r'["\']?([a-zA-Z_/]+(?:/[a-zA-Z_]+)*\.[a-z]+)["\']?\s*[:=]\s*["\']?\n?```[^\n]*\n([\s\S]*?)```'
            for match in re.finditer(alt_pattern, response):
                filename = match.group(1).strip().strip('"\'')
                content = match.group(2).strip()
                if filename and content:
                    files[filename] = content
        
        return files
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, str]]:
        """Parse JSON from LLM response, handling common formatting issues."""
        if not response:
            return None
        
        # Method 1: Try to find and parse JSON directly
        try:
            # Remove markdown code block wrapper if present
            clean_response = response
            if '```json' in response:
                json_block = re.search(r'```json\s*([\s\S]*?)\s*```', response)
                if json_block:
                    clean_response = json_block.group(1)
            elif '```' in response and '{' in response:
                # Generic code block
                json_block = re.search(r'```\s*([\s\S]*?)\s*```', response)
                if json_block and '{' in json_block.group(1):
                    clean_response = json_block.group(1)
            
            # Find JSON object
            json_match = re.search(r'\{[\s\S]*\}', clean_response)
            if not json_match:
                # Try alternative extraction
                return self._extract_file_blocks(response) or None
            
            json_str = json_match.group()
            
            # Try direct parse first
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try fixing common issues
                fixed_json = self._fix_json_string(json_str)
                data = json.loads(fixed_json)
            
            if isinstance(data, dict):
                # Filter to only string values (file contents)
                result = {k: v for k, v in data.items() if isinstance(v, str)}
                if result:
                    return result
            
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"[{self.ROLE}] JSON parse failed: {e}")
        
        # Method 2: Try alternative extraction from code blocks
        alt_files = self._extract_file_blocks(response)
        if alt_files:
            logger.info(f"[{self.ROLE}] Extracted {len(alt_files)} files from code blocks")
            return alt_files
        
        return None


class CoreAgent(BaseAgent):
    """
    CORE Agent - The Orchestrator with strict manifest output.
    
    Responsibilities:
    - Analyze user request
    - Create structured ProjectManifest
    - Decide which agents to activate
    - Coordinate agent collaboration
    """
    
    ROLE = AgentRole.CORE
    TASK_TYPE = TaskType.REASONING  # Will use DeepSeek for deep analysis
    
    SYSTEM_PROMPT = """You are CORE, the Lead Product Manager & Orchestrator.

Your Goal: Create a PRECISE, STRUCTURED project manifest that drives all downstream generation.

OUTPUT FORMAT (STRICT JSON ONLY):
- Respond with a single JSON object that matches this schema.
- Do not wrap it in markdown code fences.
- Do not add explanations before or after.

Manifest schema (keys and value types):
{
    "analysis": "string (2-3 sentence summary)",
    "app_type": "one of: crud | ecommerce | dashboard | social | todo | blog | auth | booking | api",
    "features": ["string", ...],
    "tech_stack": {
        "backend": "FastAPI + Pydantic",
        "frontend": "React 18 + Vite",
        "styling": "Tailwind CSS"
    },
    "models": [
        {
            "name": "string",
            "fields": {"field_name": "type"},
            "relationships": ["optional relationship description"]
        }
    ],
    "endpoints": [
        {
            "path": "string, e.g. /api/items",
            "method": "GET" | "POST" | "PUT" | "DELETE" | "PATCH",
            "description": "string",
            "request_model": "string or null",
            "response_model": "string"
        }
    ],
    "files_to_generate": [
        {
            "path": "string, e.g. backend/main.py",
            "description": "string",
            "dependencies": ["optional list of related files"]
        }
    ],
    "integrations": ["string"],
    "agents_needed": [
        "ARCH" | "BACKEND" | "UIX" | "DEBUG" | "QUALITY" | "TEST"
    ],
    "priority": "short string describing what to build first"
}

CRITICAL RULES:
- "agents_needed" MUST be an array containing only these values: ARCH, BACKEND, UIX, DEBUG, QUALITY, TEST.
- "response_model" fields MUST always be non-null strings.
- All paths MUST be valid URL paths (start with "/").
- Output ONLY valid JSON, with no comments and no markdown."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Analyze request and create strict manifest with memory context."""
        spec = context.project_spec
        raw_desc = spec.get("raw", spec.get("description", ""))
        
        # Get memory context if project_id available
        memory_context = ""
        if context.project_id:
            try:
                memory = get_project_memory(context.project_id)
                mem_data = memory.get_context_for_generation(raw_desc, max_results=5)
                
                # Build context string
                if mem_data.get("preferences"):
                    memory_context += "\n\n[PROJECT PREFERENCES]\n"
                    for key, value in mem_data["preferences"].items():
                        memory_context += f"  • {key}: {value}\n"
                
                if mem_data.get("constraints"):
                    memory_context += "\n[CONSTRAINTS (MUST)]\n"
                    for constraint in mem_data["constraints"][:5]:
                        memory_context += f"  • {constraint}\n"
                
                if mem_data.get("suggestions"):
                    memory_context += "\n[SUGGESTIONS (SHOULD)]\n"
                    for suggestion in mem_data["suggestions"][:3]:
                        memory_context += f"  • {suggestion}\n"
                
                if mem_data.get("past_decisions"):
                    memory_context += "\n[PAST DECISIONS]\n"
                    for decision in mem_data["past_decisions"][:3]:
                        memory_context += f"  • {decision.get('metadata', {}).get('decision', '')}\n"
                
                if memory_context:
                    logger.info(f"[CORE] Using memory context ({len(memory_context)} chars)")
            except Exception as e:
                logger.warning(f"[CORE] Failed to load memory context: {e}")
        
        prompt = f"""Analyze this app request and create a STRUCTURED PROJECT MANIFEST:

PROJECT: {context.project_name}
DESCRIPTION: {raw_desc}

SPEC DETAILS:
{json.dumps(spec, indent=2, default=str)}{memory_context}

Create a complete project manifest following the exact JSON schema.
Identify:
1. App type (choose ONE: crud, ecommerce, dashboard, social, todo, blog, auth, booking, api)
2. Core features (minimum 3, maximum 10)
3. Data models needed (with fields and types)
4. API endpoints (full CRUD for each model)
5. All files to generate (include ALL standard files)
6. Which specialist agents to activate

IMPORTANT: Respect all preferences and constraints from project memory above.

Return ONLY the JSON manifest."""

        if context.image_data:
            prompt += "\n\n[IMAGE CONTEXT] UI design image provided - analyze visual structure."

        response = await self._call_llm(prompt)
        
        if not response:
            # Use fallback manifest
            fallback = create_default_manifest(context.project_name, raw_desc)
            logger.warning("[CORE] Using fallback manifest (no LLM response)")
            return AgentMessage(
                role=self.ROLE,
                content=fallback.model_dump_json(indent=2),
                reasoning="Default manifest (no LLM)",
                confidence=0.5,
                artifacts={}
            )
        
        # Parse and validate manifest
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            plan_dict = json.loads(json_match.group())
            
            # Validate with Pydantic
            manifest = validate_manifest(plan_dict)
            
            logger.info(f"[CORE] ✅ Valid manifest created: {manifest.app_type}")
            logger.info(f"[CORE] Features: {', '.join(manifest.features[:3])}...")
            logger.info(f"[CORE] Models: {len(manifest.models)}, Endpoints: {len(manifest.endpoints)}")
            
            return AgentMessage(
                role=self.ROLE,
                content=manifest.model_dump_json(indent=2),
                reasoning=manifest.analysis,
                confidence=0.95,
                artifacts={}
            )
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"[CORE] ❌ Invalid manifest: {e}")
            
            # Try to recover with fallback
            fallback = create_default_manifest(context.project_name, raw_desc)
            logger.warning("[CORE] Using fallback manifest (validation failed)")
            
            return AgentMessage(
                role=self.ROLE,
                content=fallback.model_dump_json(indent=2),
                reasoning=f"Fallback manifest (error: {str(e)[:100]})",
                confidence=0.6,
                artifacts={}
            )


class ArchAgent(BaseAgent):
    """
    ARCH Agent - Architecture Specialist.
    
    Responsibilities:
    - Design system architecture
    - Define API contracts
    - Create data models
    - Plan file structure
    """
    
    ROLE = AgentRole.ARCH
    TASK_TYPE = TaskType.REASONING
    
    SYSTEM_PROMPT = """You are ARCH, the Systems Architect.

Your Goal: Design a scalable, maintainable, and clean architecture for a World-Class Application.

Responsibilities:
1. Structure: Define a folder structure that separates concerns (routes, controllers, services, models).
2. API Contract: Define clear, consistent RESTful API endpoints.
3. Data Modeling: Design efficient data models with proper relationships.
4. Scalability: Plan for future growth (modular design).

Tech Stack:
- Backend: FastAPI, Pydantic, SQLModel
- Frontend: React, Vite, Tailwind CSS
- API: RESTful JSON

Output Format:
- Start with [AGENT: ARCH]
- Provide architecture decisions
- Output JSON for API specs and data models

Focus on simplicity, best practices, and long-term maintainability."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Design the architecture."""
        spec = context.project_spec
        
        # Get plan from CORE agent if available
        core_plan = ""
        for msg in context.messages:
            if msg.role == AgentRole.CORE:
                core_plan = msg.content
                break
        
        prompt = f"""Design the architecture for this app:

PROJECT: {context.project_name}
SPEC: {json.dumps(spec, indent=2, default=str)}

CORE AGENT PLAN:
{core_plan}

Create:
1. API endpoints (path, method, request/response)
2. Data models (fields, types, relationships)
3. File structure with descriptions

Output JSON:
{{
    "endpoints": [
        {{"path": "/items", "method": "GET", "description": "List all items", "response": "List[Item]"}},
        {{"path": "/items", "method": "POST", "description": "Create item", "request": "ItemCreate", "response": "Item"}}
    ],
    "models": [
        {{"name": "Item", "fields": {{"id": "int", "title": "str", "created_at": "datetime"}}}}
    ],
    "files": {{
        "backend/main.py": "FastAPI app with endpoints",
        "backend/models.py": "Pydantic/SQLModel models",
        "frontend/src/App.jsx": "Main React component"
    }}
}}"""

        response = await self._call_llm(prompt)
        
        if response:
            try:
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    arch = json.loads(json_match.group())
                    return AgentMessage(
                        role=self.ROLE,
                        content=json.dumps(arch, indent=2),
                        reasoning="Architecture designed",
                        confidence=0.9,
                        artifacts={}
                    )
            except json.JSONDecodeError:
                pass
        
        return AgentMessage(
            role=self.ROLE,
            content=response or "Using default architecture",
            reasoning="Architecture analysis complete",
            confidence=0.7,
            artifacts={}
        )


class BackendAgent(BaseAgent):
    """
    BACKEND Agent - FastAPI/Python Specialist.
    
    Responsibilities:
    - Generate FastAPI backend code
    - Create Pydantic models
    - Implement API endpoints
    - Handle data storage
    """
    
    ROLE = AgentRole.BACKEND
    TASK_TYPE = TaskType.CODE  # Uses Groq for fast code generation
    
    SYSTEM_PROMPT = """You are BACKEND, the Senior Python Architect.

Your Goal: Build a robust, secure, and scalable API backend.

Responsibilities:
1. API Design: Follow RESTful best practices.
   - Use proper HTTP methods and status codes (201 Created, 404 Not Found, etc.).
   - Standardize error responses.
2. Code Quality:
   - Type hints (mypy strict) are mandatory.
   - Use Pydantic for rigorous data validation.
   - Implement Dependency Injection where appropriate.
3. Functionality:
   - Full CRUD operations.
   - In-memory persistence (simulated DB) that is thread-safe if possible.
   - CORS configuration for frontend integration.
   - Health check endpoint.

Tech Stack:
- FastAPI
- Pydantic V2
- Python 3.11+

Output Format:
- Start with [AGENT: BACKEND]
- Output complete, runnable Python code
- Use JSON format: {"filename": "code content"}

Write code that you would be proud to ship to production."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Generate backend code."""
        spec = context.project_spec
        
        # Get architecture from ARCH agent
        arch_spec = ""
        for msg in context.messages:
            if msg.role == AgentRole.ARCH:
                arch_spec = msg.content
                break
        
        prompt = f"""Generate the FastAPI backend for this app:

PROJECT: {context.project_name}
SPEC: {json.dumps(spec, indent=2, default=str)}

ARCHITECTURE:
{arch_spec}

Generate these files as JSON (filename -> complete code):
1. backend/main.py - FastAPI app with all endpoints
2. backend/requirements.txt - Dependencies

Requirements:
- FastAPI with CORS middleware
- Pydantic models for request/response
- In-memory storage (list/dict)
- Full CRUD operations
- Health check endpoint
- Proper error handling

Output format:
{{
    "backend/main.py": "complete python code here",
    "backend/requirements.txt": "dependencies here"
}}"""

        response = await self._call_llm(prompt, max_tokens=8192)
        
        # Parse JSON response using base class method
        artifacts = self._parse_json_response(response)
        
        if artifacts:
            logger.info(f"[BACKEND] Parsed {len(artifacts)} files from LLM")
        else:
            logger.warning("[BACKEND] Using fallback backend generation")
            artifacts = self._generate_fallback_backend(context)
        
        return AgentMessage(
            role=self.ROLE,
            content=f"Generated {len(artifacts)} backend files",
            reasoning="Backend code generated",
            confidence=0.9 if len(artifacts) >= 2 else 0.6,
            artifacts=artifacts
        )
    
    def _generate_fallback_backend(self, context: AgentContext) -> Dict[str, str]:
        """Generate fallback backend code."""
        name = context.project_name
        return {
            "backend/main.py": f'''"""FastAPI backend for {name}."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="{name}", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    created_at: datetime

items_db: List[dict] = []
counter = 0

@app.get("/")
def root():
    return {{"message": "Welcome to {name}", "docs": "/docs"}}

@app.get("/health")
def health():
    return {{"status": "ok"}}

@app.get("/items", response_model=List[Item])
def list_items():
    return items_db

@app.post("/items", response_model=Item)
def create_item(item: ItemCreate):
    global counter
    counter += 1
    new_item = {{"id": counter, "title": item.title, "description": item.description, "created_at": datetime.utcnow()}}
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
    global items_db
    items_db = [i for i in items_db if i["id"] != item_id]
    return {{"message": "Deleted"}}
''',
            "backend/requirements.txt": """fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.0.0
"""
        }


class UIXAgent(BaseAgent):
    """
    UIX Agent - Frontend/React Specialist.
    
    Responsibilities:
    - Generate React components
    - Create responsive UI with Tailwind
    - Handle state management
    - API integration
    """
    
    ROLE = AgentRole.UIX
    TASK_TYPE = TaskType.UI_TEXT  # Uses Gemini for quality UI code
    
    SYSTEM_PROMPT = """You are UIX, the World-Class Frontend Specialist.

Your Goal: Create stunning, production-grade user interfaces that rival top SaaS products (like Linear, Vercel, Stripe).

Responsibilities:
1. UI Design: Use Tailwind CSS to create beautiful, clean, modern interfaces.
   - Use generous whitespace, subtle shadows, and rounded corners.
   - Ensure mobile responsiveness (mobile-first).
   - Use a consistent color palette and typography.
2. React Architecture:
   - Use functional components with hooks.
   - Implement proper state management.
   - Handle Loading and Error states gracefully (show skeletons/spinners).
3. Integration:
   - Connect to the backend using Axios.
   - Handle API errors and show user-friendly toasts/alerts.

Tech Stack:
- React 18 + Vite
- Tailwind CSS (Utility-first)
- Axios

Output Format:
- Start with [AGENT: UIX]
- Output complete, runnable React code
- Use JSON format: {"filename": "code content"}

Do not output generic or ugly code. Make it shine."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Generate frontend code."""
        spec = context.project_spec
        
        # Get architecture and backend info
        arch_spec = ""
        backend_info = ""
        for msg in context.messages:
            if msg.role == AgentRole.ARCH:
                arch_spec = msg.content
            elif msg.role == AgentRole.BACKEND:
                backend_info = msg.content
        
        prompt = f"""Generate the React frontend for this app:

PROJECT: {context.project_name}
SPEC: {json.dumps(spec, indent=2, default=str)}

ARCHITECTURE:
{arch_spec}

BACKEND:
{backend_info}

Generate these files as JSON (filename -> complete code):
1. frontend/index.html - HTML entry point
2. frontend/package.json - Dependencies
3. frontend/vite.config.js - Vite config
4. frontend/src/main.jsx - React entry
5. frontend/src/App.jsx - Main component with full UI

Requirements:
- Modern React with hooks
- Clean, responsive design (inline styles or Tailwind classes)
- API integration with axios
- Loading states and error handling
- Full CRUD UI matching backend
- Include lucide-react for icons in package.json

Output format:
{{
    "frontend/index.html": "html code",
    "frontend/package.json": "json content",
    "frontend/vite.config.js": "vite config",
    "frontend/src/main.jsx": "react entry",
    "frontend/src/App.jsx": "main component"
}}"""

        if context.image_data:
            prompt += "\n\n[IMAGE CONTEXT PROVIDED] Use the attached image as the PRIMARY reference for the UI design. Match the layout, colors, and structure exactly."

        # Pass image_data to provider if supported (Gemini)
        kwargs = {}
        if context.image_data and self.provider and "gemini" in self.provider.name.lower():
            kwargs["image_data"] = context.image_data

        response = await self._call_llm(prompt, max_tokens=8192, **kwargs)
        artifacts = {}
        
        # Parse JSON response using base class method
        artifacts = self._parse_json_response(response)
        
        if artifacts and len(artifacts) >= 3:
            logger.info(f"[UIX] Parsed {len(artifacts)} files from LLM")
        else:
            logger.warning("[UIX] Using fallback frontend generation")
            artifacts = self._generate_fallback_frontend(context)
        
        return AgentMessage(
            role=self.ROLE,
            content=f"Generated {len(artifacts)} frontend files",
            reasoning="Frontend code generated",
            confidence=0.9 if len(artifacts) >= 4 else 0.6,
            artifacts=artifacts
        )
    
    def _generate_fallback_frontend(self, context: AgentContext) -> Dict[str, str]:
        """Generate fallback frontend code."""
        name = context.project_name
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower())
        
        return {
            "frontend/index.html": f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{name}</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
''',
            "frontend/package.json": json.dumps({
                "name": safe_name,
                "version": "1.0.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build"},
                "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0", "axios": "^1.6.0"},
                "devDependencies": {"vite": "^5.0.0", "@vitejs/plugin-react": "^4.2.0"}
            }, indent=2),
            "frontend/vite.config.js": '''import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 }
});
''',
            "frontend/src/main.jsx": '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
''',
            "frontend/src/App.jsx": f'''import React, {{ useState, useEffect }} from 'react';
import axios from 'axios';

const API = 'http://localhost:8000';

export default function App() {{
  const [items, setItems] = useState([]);
  const [title, setTitle] = useState('');

  useEffect(() => {{ axios.get(`${{API}}/items`).then(r => setItems(r.data)); }}, []);

  const addItem = async (e) => {{
    e.preventDefault();
    if (!title) return;
    await axios.post(`${{API}}/items`, {{ title }});
    setTitle('');
    const r = await axios.get(`${{API}}/items`);
    setItems(r.data);
  }};

  const deleteItem = async (id) => {{
    await axios.delete(`${{API}}/items/${{id}}`);
    setItems(items.filter(i => i.id !== id));
  }};

  return (
    <div style={{{{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}}}>
      <h1>{name}</h1>
      <form onSubmit={{addItem}} style={{{{ marginBottom: '1rem' }}}}>
        <input value={{title}} onChange={{e => setTitle(e.target.value)}} placeholder="New item" style={{{{ padding: '0.5rem', marginRight: '0.5rem' }}}} />
        <button type="submit" style={{{{ padding: '0.5rem 1rem' }}}}>Add</button>
      </form>
      <ul style={{{{ listStyle: 'none', padding: 0 }}}}>
        {{items.map(item => (
          <li key={{item.id}} style={{{{ padding: '0.5rem', marginBottom: '0.5rem', background: '#f5f5f5', display: 'flex', justifyContent: 'space-between' }}}}>
            <span>{{item.title}}</span>
            <button onClick={{() => deleteItem(item.id)}} style={{{{ color: 'red' }}}}>Delete</button>
          </li>
        ))}}
      </ul>
    </div>
  );
}}
'''
        }


class DebugAgent(BaseAgent):
    """
    DEBUG Agent - Error Fixing Specialist.
    
    Responsibilities:
    - Validate generated code
    - Fix syntax errors
    - Optimize code quality
    - Ensure consistency
    """
    
    ROLE = AgentRole.DEBUG
    TASK_TYPE = TaskType.CODE  # Uses Groq for fast fixes
    
    SYSTEM_PROMPT = """You are DEBUG, the error fixing and optimization specialist.

Your responsibilities:
1. Validate generated code for errors
2. Fix syntax and logic issues
3. Ensure code consistency
4. Optimize performance

Focus on:
- Python syntax correctness
- JavaScript/JSX syntax
- Import statements
- API endpoint consistency
- Error handling

Output Format:
- Start with [AGENT: DEBUG]
- List issues found
- Provide fixed code as JSON

Be thorough but efficient."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Validate and fix generated code."""
        
        # Collect all artifacts from other agents
        all_files = dict(context.files)
        
        for msg in context.messages:
            if msg.artifacts:
                all_files.update(msg.artifacts)
        
        if not all_files:
            return AgentMessage(
                role=self.ROLE,
                content="No files to validate",
                reasoning="No artifacts found",
                confidence=1.0,
                artifacts={}
            )
        
        # Quick validation without LLM (syntax check)
        issues = []
        fixed_files = {}
        
        for filepath, content in all_files.items():
            if filepath.endswith('.py'):
                # Check Python syntax
                try:
                    compile(content, filepath, 'exec')
                except SyntaxError as e:
                    issues.append(f"{filepath}: {e}")
            elif filepath.endswith('.json'):
                # Check JSON syntax
                try:
                    json.loads(content)
                except json.JSONDecodeError as e:
                    issues.append(f"{filepath}: Invalid JSON - {e}")
        
        if issues:
            # Try to fix with LLM
            prompt = f"""Fix these code issues:

ISSUES:
{chr(10).join(issues)}

FILES:
{json.dumps(all_files, indent=2)}

Output the fixed files as JSON:
{{"filepath": "fixed content"}}

Only include files that needed fixing."""

            response = await self._call_llm(prompt, max_tokens=8192)
            
            if response:
                try:
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        fixed_files = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        return AgentMessage(
            role=self.ROLE,
            content=f"Validated {len(all_files)} files, found {len(issues)} issues",
            reasoning=f"Issues: {issues}" if issues else "No issues found",
            confidence=1.0 if not issues else 0.8,
            artifacts=fixed_files
        )


class EditAgent(BaseAgent):
    """
    EDIT Agent - Iterative Refinement Specialist.
    
    Responsibilities:
    - Analyze existing code
    - Apply user instructions (diffs)
    - Refactor code
    """
    
    ROLE = AgentRole.EDIT
    TASK_TYPE = TaskType.CODE
    
    SYSTEM_PROMPT = """You are EDIT, the iterative refinement specialist.

Your responsibilities:
1. Analyze the existing code provided
2. Understand the user's modification request
3. Apply the changes surgically (don't rewrite if not needed)
4. Ensure the code remains functional

Output Format:
- Start with [AGENT: EDIT]
- Output ONLY the files that need changing
- Use JSON format: {"filename": "new complete content"}

Be precise. Do not break existing functionality."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Apply edits to existing files using AST-aware patching."""
        spec = context.project_spec
        instruction = spec.get("instruction", "")
        
        # Collect all current files
        all_files = dict(context.files)
        
        prompt = f"""Apply this modification to the project:

INSTRUCTION: {instruction}

CURRENT FILES:
{json.dumps(all_files, indent=2)}

Return ONLY the files that need to be changed as JSON:
{{"filename": "new complete content"}}
"""

        response = await self._call_llm(prompt, max_tokens=8192)
        raw_artifacts = self._parse_json_response(response)
        
        if not raw_artifacts:
            return AgentMessage(
                role=self.ROLE,
                content="No changes generated",
                reasoning="LLM returned no files",
                confidence=0.5,
                artifacts={}
            )
        
        # Apply AST-aware patching for Python files
        patched_artifacts = {}
        for filepath, new_content in raw_artifacts.items():
            if filepath in all_files and filepath.endswith('.py'):
                # Try AST patching
                old_content = all_files[filepath]
                patch = generate_patch(old_content, new_content, filepath)
                
                if patch.patch_type != "full_replace":
                    logger.info(f"[EDIT] Applying {patch.patch_type} patch to {filepath}")
                    patched_content = apply_patch(old_content, patch)
                    patched_artifacts[filepath] = patched_content
                else:
                    patched_artifacts[filepath] = new_content
            else:
                patched_artifacts[filepath] = new_content
        
        return AgentMessage(
            role=self.ROLE,
            content=f"Applied edits to {len(patched_artifacts)} files",
            reasoning="Edits applied with AST patching where possible",
            confidence=0.9,
            artifacts=patched_artifacts
        )


class QualityAgent(BaseAgent):
    """
    QUALITY Agent - Code Quality & Security Specialist.
    
    Responsibilities:
    - Static analysis (simulated)
    - Security vulnerability scanning
    - Code style enforcement
    - Best practices review
    """
    
    ROLE = AgentRole.QUALITY
    TASK_TYPE = TaskType.CODE
    
    SYSTEM_PROMPT = """You are QUALITY, the code quality and security specialist.

Your responsibilities:
1. Review code for security vulnerabilities (SQLi, XSS, secrets)
2. Enforce code style (PEP8, ESLint principles)
3. Identify anti-patterns and bad practices
4. Fix issues directly in the code

Focus on:
- Security: Input validation, auth checks, secret handling
- Performance: N+1 queries, memory leaks
- Style: Type hints, docstrings, variable naming

Output Format:
- Start with [AGENT: QUALITY]
- List critical issues found
- Output FIXED files as JSON: {"filename": "fixed content"}

Be strict but practical."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Review and fix code quality issues with automated validation."""
        
        # Collect all current files
        all_files = dict(context.files)
        
        # Skip if no files
        if not all_files:
            return AgentMessage(role=self.ROLE, content="No files to review")
        
        # Run automated validation first
        validation_service = get_validation_service()
        all_passed, validation_results = await validation_service.validate_and_report(all_files)
        
        # Collect validation issues
        issues_summary = []
        critical_issues = []
        
        for validator_name, result in validation_results.items():
            if not result.passed:
                issues_summary.append(
                    f"{validator_name}: {result.error_count} errors, {result.warning_count} warnings"
                )
                
                for issue in result.issues:
                    if issue.severity.value == "error":
                        critical_issues.append(
                            f"{issue.file}:{issue.line} - {issue.message} ({issue.rule})"
                        )
        
        # Build prompt with validation feedback
        validation_feedback = "\n".join(issues_summary) if issues_summary else "No automated issues found"
        critical_feedback = "\n".join(f"- {issue}" for issue in critical_issues[:20])

        prompt = f"""Review and fix quality/security issues in these files:

FILES:
{json.dumps(all_files, indent=2)}

AUTOMATED VALIDATION RESULTS:
{validation_feedback}

CRITICAL ISSUES TO FIX:
{critical_feedback if critical_feedback else "None"}

Check for:
1. Security: Hardcoded secrets, missing auth, injection risks
2. Quality: Unused imports, missing type hints, poor error handling
3. React: Missing keys in lists, dangerous dangerouslySetInnerHTML

Output ONLY the files that needed fixing as JSON:
{{"filename": "fixed complete content"}}
"""

        response = await self._call_llm(prompt, max_tokens=8192)
        artifacts = self._parse_json_response(response)
        
        status = "✅ All checks passed" if all_passed else f"⚠️ {len(critical_issues)} issues found"
        
        return AgentMessage(
            role=self.ROLE,
            content=f"Quality review complete: {status}. Fixed {len(artifacts) if artifacts else 0} files",
            reasoning=f"Automated validation + LLM review. {len(validation_results)} validators run",
            confidence=0.9 if all_passed else 0.7,
            artifacts=artifacts or {}
        )


class TestAgent(BaseAgent):
    """
    TEST Agent - QA Automation Specialist.
    
    Responsibilities:
    - Generate unit tests (pytest)
    - Generate frontend tests (React Testing Library)
    - Ensure critical paths are covered
    """
    
    ROLE = AgentRole.TEST
    TASK_TYPE = TaskType.CODE
    
    SYSTEM_PROMPT = """You are TEST, the QA automation specialist.

Your responsibilities:
1. Generate comprehensive unit tests
2. Cover success and failure scenarios
3. Mock external dependencies (DB, APIs)
4. Ensure tests are runnable

Tech Stack:
- Backend: pytest, pytest-asyncio, httpx
- Frontend: Vitest, React Testing Library

Output Format:
- Start with [AGENT: TEST]
- Output test files as JSON: {"filename": "test content"}

Generate high-quality, reliable tests."""
    
    async def execute(self, context: AgentContext) -> AgentMessage:
        """Generate tests for the project."""
        
        # Collect all current files
        all_files = dict(context.files)
        
        prompt = f"""Generate unit tests for this project:

FILES:
{json.dumps(all_files, indent=2)}

Generate:
1. backend/tests/test_main.py (API endpoints)
2. backend/tests/test_models.py (Data models)
3. frontend/src/__tests__/App.test.jsx (UI components)

Requirements:
- Use pytest for backend
- Use Vitest/RTL for frontend
- Mock database and external calls
- Test happy paths and error cases

Output JSON:
{{"filename": "test code content"}}
"""

        response = await self._call_llm(prompt, max_tokens=8192)
        artifacts = self._parse_json_response(response)
        
        return AgentMessage(
            role=self.ROLE,
            content=f"Generated {len(artifacts) if artifacts else 0} test files",
            reasoning="Tests generated",
            confidence=0.9,
            artifacts=artifacts or {}
        )


class AgentOrchestrator:
    """
    Orchestrates multi-agent collaboration.
    
    Workflow:
    1. CORE analyzes request and creates plan
    2. ARCH designs architecture
    3. BACKEND generates backend code
    4. UIX generates frontend code
    5. DEBUG validates and fixes (with feedback loop)
    6. Combine all artifacts
    """
    
    def __init__(self, providers: Dict[TaskType, AIProvider]):
        """
        Initialize orchestrator with task-specific providers.
        
        Args:
            providers: Dict mapping TaskType to AIProvider
                - CODE → Groq (fastest for code)
                - REASONING → DeepSeek (best for planning)
                - UI_TEXT → Gemini (quality text/UI)
        """
        self.providers = providers
        
        # Initialize agents with providers
        self.agents = {
            AgentRole.CORE: CoreAgent(providers),
            AgentRole.ARCH: ArchAgent(providers),
            AgentRole.BACKEND: BackendAgent(providers),
            AgentRole.UIX: UIXAgent(providers),
            AgentRole.DEBUG: DebugAgent(providers),
            AgentRole.EDIT: EditAgent(providers),
            AgentRole.QUALITY: QualityAgent(providers),
            AgentRole.TEST: TestAgent(providers),
        }
        
        logger.info(f"🤖 AgentOrchestrator initialized with {len(providers)} providers")
    
    async def _run_agent(self, role: AgentRole, context: AgentContext) -> AgentMessage:
        """Run a specific agent and update context."""
        agent = self.agents.get(role)
        if not agent:
            raise ValueError(f"Agent {role} not found")
            
        logger.info(f"[{role.value}] Executing...")
        message = await agent.execute(context)
        context.messages.append(message)
        
        if message.artifacts:
            context.files.update(message.artifacts)
            logger.info(f"[{role.value}] Generated {len(message.artifacts)} files")
            
        return message

    async def generate_project(
        self,
        spec: Dict[str, Any],
        project_name: Optional[str] = None,
        image_data: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate a complete project using multi-agent collaboration.
        
        Args:
            spec: Project specification
            project_name: Name of the project
            image_data: Optional base64 encoded image
            project_id: ID of the project (for context tracking)
            
        Returns:
            Dictionary of filepath -> content
        """
        if not project_name:
            project_name = spec.get("name", spec.get("raw", "GeneratedApp"))[:50]
        
        # Create shared context
        context = AgentContext(
            project_spec=spec,
            project_name=project_name,
            project_id=project_id,
            image_data=image_data
        )
        
        logger.info(f"🚀 Starting multi-agent generation for: {project_name}")
        
        try:
            # 1. Plan & Design
            await self._run_agent(AgentRole.CORE, context)
            await self._run_agent(AgentRole.ARCH, context)
            
            # 2. Generate Code
            await self._run_agent(AgentRole.BACKEND, context)
            await self._run_agent(AgentRole.UIX, context)
            
            # 3. Intelligent Feedback Loop
            max_retries = 2
            for i in range(max_retries):
                logger.info(f"🔄 Quality Control Loop {i+1}/{max_retries}")
                
                # Run Debug Agent to find and fix issues
                debug_msg = await self._run_agent(AgentRole.DEBUG, context)
                
                # Check if we are clean
                if "found 0 issues" in debug_msg.content or "No issues found" in debug_msg.reasoning:
                    logger.info("✅ Quality Check Passed")
                    break
                
                # If issues were found, DebugAgent has already tried to fix them 
                # and updated context.files via _run_agent -> context.files.update
                if debug_msg.artifacts:
                    logger.info(f"🛠️ Applied {len(debug_msg.artifacts)} fixes")
                else:
                    logger.warning("⚠️  Issues found but no fixes generated")
            
            # 4. Enterprise Quality Assurance
            logger.info("🛡️ Running Security & Quality Review")
            await self._run_agent(AgentRole.QUALITY, context)
            
            # 5. Test Generation
            logger.info("🧪 Generating Test Suite")
            await self._run_agent(AgentRole.TEST, context)
                    
        except Exception as e:
            logger.error(f"❌ Orchestration failed: {e}")
            context.errors.append(str(e))
        
        # Combine all files
        final_files = dict(context.files)
        
        # Add README if not present
        if "README.md" not in final_files:
            final_files["README.md"] = self._generate_readme(context)
        
        logger.info(f"✅ Multi-agent generation complete: {len(final_files)} files")
        
        return final_files
    
    def _generate_readme(self, context: AgentContext) -> str:
        """Generate a README.md file."""
        return f"""# {context.project_name}

{context.project_spec.get('raw', context.project_spec.get('description', 'Generated application'))}

## Quick Start

### Backend
```bash
cd backend
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

Visit http://localhost:8000/docs for Swagger UI.

---
*Generated by Multi-Agent AI System*
"""

    async def edit_project(
        self,
        current_files: Dict[str, str],
        instruction: str,
        project_name: str = "ExistingProject"
    ) -> Dict[str, str]:
        """
        Edit an existing project based on user instructions.
        """
        context = AgentContext(
            project_spec={"instruction": instruction},
            project_name=project_name,
            files=current_files
        )
        
        logger.info(f"✏️ Editing project: {project_name} with instruction: {instruction}")
        
        try:
            # Run Edit Agent
            await self._run_agent(AgentRole.EDIT, context)
            
            # Run Debug Agent to ensure no regressions
            await self._run_agent(AgentRole.DEBUG, context)
            
        except Exception as e:
            logger.error(f"❌ Edit failed: {e}")
            context.errors.append(str(e))
            
        return dict(context.files)


def create_orchestrator_with_providers(
    providers: List[AIProvider]
) -> AgentOrchestrator:
    """
    Create an orchestrator with task-based provider mapping.
    
    Maps providers to task types based on their capabilities:
    - Groq → CODE (fastest)
    - Cerebras → REASONING (ultra-fast reasoning)
    - Gemini → UI_TEXT (quality)
    - OpenRouter → fallback for all
    """
    provider_map: Dict[TaskType, AIProvider] = {}
    
    for provider in providers:
        if not provider.is_available():
            continue
        
        name = provider.name.lower()
        
        # Priority mapping: DeepSeek first for reasoning
        if 'deepseek' in name:
            provider_map[TaskType.REASONING] = provider  # PRIMARY for reasoning
        elif 'groq' in name:
            provider_map[TaskType.CODE] = provider
        elif 'cerebras' in name:
            # Fallback for reasoning if DeepSeek unavailable
            if TaskType.REASONING not in provider_map:
                provider_map[TaskType.REASONING] = provider
        elif 'gemini' in name:
            provider_map[TaskType.UI_TEXT] = provider
        elif 'openrouter' in name:
            # OpenRouter as fallback for missing task types
            if TaskType.CODE not in provider_map:
                provider_map[TaskType.CODE] = provider
            if TaskType.REASONING not in provider_map:
                provider_map[TaskType.REASONING] = provider
            if TaskType.UI_TEXT not in provider_map:
                provider_map[TaskType.UI_TEXT] = provider
    
    # Use any available provider as fallback
    if providers:
        available = [p for p in providers if p.is_available()]
        if available:
            for task_type in TaskType:
                if task_type not in provider_map:
                    provider_map[task_type] = available[0]
    
    logger.info(f"🤖 Agent-Provider Mapping:")
    for task_type, provider in provider_map.items():
        logger.info(f"   {task_type.value} → {provider.name}")
    
    return AgentOrchestrator(provider_map)
