import os
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
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
