# iStudiox (Starter)

Production-ready blueprint for a multi-agent AI App Builder featuring FastAPI backend, Vite + Tailwind frontend, Expo mobile starter, and agent prompt library.

## Quick Start

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Docker Compose (backend + redis + worker):

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Key Docs

- `docs/architecture.md` — system overview, diagram, flow.
- `docs/agents.md` — multi-agent responsibilities.
- `docs/hardening_checklist.md` — AST validation, security, monitoring.
- `docs/howto_deploy.md` — local dev, testing, deployment tips.
- `docs/mobile_starter.md` — Expo setup guide.
- `docs/project_structure.md` — recommended folder tree.

## Agent Prompts

See `agents/prompts/*.txt` for UI, Logic, Backend, Debugger, Build, Deploy agent templates. Each prompt enforces JSON outputs (`file_path -> content`) and AST-safe requirements.

## Next Steps

1. Configure secrets in `backend/.env` (copy from `.env.example`).
2. Replace `call_local_ollama` with your preferred LLM runner or HTTP endpoint.
3. Implement AST validator + Debugger Agent integration before enabling writeback.
4. Add CI (GitHub Actions) to run backend/frontend tests and trigger Deploy Agent previews.
