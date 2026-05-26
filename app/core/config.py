"""
Configuration management using pydantic-settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # BrightData API
    BRIGHTDATA_API_KEY: str
    
    # MinIO Object Storage
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "fairprice-evidence"
    
    # Application
    APP_NAME: str = "FairPrice Watchdog"
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()

# Made with Bob
