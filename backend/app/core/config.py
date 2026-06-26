from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    data_sources_db_url: str = os.getenv("DATA_SOURCES_DB_URL", "sqlite:///./data_sources.db")
    query_history_db_url: str = os.getenv("QUERY_HISTORY_DB_URL", "sqlite:///./query_history.db")
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
    langgraph_memory_db_uri: str = os.getenv("LANGGRAPH_MEMORY_DB_URI", "")
    langgraph_run_migrations_on_start: bool = os.getenv("LANGGRAPH_RUN_MIGRATIONS_ON_START", "false").lower() == "true"

    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # App Settings
    APP_NAME: str = "DataPilot AI"
    DEBUG: bool = False
    LLM_PROVIDER: str = "groq"  # mock | groq | openrouter | gemini

    # Security
    APPROVAL_TTL_SECONDS: int = int(os.getenv("APPROVAL_TTL_SECONDS", "3600"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
