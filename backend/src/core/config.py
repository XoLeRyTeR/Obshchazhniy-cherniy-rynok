from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    database_url: SecretStr
    jwt_secret: SecretStr
    access_token_ttl: int = Field(default=604800, ge=60)
    cors_origins: list[str] = ["http://localhost:8081", "http://127.0.0.1:8081"]
    media_dir: Path = Path("uploads")
    media_base_url: str = "http://localhost:8000/media"
    readiness_timeout: float = Field(default=3, gt=0, le=30)
    auth_rate_limit: int = Field(default=20, ge=1)
    auth_rate_window: int = Field(default=60, ge=1)

    @field_validator("jwt_secret")
    @classmethod
    def secret_length(cls, value):
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must have at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_url(cls, value):
        if not value.get_secret_value().startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg")
        return value

