# Local Dev, Testing, and Deployment

## Local Development

1. Backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
2. Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Docker Compose (backend + redis + worker):
   ```bash
   docker compose -f infra/docker-compose.yml up --build
   ```

## Testing Strategy

- Backend: `pytest` (ensure generator + routers covered) and `ruff` + `mypy` for lint/type checks.
- Frontend: `npm run test` (Vitest/Jest) plus Playwright E2E for Builder flow.
- Agents: Use snapshot tests for prompts; run AST validator on generated files before packaging.

## Deployment Options

- **Backend**: Render, Railway, Fly.io, or Docker image on any VPS. Expose `uvicorn` behind Caddy/Nginx.
- **Frontend**: Vercel/Netlify static deploy from `npm run build` output.
- **Mobile**: Expo EAS for managed builds; share preview QR directly with users.
- **CI/CD**: GitHub Actions pipeline that runs tests, builds artifacts, uploads Build Agent zips, and triggers Deploy Agent for previews.

## Environment & Secrets

- Store secrets in `.env` (never commit). Required vars: `DATABASE_URL`, `SECRET_KEY`, `REDIS_URL`, provider tokens.
- Use GitHub Actions secrets + Vercel/Render dashboards for production values.
