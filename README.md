# Fieldnotes — Research Briefing Agent

A full-stack research app that turns a question into a source-linked briefing. A
LangGraph workflow plans the research, gathers evidence, judges whether it is good
enough, and writes a cited summary — every factual claim traceable to a numbered source.

**Live demo:** https://research-agent2-production.up.railway.app/

Stack: React + TypeScript, FastAPI, LangGraph, PostgreSQL, and Groq's hosted
GPT-OSS 20B model. Deployed on Railway.

---

## How the research workflow works

The agent is a state machine with a conditional loop. It is not a single
prompt — each stage does one job and the evidence stage can send the workflow
back to gather more.

```
                 ┌──────────────────────────────────────┐
                 │                                      │
START ──► plan ──► search ──► assess ──────────────────► write ──► END
                             ▲                           │
                             └───────────────────────────┘
                        needs_more and attempt < 2
```

| Stage | What it does | LLM? |
| --- | --- | --- |
| `plan` | Turns the question into a 3-step plan and up to 3 Wikipedia search queries | yes |
| `search` | Queries the Wikipedia API, strips HTML from snippets, deduplicates by URL, caps at 8 sources | no |
| `assess` | Short-circuits if ≥ 5 sources were found; otherwise asks the model whether coverage is sufficient and proposes follow-up queries | sometimes |
| `write` | Writes the briefing from the snippets alone, citing `[S1]`–`[S8]` inline | yes |

Two design decisions worth noting:

**Loop termination is guaranteed.** Each pass through `search` increments
`attempt`, and the router refuses to loop once `attempt` reaches 2. Worst case is
three search queries, two follow-ups, then a write — so a run costs 2–3 LLM calls
and at most 8 HTTP calls to Wikipedia.

**Evidence is treated as hostile input.** Retrieved snippets are fed to the model
inside prompts that explicitly mark them as untrusted data with instructions to
ignore any directives found inside. The writer is told to cite only the supplied
IDs and never invent a citation. This is the standard mitigation for prompt
injection through retrieved text — it raises the bar rather than closing the hole
completely.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, lucide-react, hand-written CSS |
| API | FastAPI, Pydantic v2 |
| Orchestration | LangGraph (used standalone — no LangChain) |
| LLM | Groq `openai/gpt-oss-20b`, called over the OpenAI-compatible API |
| Database | PostgreSQL 17, SQLAlchemy 2.0, Alembic |
| Auth | JWT (HS256), Argon2 password hashing via `pwdlib` |
| Deploy | Docker multi-stage build on Railway |

LangGraph is used purely as an orchestrator. The LLM is a plain `httpx` call in
`backend/app/llm.py` that asks for JSON mode and strips code fences before
parsing — no LangChain abstraction anywhere, so there is no version coupling
between the two libraries.

---

## Project structure

```
├── Dockerfile              # multi-stage: Node builds the SPA, Python serves it
├── railway.toml            # builder + healthcheck configuration
├── compose.yaml            # local PostgreSQL only
├── backend/
│   ├── entrypoint.sh       # validates DATABASE_URL, waits for Postgres, migrates, serves
│   ├── requirements.txt
│   └── app/
│       ├── graph.py        # the LangGraph state machine
│       ├── llm.py          # Groq client + JSON coercion
│       ├── main.py         # FastAPI routes, also serves the built SPA
│       ├── models.py       # SQLAlchemy User / ResearchRun
│       ├── security.py     # JWT + Argon2
│       ├── database.py     # engine + session dependency
│       └── config.py       # pydantic-settings
└── frontend/src/App.tsx    # entire UI
```

---

## Running locally

**Requirements:** Python 3.12+, Node 20.19+ or 22.12+, Docker Desktop.

```powershell
# 1. PostgreSQL
docker compose up -d db

# 2. Backend
cd backend
Copy-Item .env.example .env        # then add your GROQ_API_KEY
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# 3. Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and create an account. API docs are at
http://127.0.0.1:8000/docs.

There is also a self-contained smoke test that boots the app in-process against a
throwaway SQLite database and exercises the auth flow, routing, and error
mapping without needing Postgres or an API key:

```powershell
cd backend
python verify_deploy.py
```

---

## Environment variables

`backend/.env` for local development; the same keys as service variables in
production.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | PostgreSQL connection string. **Must use `postgresql+psycopg://`** — see below |
| `JWT_SECRET` | yes | Signing key for access tokens |
| `GROQ_API_KEY` | yes | Key from [Groq Console](https://console.groq.com/keys) |
| `GROQ_MODEL` | no | Defaults to `openai/gpt-oss-20b` |
| `CORS_ORIGINS` | no | Comma-separated browser origins. Unnecessary when the SPA is served by the API |

### The `psycopg3` gotcha

Managed Postgres providers (Railway, Neon, Supabase, Heroku, Fly) hand out a bare
`postgresql://` URL. SQLAlchemy interprets that as **psycopg2**, but this project
installs psycopg3 only — so a naive deploy dies with
`ModuleNotFoundError: No module named 'psycopg2'`.

`config.py` normalises the scheme on the way in:

```python
@field_validator("database_url")
@classmethod
def _use_psycopg3_driver(cls, value: str) -> str:
    if value.startswith(("postgresql://", "postgres://")):
        return "postgresql+psycopg://" + value.split("://", 1)[1]
    return value
```

One validator, and it works for every major provider.

---

## Deploying to Railway

Two services: the app container and Railway's PostgreSQL.

**1. Create the database.** Project canvas → **+ New** → **PostgreSQL** template.
Railway creates a service named `Postgres` with a persistent volume attached.

**2. Deploy the app.** **+ New** → **GitHub repo** → select this repository.
Set the **Root Directory to `/`** — the Dockerfile sits at the repo root and needs
both `backend/` and `frontend/` in the build context.

**3. Set variables** on the app service. In the value field for `DATABASE_URL`,
use the autocomplete dropdown and select the Postgres service, which writes
`${{Postgres.DATABASE_URL}}` for you:

```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
JWT_SECRET   = <32 random bytes, hex encoded>
GROQ_API_KEY = gsk_...
GROQ_MODEL   = openai/gpt-oss-20b
```

> Variable edits are **staged** in Railway. They do not take effect until you
> deploy the staged change.

**4. Generate a domain.** Settings → Networking → **Public Networking** →
Generate Domain, target port **8080**.

**5. Deploy.** The logs should read:

```
Waiting for postgres at postgres.railway.internal ...
Postgres reachable after 1 attempt(s).
Starting uvicorn on 0.0.0.0:8080
```

### Why one container serves both

The Dockerfile builds the React bundle with Node, then copies it into the Python
image where FastAPI serves it as static files from the same origin as the API.
The frontend already called relative `/api` paths, so this removes CORS
preflights and the need for a second service or a reverse proxy. Routes are
registered before the static mount, so API endpoints always take precedence over
the SPA.

`entrypoint.sh` fails fast with an actionable message if `DATABASE_URL` is missing
or still points at localhost, and retries the database connection for up to 60
seconds — app containers can start before the database is ready to accept
connections.

---

## Security notes

- **Never commit `backend/.env`.** It is gitignored; it holds a real API key.
- **`JWT_SECRET` must be set in production.** The default in `config.py` is
  published in this repository, so anyone could mint a token for any account.
  Seal the variable in Railway so it is not visible in the dashboard.
- **Tokens currently live in `localStorage`**, which is readable by any injected
  script. An `httpOnly` cookie plus CSRF protection would be the next step.
- **There is no rate limiting** on `POST /api/runs`, so an authenticated user can
  currently exhaust the Groq quota quickly.

---

## Known limitations

- `POST /api/runs` is **synchronous** — it blocks for 10–60 seconds while the
  graph runs, so the UI shows a spinner rather than live progress. A background
  job with polling, or streaming node updates over SSE, would be the fix.
- **The graph has no checkpointer.** LangGraph is compiled without one, so runs
  cannot resume after a crash, cannot be replayed, and support no human-in-the-loop
  interrupts. Adding `langgraph-checkpoint-postgres` would enable all three.
- **Search is Wikipedia only.** No key needed, but it is a narrow source.
- `GET /api/runs` loads every saved report to build the sidebar list, which will
  slow down as runs accumulate.

---

## Screenshots

### AI-generated briefing — dark mode

![Fieldnotes research briefing in dark mode](assets/Screenshot%202026-09-25%20151300.png)

### AI-generated briefing — light mode

![Fieldnotes research briefing in light mode](assets/Screenshot%202026-09-25%20151539.png)

### Sign-in — dark mode

![Fieldnotes sign-in page in dark mode](assets/Screenshot%202026-09-25%20151321.png)
