import os
from typing import Literal
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Global City AI Governance RAG & MCP Hub (Vertex AI Search)"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # GCP Settings
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "tdf-ocf")
    GCP_REGION: str = os.getenv("GCP_REGION", "asia-east1")

    # Vertex AI Search & Agent Builder Settings
    VERTEX_DATA_STORE_ID: str = os.getenv("VERTEX_DATA_STORE_ID", "city-governance-datastore")
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "global")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "tdf-ocf-city-governance-docs")

    # LLM Settings
    GEMINI_CHAT_MODEL: str = Field("gemini-3.7-flash", validation_alias=AliasChoices("GEMINI_CHAT_MODEL", "GEMINI_MODEL"))
    GEMINI_CLEANER_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_LOCATION: str = "global"
    GEMINI_PROVIDER: Literal["vertex", "developer"] = "vertex"
    GEMINI_API_KEY: str = Field("", repr=False)
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    GEMINI_TEMPERATURE: float = 1.0
    GEMINI_THINKING_BUDGET: int | None = None
    GEMINI_THINKING_LEVEL: str | None = None
    GEMINI_TIMEOUT_MS: int = 120000
    CONTEXT_INPUT_TOKENS: int = 16000
    CONTEXT_HISTORY_TOKENS: int = 3000
    CONTEXT_EVIDENCE_TOKENS: int = 9000
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    LOGIN_ALLOWED_EMAILS: list[str] = []
    AUTH_SESSION_SECRET: str = Field("", repr=False)
    AUTH_SESSION_SECONDS: int = 3600
    ADMIN_EMAILS: list[str] = []
    EDITOR_EMAILS: list[str] = []
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    DATABASE_URL: str = Field("sqlite:///./data/governance.db", repr=False)
    ARTIFACT_STORAGE_DIR: str = "./data/artifacts"
    ARTIFACT_GCS_BUCKET: str = ""
    ARTIFACT_TTL_HOURS: int = 24
    JOBS_PER_USER_HOUR: int = 10
    JOB_MAX_INPUT_CHARS: int = 100000
    WORKER_ENABLED: bool = True
    CLOUD_TASKS_QUEUE: str = ""
    WORKER_SERVICE_ACCOUNT: str = ""
    APP_ORIGIN: str = "http://localhost:8080"
    WORKER_LEGACY_ORIGINS: list[str] = []
    CHUNK_INDEX_ENABLED: bool = False
    CHUNK_DATA_STORE_ID: str = ""
    CHUNK_SEARCH_ENGINE_ID: str = ""
    SOFFICE_BIN: str = "soffice"
    FONT_DIR: str = "/usr/share/fonts/truetype/governance"


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
