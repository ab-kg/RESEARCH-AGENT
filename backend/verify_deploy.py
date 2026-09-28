"""Boot verification for the Railway deployment changes.

Runs the real FastAPI app in-process against a throwaway SQLite database so the
auth flow, the API-vs-SPA routing precedence, and the LLM-missing error path are
all exercised without needing Postgres or a Groq key.
"""
import os
import shutil
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
FRONTEND_DIST = BACKEND.parent / "frontend" / "dist"

# Simulate the Docker layout: the compiled SPA lands in backend/static
static_dir = BACKEND / "static"
if static_dir.exists():
    shutil.rmtree(static_dir)
if FRONTEND_DIST.is_dir():
    shutil.copytree(FRONTEND_DIST, static_dir)
    print(f"[setup] copied SPA -> {static_dir}")
else:
    print("[setup] WARNING: frontend/dist missing, SPA mount will be skipped")

os.environ["DATABASE_URL"] = "sqlite:///./verify.db"
os.environ["JWT_SECRET"] = "verification-secret-not-a-real-one"
os.environ["GROQ_API_KEY"] = ""
os.environ["CORS_ORIGINS"] = "https://fieldnotes.up.railway.app, http://localhost:5173"

import sys

sys.path.insert(0, str(BACKEND))

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}{(' -> ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


# ---------------------------------------------------------------- 1. config
from app.config import Settings  # noqa: E402

print("\n=== 1. DATABASE_URL driver normalisation ===")
# These are the exact shapes Railway / Neon / Supabase / Heroku hand out.
cases = [
    ("postgresql://postgres:pw@postgres.railway.internal:5432/railway", "postgresql+psycopg://"),
    ("postgres://u:p@host:5432/db", "postgresql+psycopg://"),
    ("postgresql+psycopg://fieldnotes:fieldnotes-dev@localhost:5432/fieldnotes", "postgresql+psycopg://"),
    ("postgresql+psycopg2://x:y@z/db", "postgresql+psycopg2://"),
    ("sqlite:///./verify.db", "sqlite:///"),
]
for raw, expected_prefix in cases:
    got = Settings(database_url=raw).database_url
    check(f"normalise {raw[:52]}", got.startswith(expected_prefix), got)

check(
    "psycopg2 would have been selected by bare postgresql://",
    Settings(database_url="postgresql://a:b@c:5432/d").database_url.startswith("postgresql+psycopg://"),
)

origins = Settings(cors_origins="https://a.example.com/ , https://b.example.com").cors_origin_list
check("cors_origin_list parses + strips trailing slash", origins == ["https://a.example.com", "https://b.example.com"], str(origins))

# ---------------------------------------------------------------- 2. app boot
print("\n=== 2. App boot, routes, SPA mount ===")
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: F401,E402

Base.metadata.create_all(engine)

from fastapi import routing

paths = {r.path for r in app.routes if hasattr(r, "path")}
for required in ("/health", "/api/auth/register", "/api/auth/login", "/api/auth/me", "/api/runs"):
    check(f"route {required} registered", required in paths)
# Starlette normalises Mount("/") to path "" rather than "/".
spa_mounts = [r for r in app.routes if isinstance(r, routing.Mount) and r.path == ""]
check("SPA mounted at /", len(spa_mounts) == 1, f"{len(spa_mounts)} root mount(s), {len(paths)} routes total")

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

r = client.get("/health")
check("GET /health", r.status_code == 200 and r.json() == {"status": "ok"}, f"{r.status_code} {r.json()}")

r = client.get("/")
check("GET / serves the React shell", r.status_code == 200 and "<div id=\"root\">" in r.text, f"{r.status_code} len={len(r.text)}")

asset = next((p for p in paths if p.startswith("/assets/")), None)
if asset:
    r = client.get(asset)
    check(f"GET {asset} serves built JS", r.status_code == 200 and "javascript" in r.headers.get("content-type", ""), str(r.status_code))

# The critical ordering property: API routes must not be swallowed by the "/" mount.
r = client.post("/api/runs", json={"question": "a question long enough to pass validation"}, headers={"Authorization": "Bearer nonsense"})
check("POST /api/runs is NOT swallowed by the SPA mount (401, not 404/HTML)", r.status_code == 401, f"{r.status_code} {r.text[:80]}")

# ---------------------------------------------------------------- 3. auth flow
print("\n=== 3. Auth + persistence round trip ===")
r = client.post("/api/auth/register", json={"email": "demo@example.com", "password": "correct-horse-battery"})
check("register returns 200 + token", r.status_code == 200 and "access_token" in r.json(), f"{r.status_code} {r.text[:120]}")
token = r.json().get("access_token", "")
auth = {"Authorization": f"Bearer {token}"}

check("duplicate register rejected with 409", client.post("/api/auth/register", json={"email": "demo@example.com", "password": "correct-horse-battery"}).status_code == 409)
check("short password rejected with 422", client.post("/api/auth/register", json={"email": "x@example.com", "password": "short"}).status_code == 422)
check("bad password rejected with 401", client.post("/api/auth/login", json={"email": "demo@example.com", "password": "wrong-password-here"}).status_code == 401)
check("login with correct password works", client.post("/api/auth/login", json={"email": "demo@example.com", "password": "correct-horse-battery"}).status_code == 200)

r = client.get("/api/auth/me", headers=auth)
check("GET /api/auth/me resolves the user", r.status_code == 200 and r.json()["email"] == "demo@example.com", f"{r.status_code} {r.text[:80]}")
check("GET /api/runs without token is 401", client.get("/api/runs").status_code == 401)

# ---------------------------------------------------------------- 4. graph wiring
print("\n=== 4. LangGraph wiring + missing-Groq error mapping ===")
from app.graph import research_graph  # noqa: E402

check("graph compiled", hasattr(research_graph, "invoke"))
nodes = set(getattr(research_graph, "nodes", {}) or {})
check("expected nodes present", {"plan", "search", "assess", "write"} <= nodes, str(sorted(nodes)))

r = client.post("/api/runs", json={"question": "What is urban heat adaptation?"}, headers=auth)
check(
    "missing GROQ_API_KEY maps to 503 (not 500)",
    r.status_code == 503,
    f"{r.status_code} {r.text[:140]}",
)

check(
    "question shorter than min_length is 422",
    client.post("/api/runs", json={"question": "hi"}, headers=auth).status_code == 422,
)

r = client.get("/api/runs", headers=auth)
check("GET /api/runs returns a list for the user", r.status_code == 200 and isinstance(r.json(), list), f"{r.status_code} {r.text[:80]}")

# ---------------------------------------------------------------- done
engine.dispose()
db_file = BACKEND / "verify.db"
if db_file.exists():
    db_file.unlink()

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} FAILURE(S): " + ", ".join(failures))
    raise SystemExit(1)
print("ALL CHECKS PASSED")
