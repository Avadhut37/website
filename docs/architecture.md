# iStudiox Architecture

Modular multi-agent platform with central orchestrator, persistent memory, AST validator, and safe deploy pipeline.

## High-Level Topology

```
			   +----------------------+
			   |   Web / Mobile UI    |
			   |  (React / Expo RN)   |
			   +----------+-----------+
					  |
				  HTTPS | WebSocket (preview)
					  |
			   +----------v-----------+
			   |     API Gateway      |  <- FastAPI (auth, routing, rate limits)
			   +----------+-----------+
					  |
	  +-----------------------+------------------------+
	  |                       |                        |
+-------v------+        +-------v-------+        +-------v-------+
| Persistency  |        |  Orchestrator |        |  Preview & CI |
| (DB + Files) |        |  (Agents CMD) |        |  Build Agent  |
| - SQLite /   |        | - Agent router|        |  (Zip, deploy)|
|   Postgres   |        | - Memory DB   |        | - Netlify/Vercel|
+-------+------+        +-------+-------+        +-------+-------+
	  |                          |                        |
 +------v------+           +-------v------+         +-------v------+
 |   Storage   |           |  Agents Pool  |         |  Deployer    |
 | Supabase /  |           |  - UI Agent   |         | (Netlify,    |
 | local FS    |           |  - Logic Agent|         |  Vercel, Expo)|
 +-------------+           |  - Backend    |         +---------------+
				   |  - Debugger   |
				   |  - Build      |
				   +---------------+

```

## Request Flow

1. User types a spec such as "Create a Zomato clone with wallet" in the Builder UI.
2. API Gateway (FastAPI) validates/authenticates request, stores spec in Memory DB, and writes project stub to SQLModel database.
3. Orchestrator schedules agents in sequence:
   - **UI Agent**: generates React/Tailwind components.
   - **Backend Agent**: produces FastAPI models, routers, and DB migrations.
   - **Logic Agent**: builds client-side state and API clients.
4. AST Validator parses the generated code; Debugger Agent patches syntax/type issues.
5. Build Agent bundles the code into a zip, generates Dockerfiles, and can trigger preview deployments (Netlify/Vercel/Expo).
6. Preview links feed into web iframe or Expo mobile preview for live testing.

## Core Subsystems

- **Memory Layer**: SQLite/Redis storing project manifests, component registry, dependency map, and version hashes.
- **Agent Pool**: Reusable prompt templates for UI, Logic, Backend, Debugger, Build, Deploy agents.
- **Safety Railings**: AST validation, linting (Black/Ruff/ESLint), unit tests, rate limiting, and environment-based secret loading.
- **Preview & Deploy**: Build Agent packages zipped artifacts; Deploy Agent pushes to Netlify/Vercel (web) or Expo (mobile) via CI pipelines.
