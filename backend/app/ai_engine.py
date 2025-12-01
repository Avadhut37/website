"""Lightweight wrapper around whichever LLM backend you prefer."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Dict


MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5-coder")


def call_local_ollama(prompt: str) -> str:
    """Invoke an Ollama model via CLI."""
    try:
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except FileNotFoundError:
        return None  # CLI missing
    except subprocess.TimeoutExpired:
        return None
    return result.stdout or result.stderr


def generate_fallback_files(spec: dict) -> Dict[str, str]:
    """Generate a meaningful starter project when LLM is unavailable."""
    app_name = spec.get("raw", spec.get("name", "MyApp"))
    
    return {
        "README.md": f"""# {app_name}

Generated project scaffold.

## Structure
- `backend/` - FastAPI backend
- `frontend/` - React frontend

## Getting Started

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
""",
        "backend/main.py": f'''"""FastAPI backend for {app_name}."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="{app_name}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {{"message": "Welcome to {app_name}"}}

@app.get("/health")
def health():
    return {{"status": "ok"}}
''',
        "backend/requirements.txt": "fastapi>=0.110.0\nuvicorn[standard]>=0.27.0\n",
        "frontend/package.json": json.dumps({
            "name": app_name.lower().replace(" ", "-"),
            "version": "0.1.0",
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
  <title>{app_name}</title>
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
  server: { port: 3000 }
});
''',
        "frontend/src/main.jsx": f'''import React from 'react';
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

export default function App() {{
  const [message, setMessage] = useState('Loading...');

  useEffect(() => {{
    axios.get('http://localhost:8000/')
      .then(res => setMessage(res.data.message))
      .catch(() => setMessage('Backend not available'));
  }}, []);

  return (
    <div style={{{{ padding: '2rem', fontFamily: 'system-ui' }}}}>
      <h1>{app_name}</h1>
      <p>{{message}}</p>
    </div>
  );
}}
''',
    }


def call_llm_and_generate(spec: dict) -> Dict[str, str]:
    """Generate project files using LLM or fallback."""
    prompt = (
        "Create a minimal FastAPI + React project based on this spec json:\n"
        f"{json.dumps(spec, indent=2)}\n"
        "Return ONLY a valid JSON object mapping file paths to file contents. "
        "No markdown, no explanation, just JSON."
    )
    
    raw = call_local_ollama(prompt)
    
    if raw:
        # Try to extract JSON from the response
        try:
            files = json.loads(raw)
            if isinstance(files, dict) and len(files) > 0:
                return files
        except json.JSONDecodeError:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                try:
                    files = json.loads(json_match.group())
                    if isinstance(files, dict) and len(files) > 0:
                        return files
                except json.JSONDecodeError:
                    pass
    
    # Fallback to template generation
    return generate_fallback_files(spec)
