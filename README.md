# Research Briefing Agent

A React + FastAPI application with a LangGraph research workflow, PostgreSQL persistence, and email/password accounts. The starter graph is provider-independent and returns a clearly labeled demonstration report until a model and search provider are configured.

## Requirements

- Node.js 20.19+ or 22.12+
- Python 3.12+
- Ollama is optional for the initial scaffold; Docker setup will be added after the app runs locally.

## Start locally

### Start PostgreSQL

From the project root, with Docker Desktop running:

```powershell
docker compose up -d db
```

The local database is configured for development only. It stores data in the `postgres_data` Docker volume.

### Backend

```powershell
cd backend
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

### Frontend (in another terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually http://localhost:5173. Create an account from the sign-in screen. Accounts require a valid email and a password of at least 10 characters.

## Current scope

The current milestone provides account registration/sign-in, JWT-protected API endpoints, PostgreSQL-backed account and research-run storage, and a LangGraph plan → research → evidence review → report flow. Research is currently a demo placeholder; it does not pretend to have searched the web or cite fabricated sources. Next milestones are local-model integration, real web search, durable LangGraph checkpoints, and full application Docker deployment.

The JWT signing secret and local database password are development defaults. Replace them with strong secrets before deploying. Sign-out removes the browser's saved bearer token; tokens are currently kept in local storage for this development milestone.
