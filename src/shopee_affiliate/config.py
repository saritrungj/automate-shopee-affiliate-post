from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    secret_key: str = "dev"
    database_url: str = "sqlite:///./generated/local.db"
    redis_url: str = "redis://localhost:6379/0"

    llm_gateway: str = "openclaw"
    openclaw_base_url: str = "http://127.0.0.1:7331"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    llm_fallback_mode: str = "mock"
    affiliate_disclosure_hashtag: str = "#โฆษณา"

    generated_dir: Path = Field(default=Path("generated"))
    prompt_dir: Path = Field(default=Path("prompts"))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    return settings

