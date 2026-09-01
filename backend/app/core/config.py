import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Global City AI Governance RAG & MCP Hub"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # GCP Settings
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "tdf-ocf")
    GCP_REGION: str = os.getenv("GCP_REGION", "asia-east1")

    # Database (PostgreSQL + pgvector)
    # When deployed on Cloud Run, use Cloud SQL Unix Domain Socket if INSTANCE_CONNECTION_NAME is set
    INSTANCE_CONNECTION_NAME: str = os.getenv("INSTANCE_CONNECTION_NAME", "tdf-ocf:asia-east1:city-rag-sql-dev")
    DB_USER: str = os.getenv("DB_USER", "rag_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "GovRAG2026SecurePass!")
    DB_NAME: str = os.getenv("DB_NAME", "city_governance")
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    
    # Embedding Model (Multilingual aligned 100+ languages)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    EMBEDDING_DIMENSION: int = 768

    # LLM Settings
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Chunking Defaults
    DEFAULT_CHUNK_SIZE: int = 500  # Words / Tokens
    DEFAULT_CHUNK_OVERLAP: int = 80

    @property
    def database_url(self) -> str:
        # Check if running in Cloud Run with Cloud SQL socket
        socket_path = f"/cloudsql/{self.INSTANCE_CONNECTION_NAME}"
        if os.path.exists(socket_path):
            return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@/{self.DB_NAME}?host={socket_path}"
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
