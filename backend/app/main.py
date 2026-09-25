from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.graph import research_graph
from app.llm import LLMConfigurationError, LLMProviderError
from app.models import ResearchRun, User
from app.security import create_access_token, get_current_user, hash_password, verify_password

app = FastAPI(title="Fieldnotes Research API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=10, max_length=128)


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=1000)


def serialize_run(run: ResearchRun) -> dict:
    return {
        "id": run.id,
        "question": run.question,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
        "report": run.report,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register")
def register(credentials: Credentials, db: Session = Depends(get_db)) -> dict:
    email = credentials.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "email": user.email}


@app.post("/api/auth/login")
def login(credentials: Credentials, db: Session = Depends(get_db)) -> dict:
    email = credentials.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect")
    return {"access_token": create_access_token(user.id), "token_type": "bearer", "email": user.email}


@app.get("/api/auth/me")
def current_account(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email}


@app.get("/api/runs")
def list_runs(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    runs = db.scalars(
        select(ResearchRun).where(ResearchRun.user_id == user.id).order_by(ResearchRun.created_at.desc())
    ).all()
    return [serialize_run(run) for run in runs]


@app.post("/api/runs")
def create_run(
    request: ResearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    try:
        result = research_graph.invoke({"question": request.question.strip()})
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Wikipedia search is temporarily unavailable. Please retry.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="The research workflow could not complete. Please retry.") from exc

    run = ResearchRun(
        user_id=user.id,
        question=request.question.strip(),
        status="completed",
        report=result["report"],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return serialize_run(run)


@app.get("/api/runs/{run_id}")
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    run = db.scalar(select(ResearchRun).where(ResearchRun.id == run_id, ResearchRun.user_id == user.id))
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    return serialize_run(run)
