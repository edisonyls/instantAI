import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and configuration"""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "InstantAI"

    # Database Settings
    CHROMA_DB_PATH: str = "data/chroma_db"

    # Ollama Settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma2:2b"  # Default model

    # Document Processing Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    CHUNK_SIZE: int = 1000  # Characters per chunk
    CHUNK_OVERLAP: int = 200  # Overlap between chunks

    # Vector Database Settings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_DB_COLLECTION: str = "documents"

    # RAG Settings
    MAX_CONTEXT_LENGTH: int = 4000  # Maximum context length for RAG
    SIMILARITY_THRESHOLD: float = 0.1  # Minimum similarity for context retrieval (lowered for better recall)
    MAX_RETRIEVED_CHUNKS: int = 5  # Maximum number of chunks to retrieve

    # File Storage Settings
    UPLOAD_DIR: str = "uploads"
    TEMP_DIR: str = "temp"

    # Security Settings
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS Settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000"]

    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create necessary directories
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.TEMP_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.CHROMA_DB_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)


settings = Settings()
