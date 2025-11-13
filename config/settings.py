from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # OpenAI
    google_api_key: str
    gemini_model: str
    gemini_temperature: float = 0.0
    embedding_model: str
    
    # Database
    database_url: str
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "interview_system"
    db_user: str = "interview_admin"
    db_password: str = "interview123"
    
    # Vector Store
    vector_store_path: str = "./data/vectorstore"
    
    # Interview Settings
    similarity_threshold: float = 0.8
    top_k_results: int = 3
    pass_threshold: int = 60
    passing_score: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
