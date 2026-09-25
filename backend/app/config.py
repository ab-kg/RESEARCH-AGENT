from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fieldnotes:fieldnotes-dev@localhost:5432/fieldnotes"
    jwt_secret: str = "local-only-change-this-secret-before-deploying"
    access_token_minutes: int = 60 * 24 * 7

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
