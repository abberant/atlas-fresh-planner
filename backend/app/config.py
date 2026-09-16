"""Application settings, read from environment variables with safe defaults."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = "data/Atlas_Fresh_Production_Commercial_Data.xlsx"


class Settings(BaseSettings):
    """Runtime configuration. The app must work with no .env file at all."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_path: str = DEFAULT_DATA_PATH
    ai_provider: str = "none"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    ai_timeout_seconds: int = 20

    @property
    def resolved_data_path(self) -> Path:
        """DATA_PATH is relative to the repository root unless it is absolute."""
        candidate = Path(self.data_path)
        return candidate if candidate.is_absolute() else REPO_ROOT / candidate

    @property
    def ai_configured(self) -> bool:
        if self.ai_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.ai_provider == "gemini":
            return bool(self.gemini_api_key)
        if self.ai_provider == "ollama":
            return bool(self.ollama_url)
        return False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
