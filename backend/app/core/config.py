import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os


def _get_project_root() -> str:
    """Get the project root directory."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _abs_sqlite_url(relative_url: str) -> str:
    """Convert a relative or absolute path to an absolute sqlite URL.

    Handles paths like sqlite:///./data_sources.db or sqlite:///data_sources.db
    and converts them to absolute paths based on the project root.
    """
    if relative_url.startswith("sqlite://"):
        actual_path = relative_url[len("sqlite://"):]
        if actual_path.startswith("/"):
            actual_path = actual_path[1:]
        if not os.path.isabs(actual_path):
            project_root = _get_project_root()
            actual_path = os.path.join(project_root, actual_path.lstrip("./").lstrip(".\\"))
        return f"sqlite:///{actual_path}"
    return relative_url


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = ""
    data_sources_db_url: str = "sqlite:///./data_sources.db"
    query_history_db_url: str = "sqlite:///./query_history.db"
    encryption_key: str = ""
    langgraph_memory_db_uri: str = ""
    langgraph_run_migrations_on_start: bool = False

    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    TOGETHER_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # Default model
    DEFAULT_LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_PROVIDER: str = "groq"

    # LangSmith Tracing & Evaluation
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "datapilot-ai"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # App Settings
    APP_NAME: str = "DataPilot AI"
    DEBUG: bool = False
    DEFAULT_LLM_PROVIDER: str = "groq"

    # Chat Memory
    CHAT_DB_URL: str = "sqlite:///./data/chat.db"
    CHAT_HISTORY_LIMIT: int = 20

    # Security
    APPROVAL_TTL_SECONDS: int = 3600

    # PostgreSQL (optional, overrides SQLite for production)
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Application Insights (Azure)
    APPLICATIONINSIGHTS_CONNECTION_STRING: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_postgres_url(self) -> str | None:
        if self.POSTGRES_HOST and self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return None

    def get_resolved_database_url(self) -> str:
        pg_url = self.get_postgres_url()
        if pg_url:
            return pg_url
        return self.DATABASE_URL or "sqlite+aiosqlite:///./dev.db"


settings = Settings()
logger = logging.getLogger(__name__)
logger.info("Settings loaded: provider=%s, debug=%s, database=%s",
            settings.LLM_PROVIDER or settings.DEFAULT_LLM_PROVIDER,
            settings.DEBUG,
            "postgresql" if settings.get_postgres_url() else "sqlite")

# Resolve SQLite paths for data_sources and query_history
if settings.data_sources_db_url.startswith("sqlite:///"):
    settings.data_sources_db_url = _abs_sqlite_url(settings.data_sources_db_url)
if settings.query_history_db_url.startswith("sqlite:///"):
    settings.query_history_db_url = _abs_sqlite_url(settings.query_history_db_url)
if settings.CHAT_DB_URL.startswith("sqlite:///"):
    settings.CHAT_DB_URL = _abs_sqlite_url(settings.CHAT_DB_URL)

# MUST run before any langsmith/langchain imports — the SDK caches env var
# state at import time. Setting them here ensures the tracers pick them up.
if settings.LANGCHAIN_API_KEY and settings.LANGCHAIN_TRACING_V2:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_API_KEY", settings.LANGCHAIN_API_KEY)
    os.environ.setdefault("LANGSMITH_PROJECT", settings.LANGCHAIN_PROJECT or "datapilot-ai")
    os.environ.setdefault("LANGSMITH_ENDPOINT", settings.LANGCHAIN_ENDPOINT or "https://api.smith.langchain.com")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)

# If POSTGRES credentials are provided, use them as the primary DATABASE_URL
pg_url = settings.get_postgres_url()
if pg_url:
    settings.DATABASE_URL = pg_url