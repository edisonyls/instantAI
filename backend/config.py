import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration"""

    # API Settings
    PROJECT_NAME: str = "InstantAI"

    # Database Settings
    DATABASE_URL: str = "postgresql://instantai:instantai_password@localhost:5432/instantai"

    # Ollama Settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma2:2b"

    # Document Processing Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Vector Embeddings Settings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # RAG Settings
    SIMILARITY_THRESHOLD: float = 0.1
    MAX_RETRIEVED_CHUNKS: int = 5

    # File Storage Settings
    UPLOAD_DIR: str = "uploads"
    TEMP_DIR: str = "temp"

    # CORS Settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000"]

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create necessary directories
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.TEMP_DIR, exist_ok=True)


settings = Settings()
