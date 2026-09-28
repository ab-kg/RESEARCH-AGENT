from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fieldnotes:fieldnotes-dev@localhost:5432/fieldnotes"
    jwt_secret: str = "local-only-change-this-secret-before-deploying"
    access_token_minutes: int = 60 * 24 * 7
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3_driver(cls, value: str) -> str:
        """Managed Postgres providers (Railway, Neon, Supabase, Heroku, Fly) hand out a
        bare `postgresql://` URL, which SQLAlchemy maps to psycopg2. This project installs
        psycopg3 only, so rewrite the scheme to the explicit psycopg3 dialect."""
        if value.startswith(("postgresql://", "postgres://")):
            return "postgresql+psycopg://" + value.split("://", 1)[1]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
