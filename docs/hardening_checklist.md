# Engineering Hardening Checklist

1. **AST Validation Pipeline**
   - Parse backend files with `ast`/`libcst`; parse frontend files with `esprima` or `acorn`.
   - Reject invalid code before it hits the repo; invoke Debugger Agent automatically.
2. **Templates-First Generation**
   - Seed agents with reusable templates (UI components, routers, db models) to maintain consistency.
3. **Component Registry & Memory**
   - Track components, props, and dependencies; dedupe by hashing file contents.
4. **Automated Tests**
   - Generate unit tests for backend/agents and Playwright E2E for frontend.
   - Block deploys unless `pytest` + `npm run test` + `playwright test` succeed.
5. **Security Layer**
   - Input validation, rate limits, sanitized code snippets, and strict env var usage for secrets.
6. **Versioning & Incremental Edits**
   - Maintain file hash history; apply minimal diffs instead of full rewrites.
7. **CI Preview Deployments**
   - Use Vercel/Netlify preview URLs per PR; expire previews automatically.
8. **Monitoring & Observability**
   - Free-tier Sentry for exceptions; Prometheus + Grafana stack for metrics.
9. **Fallback LLM Strategy**
   - Orchestrator tries primary model, then fallback; cache common generation outputs.
10. **Human-in-the-loop Review**
    - Provide a review UI (diff viewer) so users approve/modify agent output before export.
