# Research Briefing Agent

A React + FastAPI research app using LangGraph, PostgreSQL, and Groq's hosted GPT-OSS model. The workflow plans searches, looks up Wikipedia references, reviews evidence, and writes a source-linked briefing.

## Requirements

- Node.js 20.19+ or 22.12+
- Python 3.12+
- A Groq API key from [Groq Console](https://console.groq.com/keys)
- Docker Desktop for local PostgreSQL

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

Before starting the backend, open `backend/.env` and set `GROQ_API_KEY` to your newly generated key. The default model is `openai/gpt-oss-20b`. Keep the key in this backend file; never put it in the React app or commit it.

Open http://127.0.0.1:8000/docs.

### Frontend (in another terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually http://localhost:5173. Create an account from the sign-in screen. Accounts require a valid email and a password of at least 10 characters.

## Current scope

The current milestone provides account registration/sign-in, JWT-protected API endpoints, PostgreSQL-backed account and research-run storage, and a LangGraph workflow that uses Groq for planning, evidence review, and writing. Wikipedia is the current no-key search source. Free-tier limits vary by model and account; for a demo run, keep the workflow concise. LangGraph checkpoints and full application container deployment are future milestones.

The JWT signing secret and local database password are development defaults. Replace them with strong secrets before deploying. Sign-out removes the browser's saved bearer token; tokens are currently kept in local storage for this development milestone.

## UI screenshots

### AI-generated briefing — dark mode

![Fieldnotes research briefing in dark mode](assets/Screenshot%202026-09-25%20151300.png)

### AI-generated briefing — light mode

![Fieldnotes research briefing in light mode](assets/Screenshot%202026-09-25%20151539.png)
