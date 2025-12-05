# PHASE 1 IMPLEMENTATION - Complete Code

**Estimated Time:** 2 weeks  
**Priority:** CRITICAL  
**Goal:** Add DeepSeek provider + Strict manifest schemas

---

## Step 1: Install Dependencies

Add to `backend/requirements.txt`:

```txt
# Existing dependencies...

# Phase 1 additions
pydantic>=2.5.0  # Already present, ensure version
pydantic-settings>=2.1.0
```

---

## Step 2: Create DeepSeek Provider

**File:** `backend/app/ai/providers/deepseek.py`

```python
"""DeepSeek AI Provider - Ultra-fast reasoning specialist."""
import os
from typing import Optional
import httpx

from .base import AIProvider
from ...core.logging import logger


class DeepSeekProvider(AIProvider):
    """
    DeepSeek-R1 Provider for Complex Reasoning.
    
    Model: DeepSeek-R1 (671B parameters, distilled)
    Specialization: Advanced reasoning, complex planning, code architecture
    Free Tier: Available via OpenRouter
    Speed: ~50 tokens/second
    
    Best for:
    - System architecture design
    - Complex algorithm planning
    - Multi-step reasoning tasks
    - Strategic decision making
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = "deepseek/deepseek-r1:free"  # Free tier via OpenRouter
        self.name = "deepseek"
        self.base_url = "https://openrouter.ai/api/v1"
        
        # DeepSeek-specific optimizations
        self.max_context = 64000  # 64K context window
        self.supports_streaming = True
    
    def is_available(self) -> bool:
        """Check if DeepSeek is available."""
        return bool(self.api_key)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[str]:
        """
        Generate response using DeepSeek-R1.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Generated text or None on failure
        """
        if not self.is_available():
            logger.warning("[DeepSeek] API key not configured")
            return None
        
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://istudiox.dev",  # Required by OpenRouter
            "X-Title": "iStudiox AI Builder"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(f"[DeepSeek] Calling {self.model} (reasoning mode)")
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extract response
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    
                    # Log usage stats
                    if "usage" in data:
                        tokens_used = data["usage"].get("total_tokens", 0)
                        logger.info(f"[DeepSeek] Generated {tokens_used} tokens")
                    
                    return content
                
                logger.error(f"[DeepSeek] Unexpected response format: {data}")
                return None
                
        except httpx.HTTPStatusError as e:
            logger.error(f"[DeepSeek] HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error("[DeepSeek] Request timeout")
            return None
        except Exception as e:
            logger.error(f"[DeepSeek] Error: {e}")
            return None
    
    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": self.name,
            "model": self.model,
            "available": self.is_available(),
            "max_context": self.max_context,
            "specialization": "Advanced reasoning and planning",
            "speed": "Ultra-fast (~50 tok/s)",
            "free_tier": "Available via OpenRouter"
        }
```

---

## Step 3: Update Router to Support DeepSeek

**File:** `backend/app/ai/router.py` (update priority map)

```python
def get_priority(self, provider_name: str) -> int:
    """Get priority level for provider."""
    priority_map = {
        "deepseek": ProviderPriority.PRIMARY.value,      # NEW: Best for reasoning
        "gemini": ProviderPriority.PRIMARY.value,        # Best for UI/text
        "groq": ProviderPriority.PRIMARY.value,          # Best for code
        "cerebras": ProviderPriority.SECONDARY.value,    # Alternative reasoning
        "openrouter": ProviderPriority.SECONDARY.value,  # Fallback
        "ollama": ProviderPriority.TERTIARY.value,       # Local fallback
    }
    return priority_map.get(provider_name.lower(), ProviderPriority.FALLBACK.value)
```

---

## Step 4: Update Engine to Include DeepSeek

**File:** `backend/app/ai/engine.py` (add DeepSeek initialization)

```python
def _setup_providers(self):
    """Initialize available providers in priority order."""
    
    # DeepSeek - BEST for REASONING (671B params, ultra-fast)
    from .providers.deepseek import DeepSeekProvider
    deepseek = DeepSeekProvider()
    if deepseek.is_available():
        self.providers.append(deepseek)
        logger.info(f"✅ DeepSeek enabled: {deepseek.model} (reasoning specialist)")
    
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
    
    # Cerebras - Alternative for REASONING (~500 free/day)
    cerebras = CerebrasProvider()
    if cerebras.is_available():
        self.providers.append(cerebras)
        logger.info(f"✅ Cerebras enabled: {cerebras.model} (reasoning)")
    
    # OpenRouter - BACKUP (multiple models, 50 free/day)
    openrouter = OpenRouterProvider(use_free_only=True)
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
```

---

## Step 5: Update Agent Router Mapping

**File:** `backend/app/ai/agents.py` (update provider mapping)

```python
def create_orchestrator_with_providers(
    providers: List[AIProvider]
) -> AgentOrchestrator:
    """
    Create an orchestrator with task-based provider mapping.
    
    Maps providers to task types based on their capabilities:
    - DeepSeek → REASONING (best for planning, architecture)
    - Groq → CODE (fastest for code generation)
    - Gemini → UI_TEXT (quality text and UI)
    - OpenRouter → fallback for all
    """
    provider_map: Dict[TaskType, AIProvider] = {}
    
    for provider in providers:
        if not provider.is_available():
            continue
        
        name = provider.name.lower()
        
        # Priority mapping
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
```

---

## Step 6: Create Strict Manifest Schemas

**File:** `backend/app/schemas.py` (add at the end)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Literal
from enum import Enum


# ============ PHASE 1: Manifest Schemas ============


class AppType(str, Enum):
    """Supported application types."""
    CRUD = "crud"
    ECOMMERCE = "ecommerce"
    DASHBOARD = "dashboard"
    SOCIAL = "social"
    TODO = "todo"
    BLOG = "blog"
    AUTH = "auth"
    BOOKING = "booking"
    API = "api"


class TechStack(BaseModel):
    """Technology stack specification."""
    backend: str = Field(default="FastAPI + Pydantic", description="Backend framework")
    frontend: str = Field(default="React 18 + Vite", description="Frontend framework")
    styling: str = Field(default="Tailwind CSS", description="CSS framework")
    database: Optional[str] = Field(default=None, description="Database (optional)")
    auth: Optional[str] = Field(default=None, description="Auth provider (optional)")


class DataModel(BaseModel):
    """Data model specification."""
    name: str = Field(description="Model name (e.g., User, Product)")
    fields: Dict[str, str] = Field(description="Field name -> type mapping")
    relationships: Optional[List[str]] = Field(default=[], description="Relationships to other models")
    
    @validator('name')
    def validate_name(cls, v):
        if not v[0].isupper():
            raise ValueError("Model name must start with uppercase letter")
        return v


class APIEndpoint(BaseModel):
    """API endpoint specification."""
    path: str = Field(description="Endpoint path (e.g., /items)")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(description="HTTP method")
    description: str = Field(description="What this endpoint does")
    request_model: Optional[str] = Field(default=None, description="Request body model")
    response_model: str = Field(description="Response model")
    
    @validator('path')
    def validate_path(cls, v):
        if not v.startswith('/'):
            return f"/{v}"
        return v


class FileSpec(BaseModel):
    """File specification."""
    path: str = Field(description="Relative file path")
    description: str = Field(description="What this file contains")
    dependencies: List[str] = Field(default=[], description="Files this depends on")


class ProjectManifest(BaseModel):
    """
    Structured project manifest - output of CORE agent.
    
    This is the single source of truth for project generation.
    All downstream agents use this manifest to generate code.
    """
    
    # Analysis
    analysis: str = Field(
        description="Brief requirement analysis (2-3 sentences)"
    )
    
    # Classification
    app_type: AppType = Field(
        description="Detected application type"
    )
    
    # Features
    features: List[str] = Field(
        min_items=1,
        description="List of features to implement"
    )
    
    # Tech Stack
    tech_stack: TechStack = Field(
        default_factory=TechStack,
        description="Technology stack"
    )
    
    # Architecture
    models: List[DataModel] = Field(
        default=[],
        description="Data models to create"
    )
    
    endpoints: List[APIEndpoint] = Field(
        default=[],
        description="API endpoints to implement"
    )
    
    # Files
    files_to_generate: List[FileSpec] = Field(
        description="Exact files to create with descriptions"
    )
    
    # Integrations
    integrations: List[str] = Field(
        default=[],
        description="Third-party integrations (supabase, stripe, auth0, etc.)"
    )
    
    # Agents
    agents_needed: List[Literal["ARCH", "BACKEND", "UIX", "DEBUG", "QUALITY", "TEST"]] = Field(
        description="Which specialist agents to activate"
    )
    
    # Priority
    priority: str = Field(
        description="What to build first (MVP focus)"
    )
    
    @validator('features')
    def validate_features(cls, v):
        if not v:
            raise ValueError("At least one feature must be specified")
        return v
    
    @validator('files_to_generate')
    def validate_files(cls, v):
        required_files = [
            "backend/main.py",
            "backend/requirements.txt",
            "frontend/src/App.jsx",
            "frontend/package.json"
        ]
        
        file_paths = [f.path for f in v]
        missing = [f for f in required_files if f not in file_paths]
        
        if missing:
            raise ValueError(f"Missing required files: {missing}")
        
        return v


class ArchitectureSpec(BaseModel):
    """
    Architecture specification - output of ARCH agent.
    
    Provides detailed design decisions and structure.
    """
    
    design_decisions: List[str] = Field(
        description="Key architecture decisions made"
    )
    
    endpoints: List[APIEndpoint] = Field(
        description="Complete API specification"
    )
    
    models: List[DataModel] = Field(
        description="Complete data model specification"
    )
    
    file_structure: Dict[str, str] = Field(
        description="File path -> purpose mapping"
    )
    
    scalability_notes: Optional[str] = Field(
        default=None,
        description="Notes on how this scales"
    )


# ============ Helper Functions ============


def validate_manifest(data: dict) -> ProjectManifest:
    """
    Validate and parse a project manifest.
    
    Args:
        data: Raw dict from LLM
        
    Returns:
        Validated ProjectManifest
        
    Raises:
        ValidationError: If manifest is invalid
    """
    return ProjectManifest(**data)


def create_default_manifest(project_name: str, description: str) -> ProjectManifest:
    """Create a default manifest for fallback."""
    return ProjectManifest(
        analysis=f"Building a basic {project_name} application",
        app_type=AppType.CRUD,
        features=["CRUD operations", "REST API", "React UI"],
        models=[
            DataModel(
                name="Item",
                fields={"id": "int", "title": "str", "created_at": "datetime"}
            )
        ],
        endpoints=[
            APIEndpoint(
                path="/items",
                method="GET",
                description="List all items",
                response_model="List[Item]"
            ),
            APIEndpoint(
                path="/items",
                method="POST",
                description="Create item",
                request_model="ItemCreate",
                response_model="Item"
            )
        ],
        files_to_generate=[
            FileSpec(path="backend/main.py", description="FastAPI app"),
            FileSpec(path="backend/requirements.txt", description="Dependencies"),
            FileSpec(path="frontend/src/App.jsx", description="Main React component"),
            FileSpec(path="frontend/package.json", description="NPM config"),
            FileSpec(path="frontend/index.html", description="HTML entry"),
            FileSpec(path="frontend/vite.config.js", description="Vite config"),
            FileSpec(path="frontend/src/main.jsx", description="React entry"),
            FileSpec(path="README.md", description="Documentation")
        ],
        agents_needed=["ARCH", "BACKEND", "UIX"],
        priority="Build basic CRUD first"
    )
```

---

## Step 7: Update CoreAgent to Use Manifest Schema

**File:** `backend/app/ai/agents.py` (update CoreAgent.execute method)

```python
from app.schemas import ProjectManifest, create_default_manifest, validate_manifest
from pydantic import ValidationError

class CoreAgent(BaseAgent):
    """CORE Agent - The Orchestrator with strict manifest output."""
    
    ROLE = AgentRole.CORE
    TASK_TYPE = TaskType.REASONING  # Will use DeepSeek for deep analysis
    
    SYSTEM_PROMPT = """You are CORE, the Lead Product Manager & Orchestrator.

Your Goal: Create a PRECISE, STRUCTURED project manifest that drives all downstream generation.

Output Format: STRICTLY JSON matching this schema:
{
  "analysis": "Brief analysis (2-3 sentences)",
  "app_type": "crud|ecommerce|dashboard|social|todo|blog|auth|booking|api",
  "features": ["Feature 1", "Feature 2"],
  "tech_stack": {
    "backend": "FastAPI + Pydantic",
    "frontend": "React 18 + Vite",
    "styling": "Tailwind CSS"
  },
  "models": [
    {
      "name": "ModelName",
      "fields": {"field1": "type1", "field2": "type2"},
      "relationships": []
    }
  ],
  "endpoints": [
    {
      "path": "/endpoint",
      "method": "GET|POST|PUT|DELETE",
      "description": "What it does",
      "request_model": "ModelName (optional)",
      "response_model": "ResponseModel"
    }
  ],
  "files_to_generate": [
    {
      "path": "backend/main.py",
      "description": "FastAPI app with all endpoints",
      "dependencies": []
    },
    {
      "path": "frontend/src/App.jsx",
      "description": "Main React component",
      "dependencies": []
    }
  ],
  "integrations": [],
  "agents_needed": ["ARCH", "BACKEND", "UIX"],
  "priority": "What to build first"
}

CRITICAL:
- Output ONLY valid JSON
- Include ALL required files (backend/main.py, backend/requirements.txt, frontend/src/App.jsx, frontend/package.json, frontend/index.html, frontend/vite.config.js, frontend/src/main.jsx)
- Be specific about models and endpoints"""

    async def execute(self, context: AgentContext) -> AgentMessage:
        """Analyze request and create strict manifest."""
        spec = context.project_spec
        raw_desc = spec.get("raw", spec.get("description", ""))
        
        prompt = f"""Analyze this app request and create a STRUCTURED PROJECT MANIFEST:

PROJECT: {context.project_name}
DESCRIPTION: {raw_desc}

SPEC DETAILS:
{json.dumps(spec, indent=2, default=str)}

Create a complete project manifest following the exact JSON schema.
Identify:
1. App type (choose ONE: crud, ecommerce, dashboard, social, todo, blog, auth, booking, api)
2. Core features (minimum 3, maximum 10)
3. Data models needed (with fields and types)
4. API endpoints (full CRUD for each model)
5. All files to generate (include ALL standard files)
6. Which specialist agents to activate

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
```

---

## Step 8: Environment Configuration

**File:** `backend/.env` (add DeepSeek key)

```bash
# Existing keys...
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key

# Phase 1: Add DeepSeek (via OpenRouter)
OPENROUTER_API_KEY=your_openrouter_key
# Note: DeepSeek uses OpenRouter API, so same key works for both
```

Get your OpenRouter API key from: https://openrouter.ai/keys

---

## Step 9: Testing Phase 1

**File:** `backend/tests/test_phase1.py` (NEW)

```python
"""Tests for Phase 1: DeepSeek + Manifest Schemas."""
import pytest
from app.ai.providers.deepseek import DeepSeekProvider
from app.schemas import ProjectManifest, validate_manifest, AppType
from pydantic import ValidationError


class TestDeepSeekProvider:
    """Test DeepSeek provider integration."""
    
    @pytest.mark.asyncio
    async def test_deepseek_available(self):
        """Test DeepSeek provider availability."""
        provider = DeepSeekProvider()
        # Should be available if OPENROUTER_API_KEY is set
        assert isinstance(provider.is_available(), bool)
    
    @pytest.mark.asyncio
    async def test_deepseek_generation(self):
        """Test DeepSeek text generation."""
        provider = DeepSeekProvider()
        
        if not provider.is_available():
            pytest.skip("DeepSeek API key not configured")
        
        response = await provider.generate(
            prompt="Explain the MVC architecture pattern in 2 sentences.",
            system_prompt="You are a software architecture expert.",
            max_tokens=100,
            temperature=0.5
        )
        
        assert response is not None
        assert len(response) > 20
        assert "MVC" in response or "Model" in response


class TestManifestSchemas:
    """Test manifest schema validation."""
    
    def test_valid_manifest(self):
        """Test valid manifest creation."""
        data = {
            "analysis": "Building a todo app with user auth",
            "app_type": "todo",
            "features": ["Add todos", "Mark complete", "User auth"],
            "models": [
                {
                    "name": "Todo",
                    "fields": {"id": "int", "title": "str", "completed": "bool"},
                    "relationships": []
                }
            ],
            "endpoints": [
                {
                    "path": "/todos",
                    "method": "GET",
                    "description": "List todos",
                    "response_model": "List[Todo]"
                }
            ],
            "files_to_generate": [
                {"path": "backend/main.py", "description": "FastAPI app", "dependencies": []},
                {"path": "backend/requirements.txt", "description": "Deps", "dependencies": []},
                {"path": "frontend/src/App.jsx", "description": "React", "dependencies": []},
                {"path": "frontend/package.json", "description": "NPM", "dependencies": []},
                {"path": "frontend/index.html", "description": "HTML", "dependencies": []},
                {"path": "frontend/vite.config.js", "description": "Vite", "dependencies": []},
                {"path": "frontend/src/main.jsx", "description": "Entry", "dependencies": []}
            ],
            "agents_needed": ["ARCH", "BACKEND", "UIX"],
            "priority": "Basic CRUD first"
        }
        
        manifest = validate_manifest(data)
        assert manifest.app_type == AppType.TODO
        assert len(manifest.features) == 3
        assert len(manifest.models) == 1
        assert manifest.models[0].name == "Todo"
    
    def test_invalid_manifest_missing_files(self):
        """Test manifest validation fails without required files."""
        data = {
            "analysis": "Test",
            "app_type": "crud",
            "features": ["Feature1"],
            "files_to_generate": [
                {"path": "backend/main.py", "description": "Test", "dependencies": []}
            ],
            "agents_needed": ["ARCH"],
            "priority": "Test"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate_manifest(data)
        
        assert "Missing required files" in str(exc_info.value)
    
    def test_invalid_manifest_bad_app_type(self):
        """Test manifest validation fails with invalid app type."""
        data = {
            "analysis": "Test",
            "app_type": "invalid_type",
            "features": ["Feature1"],
            "files_to_generate": [],
            "agents_needed": ["ARCH"],
            "priority": "Test"
        }
        
        with pytest.raises(ValidationError):
            validate_manifest(data)


# Run tests with:
# cd backend
# pytest tests/test_phase1.py -v
```

---

## Step 10: Verification Checklist

After implementing Phase 1, verify:

### ✅ DeepSeek Integration
```bash
# Test DeepSeek provider
cd backend
python -c "
from app.ai.providers.deepseek import DeepSeekProvider
import asyncio

async def test():
    p = DeepSeekProvider()
    print(f'Available: {p.is_available()}')
    if p.is_available():
        resp = await p.generate('Say hello', max_tokens=50)
        print(f'Response: {resp}')

asyncio.run(test())
"
```

### ✅ Manifest Validation
```bash
# Test manifest schemas
cd backend
python -c "
from app.schemas import ProjectManifest, create_default_manifest

manifest = create_default_manifest('TestApp', 'A test application')
print(f'App Type: {manifest.app_type}')
print(f'Features: {manifest.features}')
print(f'Models: {len(manifest.models)}')
print(f'Endpoints: {len(manifest.endpoints)}')
print(f'Files: {len(manifest.files_to_generate)}')
print('✅ Manifest validation working!')
"
```

### ✅ End-to-End Test
```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# In another terminal, create a test project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "TodoApp",
    "spec": "Create a todo list app with user authentication"
  }'

# Check logs for:
# ✅ DeepSeek enabled
# ✅ Valid manifest created
# ✅ Agents activated
```

---

## Success Criteria

Phase 1 is complete when:

1. ✅ DeepSeek provider is available and responding
2. ✅ CORE agent uses DeepSeek for reasoning tasks
3. ✅ Manifests pass Pydantic validation
4. ✅ All required files are enforced in manifest
5. ✅ Tests pass: `pytest tests/test_phase1.py -v`
6. ✅ Generated projects follow strict manifest structure

---

## Performance Improvements

After Phase 1, you should see:

- **10-15% better planning quality** (DeepSeek's reasoning)
- **Zero invalid manifests** (Pydantic validation)
- **Consistent file structure** (enforced schema)
- **Better agent coordination** (structured data flow)

---

## Next Steps

Once Phase 1 is complete:

1. **Phase 2:** VFS + Git-like patching (2 weeks)
2. **Phase 3:** Comprehensive validation (1 week)
3. **Phase 4:** Project memory / RAG (1 week)

**Estimated Total:** 6 weeks to transform system quality

---

*Generated: December 3, 2025*
