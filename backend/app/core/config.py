import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    langsmith_api_key: str = os.getenv("LANGSMITH_API_KEY", "")
    langsmith_endpoint: str = os.getenv(
        "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
    )
    langsmith_project: str = os.getenv("LANGSMITH_PROJECT", "")
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
    data_sources_db_url: str = os.getenv("DATA_SOURCES_DB_URL", "")


settings = Settings()
