"""
Central configuration for CareerPilot AI.

IMPORTANT: We call load_dotenv() explicitly at import time BEFORE
pydantic-settings reads the environment. This guarantees the .env
file is loaded even in edge cases where pydantic-settings env_file
loading is skipped (e.g. when running uvicorn with --reload on Windows).
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from functools import lru_cache

# ---- Force load .env from backend/ directory immediately ----
_backend_dir = Path(__file__).parent.parent   # careerpilot-ai/backend/
_env_file = _backend_dir / ".env"
if _env_file.exists():
    load_dotenv(dotenv_path=_env_file, override=True)
else:
    # Also try current working directory (for when uvicorn is run from project root)
    _cwd_env = Path.cwd() / "backend" / ".env"
    if _cwd_env.exists():
        load_dotenv(dotenv_path=_cwd_env, override=True)
    else:
        load_dotenv(override=True)   # last resort: search upward from cwd


class Settings(BaseSettings):
    # LLM
    google_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "gemini"
    gemini_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"

    # DB
    database_url: str = "sqlite:///./careerpilot.db"

    # Vector store
    chroma_persist_dir: str = "./chroma_db"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "careerpilot-ai"

    # Notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # Jobs
    job_search_api_key: str = ""
    jsearch_api_key: str = ""

    # App
    app_env: str = "development"
    secret_key: str = "change_me_in_production"

    class Config:
        env_file = str(_env_file)
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
