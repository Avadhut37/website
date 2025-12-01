# Recommended Project Tree

```
istudiox/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ models.py
│  │  ├─ db.py
│  │  ├─ routers/
│  │  │  ├─ auth.py
│  │  │  ├─ projects.py
│  │  ├─ services/
│  │  │  ├─ generator.py
│  │  ├─ ai_engine.py
│  ├─ work/ (generated artifacts)
│  ├─ Dockerfile
│  ├─ requirements.txt
├─ frontend/
│  ├─ package.json
│  ├─ src/
│  │  ├─ main.jsx
│  │  ├─ pages/
│  │  │  ├─ Builder.jsx
│  │  │  ├─ Home.jsx
│  │  ├─ components/
│  ├─ tailwind.config.js
├─ mobile/
│  ├─ expo/ (Expo project placeholder)
├─ agents/
│  ├─ prompts/
│  │  ├─ ui_agent.txt
│  │  ├─ backend_agent.txt
│  │  ├─ logic_agent.txt
│  │  ├─ debugger_agent.txt
│  │  ├─ build_agent.txt
│  │  ├─ deploy_agent.txt
├─ infra/
│  ├─ docker-compose.yml
├─ docs/
│  ├─ architecture.md
│  ├─ hardening_checklist.md
│  ├─ howto_deploy.md
│  ├─ mobile_starter.md
│  ├─ project_structure.md
```
