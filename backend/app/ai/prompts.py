"""AI Prompt Templates for Code Generation - Enhanced for App-Specific Output."""

import re
from typing import Dict, List, Tuple


def detect_app_type(description: str) -> Tuple[str, List[str]]:
    """
    Intelligently detect app type and extract features from description.
    
    Returns:
        (app_type, list_of_features)
    """
    desc_lower = description.lower()
    
    # App type detection patterns
    patterns = {
        "ecommerce": [
            r"e-?commerce", r"shop", r"product", r"cart", r"checkout", 
            r"catalog", r"store", r"buy", r"sell", r"inventory", r"order"
        ],
        "dashboard": [
            r"dashboard", r"analytics", r"chart", r"graph", r"report",
            r"statistics", r"metrics", r"visualization", r"monitor"
        ],
        "social": [
            r"social", r"post", r"feed", r"follow", r"like", r"comment",
            r"profile", r"friend", r"share", r"message", r"chat"
        ],
        "todo": [
            r"todo", r"task", r"checklist", r"reminder", r"note",
            r"complete", r"done", r"pending"
        ],
        "blog": [
            r"blog", r"article", r"post", r"author", r"publish",
            r"content", r"cms", r"editorial"
        ],
        "auth": [
            r"auth", r"login", r"signup", r"register", r"password",
            r"user management", r"session", r"jwt", r"oauth"
        ],
        "booking": [
            r"book", r"reservation", r"appointment", r"schedule",
            r"calendar", r"slot", r"availability"
        ],
        "api": [
            r"api only", r"backend only", r"rest api", r"microservice",
            r"no frontend", r"headless"
        ]
    }
    
    # Detect app type
    app_type = "crud"  # default
    max_matches = 0
    
    for type_name, type_patterns in patterns.items():
        matches = sum(1 for p in type_patterns if re.search(p, desc_lower))
        if matches > max_matches:
            max_matches = matches
            app_type = type_name
    
    # Extract features from description
    features = []
    
    # Common feature patterns
    feature_patterns = [
        (r"search", "Search functionality"),
        (r"filter", "Filter/sort capability"),
        (r"pagination", "Pagination"),
        (r"auth|login|signup", "User authentication"),
        (r"upload|image", "File/image upload"),
        (r"cart|basket", "Shopping cart"),
        (r"payment|checkout|buy", "Payment/checkout"),
        (r"comment", "Comments system"),
        (r"rating|review", "Rating/review system"),
        (r"notification", "Notifications"),
        (r"dark mode|theme", "Theme switching"),
        (r"responsive|mobile", "Mobile responsive"),
        (r"export|download", "Data export"),
        (r"dashboard|stats|analytics", "Analytics dashboard"),
        (r"real-?time|live", "Real-time updates"),
        (r"category|categories", "Categories/tags"),
        (r"edit|update", "Edit capability"),
        (r"delete|remove", "Delete capability"),
        (r"list|view all", "List view"),
        (r"detail|single", "Detail view"),
    ]
    
    for pattern, feature_name in feature_patterns:
        if re.search(pattern, desc_lower):
            features.append(feature_name)
    
    return app_type, features


def extract_project_name(description: str) -> str:
    """Extract a clean project name from description."""
    # Remove common prefixes
    desc = re.sub(r'^(create|build|make|develop|generate)\s+(a|an|the)?\s*', '', description.lower())
    
    # Take first few meaningful words
    words = desc.split()[:4]
    name = '_'.join(words)
    
    # Clean up
    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
    name = name[:30] if len(name) > 30 else name
    
    return name.title().replace('_', '') + "App" if name else "GeneratedApp"


SYSTEM_PROMPT = """You are an expert full-stack developer AI. Generate COMPLETE, WORKING, WORLD-CLASS CODE.

⚠️ CRITICAL: DO NOT generate generic CRUD templates. Analyze the request and generate CODE SPECIFIC to the app type.

OUTPUT FORMAT (VERY IMPORTANT):
- Your entire response MUST be a single JSON object.
- Do not wrap it in markdown code fences.
- Do not add explanations before or after.

The JSON object must map file paths to COMPLETE file contents, for example:
{
    "backend/main.py": "complete python code ...",
    "frontend/src/App.jsx": "complete react code ..."
}

RULES:
1. Respond with exactly one JSON object and nothing else.
2. NO ```json wrapper, NO markdown, NO commentary – ONLY the JSON.
3. Generate COMPLETE, runnable code (no "TODO" placeholders).
4. Match the code to the SPECIFIC app requirements.
5. Include proper models, endpoints, and UI for the app type.
6. Use realistic sample data relevant to the app.
7. UI MUST BE BEAUTIFUL: Use Tailwind CSS with generous whitespace, shadows, and rounded corners.

TECH STACK:
- Backend: FastAPI + Pydantic
- Frontend: React 18 + Vite
- Styling: Tailwind CSS (via CDN or inline styles if config not possible)
- API: Axios

For E-COMMERCE: Include Product model with price/image/category, Cart, CartItem
For TODO: Include Todo model with completed status, priority, due date
For DASHBOARD: Include charts data, statistics, multiple metrics
For SOCIAL: Include User, Post, Comment, Like models
For BLOG: Include Article, Author, Category, Tag models"""


def get_generation_prompt(spec: dict, project_name: str) -> str:
    """Generate an intelligent, app-specific prompt."""
    
    # Extract description
    if "raw" in spec:
        description = spec["raw"]
    elif "description" in spec:
        description = spec["description"]
    else:
        description = str(spec)
    
    # Detect app type and features
    app_type, detected_features = detect_app_type(description)
    
    # Merge with explicitly provided features
    explicit_features = spec.get("features", [])
    all_features = list(set(detected_features + explicit_features))
    
    # Get app-specific guidance
    app_guidance = get_app_specific_guidance(app_type, all_features)
    
    return f"""Generate a COMPLETE {app_type.upper()} web application:

PROJECT: {project_name}
TYPE: {app_type}

USER REQUEST:
{description}

DETECTED FEATURES:
{chr(10).join(f'- {f}' for f in all_features) if all_features else '- Basic CRUD operations'}

{app_guidance}

REQUIRED FILES (MINIMUM):
1. backend/main.py - FastAPI with ALL endpoints for this app type
2. backend/requirements.txt - Dependencies
3. frontend/index.html - HTML entry
4. frontend/package.json - NPM config  
5. frontend/vite.config.js - Vite config
6. frontend/src/main.jsx - React entry
7. frontend/src/App.jsx - COMPLETE React app with FULL UI
8. README.md - Documentation

BACKEND INTEGRATION REQUIREMENTS:
- Assume the backend will be served behind a proxy at /api.
- All frontend API calls MUST use a relative base like "/api" (for example: axios.get("/api/items")), not hard-coded http://localhost URLs.

FRONTEND REQUIREMENTS:
- Use React 18 function components and hooks only.
- Prefer Axios instances configured with a baseURL of "/api".

⚠️ CRITICAL - OUTPUT FORMAT:
- Your response MUST be ONLY a raw JSON object.
- Do not wrap it in markdown code blocks.
- Do not add any explanation or text outside the JSON.

⚠️ IMPORTANT QUALITY RULES:
- Generate code SPECIFIC to a {app_type} app, NOT a generic CRUD app.
- Include realistic sample/mock data relevant to {app_type}.
- The UI should look like a real {app_type} application.
- Include ALL the detected features in the code.
- Remember: Output ONLY the JSON object, nothing else!"""


def get_app_specific_guidance(app_type: str, features: List[str]) -> str:
    """Get detailed guidance for specific app types."""
    
    guidance = {
        "ecommerce": """
E-COMMERCE APP REQUIREMENTS:
- Backend Models: Product(id, name, description, price, image_url, category, stock), Cart, CartItem
- Backend Endpoints: GET/POST /products, GET /products/{id}, GET /categories, POST /cart/add, GET /cart, DELETE /cart/{item_id}, POST /checkout
- Frontend: Product grid with images, category filter, search bar, shopping cart sidebar, cart total
- Sample Data: 6+ products with realistic names, prices ($10-$500), categories (Electronics, Clothing, Home)
- UI: Modern e-commerce look with product cards, Add to Cart buttons, cart icon with count""",

        "dashboard": """
DASHBOARD APP REQUIREMENTS:
- Backend Models: Metric, DataPoint, Report
- Backend Endpoints: GET /metrics, GET /stats, GET /chart-data/{type}, GET /reports
- Frontend: Stats cards (4+), line/bar charts, data tables, date range filter
- Sample Data: Revenue, users, orders metrics with weekly/monthly trends
- UI: Clean dashboard layout with cards, charts (use simple CSS bars/lines), summary stats""",

        "social": """
SOCIAL APP REQUIREMENTS:
- Backend Models: User(id, username, avatar, bio), Post(id, user_id, content, image, likes, created_at), Comment
- Backend Endpoints: GET /posts (feed), POST /posts, GET /posts/{id}, POST /posts/{id}/like, POST /posts/{id}/comment, GET /users/{id}
- Frontend: Feed of posts, create post form, like/comment buttons, user profiles
- Sample Data: 5+ users with avatars, 10+ posts with content and timestamps
- UI: Social media feed style with cards, profile pictures, engagement buttons""",

        "todo": """
TODO APP REQUIREMENTS:
- Backend Models: Todo(id, title, description, completed, priority, due_date, created_at)
- Backend Endpoints: GET /todos, POST /todos, PUT /todos/{id}, DELETE /todos/{id}, PATCH /todos/{id}/toggle
- Frontend: Todo list with checkboxes, add form with priority/due date, filter by status, edit inline
- Sample Data: 5+ todos with varying priorities (high/medium/low) and statuses
- UI: Clean task list with completion toggle, priority colors, due date display""",

        "blog": """
BLOG APP REQUIREMENTS:
- Backend Models: Article(id, title, slug, content, author, category, tags, published_at, views), Author, Category
- Backend Endpoints: GET /articles, GET /articles/{slug}, GET /categories, GET /authors/{id}/articles, POST /articles
- Frontend: Article list, article detail view, category sidebar, author info, read time
- Sample Data: 5+ articles with realistic titles, Lorem ipsum content, categories
- UI: Clean blog layout with article cards, featured image, reading time, author byline""",

        "booking": """
BOOKING APP REQUIREMENTS:
- Backend Models: Service(id, name, duration, price), TimeSlot(id, date, time, available), Booking(id, service_id, slot_id, customer_name, email)
- Backend Endpoints: GET /services, GET /slots?date=X, POST /bookings, GET /bookings/{id}
- Frontend: Service selection, calendar view, time slot picker, booking form, confirmation
- Sample Data: 4+ services, available slots for next 7 days
- UI: Step-by-step booking flow, calendar picker, time slots grid""",

        "auth": """
AUTH APP REQUIREMENTS:
- Backend Models: User(id, email, username, hashed_password, created_at)
- Backend Endpoints: POST /auth/register, POST /auth/login, GET /auth/me, POST /auth/logout
- Frontend: Login form, register form, protected dashboard, user profile
- Sample Data: Demo user credentials shown on login page
- UI: Clean auth forms with validation, toggle between login/register""",

        "api": """
API-ONLY REQUIREMENTS:
- Backend: Full REST API with comprehensive endpoints
- Documentation: Detailed API docs via FastAPI /docs
- Frontend: Simple API documentation viewer
- Sample Data: Seeded test data
- Focus: API design, validation, error handling""",
    }
    
    base_guidance = guidance.get(app_type, """
CRUD APP REQUIREMENTS:
- Backend: Standard CRUD endpoints with validation
- Frontend: List, create, edit, delete views
- Sample Data: Realistic mock data
- UI: Clean, functional interface""")
    
    # Add feature-specific additions
    feature_additions = []
    if "Search functionality" in features:
        feature_additions.append("- Include search endpoint (GET /search?q=) and search input in UI")
    if "Filter/sort capability" in features:
        feature_additions.append("- Include filter dropdowns and sort options in list views")
    if "User authentication" in features:
        feature_additions.append("- Include login/register endpoints and auth state in frontend")
    if "Pagination" in features:
        feature_additions.append("- Include pagination (limit/offset) in list endpoints and UI")
    
    if feature_additions:
        base_guidance += "\n\nADDITIONAL FEATURES:\n" + "\n".join(feature_additions)
    
    return base_guidance


# Legacy compatibility
CRUD_APP_PROMPT = get_app_specific_guidance("crud", [])
E_COMMERCE_PROMPT = get_app_specific_guidance("ecommerce", [])
DASHBOARD_PROMPT = get_app_specific_guidance("dashboard", [])


def get_specialized_prompt(app_type: str) -> str:
    """Get specialized prompt additions based on app type."""
    return get_app_specific_guidance(app_type, [])
