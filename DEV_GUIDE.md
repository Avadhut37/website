# Development Guide

## Quick Start

### Run Entire Project (Backend + Frontend)
```bash
npm run dev
```

This single command starts:
- **Backend** (FastAPI): http://localhost:8000
- **Frontend** (React/Vite): http://localhost:5173

## Available Commands

### Development
- `npm run dev` - Start both backend and frontend concurrently
- `npm run dev:backend` - Start only backend
- `npm run dev:frontend` - Start only frontend

### Installation
- `npm run install:all` - Install all dependencies (backend + frontend)

### Testing
- `npm test` - Run backend tests
- `npm run test:watch` - Run tests in watch mode

### Build
- `npm run build` - Build frontend for production

## API Endpoints

### Backend API
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

### Key Endpoints
- `POST /api/v1/ai/preview` - Generate code preview
- `GET /api/v1/ai/status` - Check AI engine status
- `GET /api/v1/ai/models` - List available models

## Project Structure

```
/workspaces/website/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── main.py       # FastAPI app entry
│   │   ├── ai/           # AI engine & agents
│   │   ├── routers/      # API endpoints
│   │   └── core/         # Config & utilities
│   ├── tests/            # Backend tests
│   └── requirements.txt
├── frontend/             # React frontend
│   ├── src/
│   │   ├── pages/        # Page components
│   │   └── components/   # Reusable components
│   └── package.json
└── package.json          # Root package (monorepo)
```

## AI Providers Status

✅ **Gemini** (PRIMARY): 1500 free/day - UI/Text generation
✅ **Groq** (CODE): 14,400 free/day - Fast code generation
✅ **Cerebras** (REASONING): ~500 free/day - Ultra-fast reasoning
✅ **OpenRouter** (BACKUP): 50 free/day - Multiple models

## Environment Variables

All configuration is in `backend/.env`:
- AI API keys (Gemini, Groq, Cerebras, OpenRouter)
- Database settings
- CORS origins
- Rate limiting

## Tech Stack

### Backend
- **Framework**: FastAPI 0.110+
- **Language**: Python 3.12+
- **AI**: Multi-provider (Gemini, Groq, Cerebras, OpenRouter)
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Testing**: pytest with async support

### Frontend
- **Framework**: React 18
- **Bundler**: Vite 5
- **Styling**: Tailwind CSS
- **HTTP**: Axios
- **State**: React Query

## Async Architecture

The backend uses a fully asynchronous architecture:
- All AI providers use `httpx.AsyncClient`
- Multi-agent system is fully async
- Non-blocking API endpoints
- Concurrent request handling

## Development Tips

1. **Backend auto-reloads** on file changes (via uvicorn --reload)
2. **Frontend hot-reloads** on file changes (via Vite HMR)
3. **API proxy**: Frontend proxies `/api/*` to backend automatically
4. **CORS**: Already configured for local development

## Troubleshooting

### Backend won't start
```bash
cd backend
/workspaces/website/.venv/bin/pip install -r requirements.txt
```

### Frontend won't start
```bash
cd frontend
npm install
```

### Port already in use
- Backend: Change port in `package.json` dev:backend script
- Frontend: Change port in `frontend/vite.config.js`

### Tests failing
```bash
cd backend
/workspaces/website/.venv/bin/pytest tests/ -v
```

## Production Deployment

See `docs/howto_deploy.md` for production deployment instructions.

---
*Last updated: December 2, 2025*
