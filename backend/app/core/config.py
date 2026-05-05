from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATA_SOURCES_DB_URL: str = os.getenv("DATA_SOURCES_DB_URL", "sqlite:///./data_sources.db")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    APPROVAL_TTL_SECONDS: int = int(os.getenv("APPROVAL_TTL_SECONDS", "3600"))
    
    # LLM API Keys
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    
    # App Settings
    APP_NAME: str = "DataPilot AI"
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

settings = Settings()