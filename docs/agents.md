# Multi-Agent Design

## Agents & Responsibilities

1. **UI Agent**
   - Input: app spec, design tokens, templates.
   - Output: React components/pages with Tailwind classes.
   - Rules: use component library (Button, Input, Modal, Card), limit edits to targeted files.

2. **Logic Agent**
   - Input: UI routes, API schema.
   - Output: API client + React Query hooks + form validation helpers.
   - Rules: strict typing, services layer separation.

3. **Backend Agent**
   - Input: spec + data model intents.
   - Output: FastAPI routers, SQLModel models, auth flows.
   - Rules: include validation, tests, guardrails for SQLi/XSS.

4. **Debugger Agent**
   - Input: generated files + logs.
   - Output: Minimal patches after AST parsing.
   - Tools: `libcst`, `ast`, `esprima`, `ruff`, `black`, `mypy`.

5. **Build Agent**
   - Input: final project tree.
   - Output: Zip artifacts, Docker image, preview build metadata.

6. **Deploy Agent**
   - Input: artifacts + env config.
   - Output: Deployments to Netlify/Vercel/Expo + Docker Compose for local.

## Memory / State

- Project manifest of screens/endpoints.
- Component registry for dedupe.
- Dependency graph (component → API usage).
- Version hash map.
- SQLite table stores per-project state, easily swapped for Postgres.

## Safety & Validation

- AST validation before writes.
- Linter + unit tests enforced per agent.
- Secrets always pulled from env, never hard-coded.
