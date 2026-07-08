from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


def _get_project_root() -> str:
    """Get the project root directory (d:/datapilot-ai-4)."""
    # config.py is in backend/app/core/, so go up 3 levels
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _abs_sqlite_url(relative_url: str) -> str:
    """Convert a relative or absolute path to an absolute sqlite URL.
    
    Handles paths like sqlite:///./data_sources.db or sqlite:///data_sources.db
    and converts them to absolute paths based on the project root.
    """
    if relative_url.startswith("sqlite://"):
        # Extract the path portion
        actual_path = relative_url[len("sqlite://"):]
        if actual_path.startswith("/"):
            actual_path = actual_path[1:]  # Remove leading slash for Windows paths
        if not os.path.isabs(actual_path):
            # Make it absolute relative to project root
            project_root = _get_project_root()
            actual_path = os.path.join(project_root, actual_path)
        return f"sqlite:///{actual_path}"
    return relative_url


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    data_sources_db_url: str = _abs_sqlite_url(os.getenv("DATA_SOURCES_DB_URL", "sqlite:///./data_sources.db"))
    query_history_db_url: str = _abs_sqlite_url(os.getenv("QUERY_HISTORY_DB_URL", "sqlite:///./query_history.db"))
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
    langgraph_memory_db_uri: str = os.getenv("LANGGRAPH_MEMORY_DB_URI", "")
    langgraph_run_migrations_on_start: bool = os.getenv("LANGGRAPH_RUN_MIGRATIONS_ON_START", "false").lower() == "true"

    # LLM API Keys (runtime-configurable, defaults to .env values)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    TOGETHER_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    
    # Default model (used when no model is specified in runtime settings)
    DEFAULT_LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_PROVIDER: str = "groq"

    # LangSmith Tracing & Evaluation
    LANGCHAIN_TRACING_V2: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "datapilot-ai")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # App Settings
    APP_NAME: str = "DataPilot AI"
    DEBUG: bool = False
    # Default LLM provider (used when no provider is specified in runtime settings)
    DEFAULT_LLM_PROVIDER: str = "groq"

    # Security
    APPROVAL_TTL_SECONDS: int = int(os.getenv("APPROVAL_TTL_SECONDS", "3600"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# MUST run before any langsmith/langchain imports — the SDK caches env var
# state at import time. Setting them here ensures the tracers pick them up.
if settings.LANGCHAIN_API_KEY and settings.LANGCHAIN_TRACING_V2:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGCHAIN_API_KEY)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGCHAIN_PROJECT or "datapilot-ai")
    os.environ.setdefault("LANGSMITH_ENDPOINT", settings.LANGCHAIN_ENDPOINT or "https://api.smith.langchain.com")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)