from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DiagnoAI"
    app_version: str = "0.2.0"
    app_env: str = "local"
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model_name: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL_NAME")
    allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8501",
        ],
        alias="ALLOW_ORIGINS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("allow_origins", mode="before")
    @classmethod
    def parse_allow_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
