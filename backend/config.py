"""Configuration for RunbookMind loaded from environment variables and .env."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

class Settings(BaseSettings):
    hindsight_api_key: str = ""
    hindsight_base_url: str = "https://api.hindsight.vectorize.io"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    bank_id: str = "runbookmind-acme-sre"
    hindsight_ui_url: str = "https://app.vectorize.io"
    use_reflect_in_analyze: bool = True
    backend_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Backwards compatibility exports
HINDSIGHT_API_KEY = settings.hindsight_api_key
HINDSIGHT_BASE_URL = settings.hindsight_base_url
GROQ_API_KEY = settings.groq_api_key
BANK_ID = settings.bank_id
