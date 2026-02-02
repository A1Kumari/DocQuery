# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    # ===================================
    # APPLICATION SETTINGS
    # ===================================
    APP_NAME: str = "ClaimCheck - Insurance Validation Engine"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # ===================================
    # API SETTINGS
    # ===================================
    API_PREFIX: str = "/api"
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # ===================================
    # LLM PROVIDER SELECTION
    # ===================================
    LLM_PROVIDER: str = "groq"  # Options: "groq", "google", "ollama"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    
    # ===================================
    # GROQ (Primary LLM) - FREE & FAST
    # ===================================
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # ===================================
    # GOOGLE (Backup - Optional)
    # ===================================
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: str = "gemini-2.0-flash-lite"
    
    # ===================================
    # PINECONE (Vector Store)
    # ===================================
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: str = "docquery"
    PINECONE_NAMESPACE: str = "default"
    
    # ===================================
    # NEO4J (Graph Database) - NEW
    # ===================================
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    
    # ===================================
    # EMBEDDINGS
    # ===================================
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # ===================================
    # DOCUMENT PROCESSING
    # ===================================
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    DEFAULT_CHUNK_SIZE: int = 1000
    DEFAULT_CHUNK_OVERLAP: int = 200
    
    # Aliases for compatibility
    MAX_CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # ===================================
    # POLICY PROCESSING - NEW
    # ===================================
    EXTRACTION_MODEL: str = "groq"  # Which LLM to use for extraction
    
    # ===================================
    # CLAIM PROCESSING - NEW
    # ===================================
    FRAUD_THRESHOLD: float = 0.5      # Score above this triggers review
    AUTO_APPROVE_THRESHOLD: float = 0.9  # Confidence for auto-approval
    
    # ===================================
    # FILE STORAGE
    # ===================================
    DATA_DIR: str = "data"
    POLICIES_DIR: str = "data/policies"
    CLAIMS_DIR: str = "data/claims"
    
    # ===================================
    # RATE LIMITING
    # ===================================
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # ===================================
    # COMPUTED PROPERTIES
    # ===================================
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    @property
    def is_neo4j_configured(self) -> bool:
        """Check if Neo4j is configured with non-default values."""
        return self.NEO4J_PASSWORD != "password"
    
    # ===================================
    # PYDANTIC CONFIG
    # ===================================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env


# ===================================
# SINGLETON PATTERN
# ===================================
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()