"""Configuration management for the chat service."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    openai_api_key: str
    sentry_dsn: Optional[str] = "https://691b07f94dbbca9171ae9995b25dc778@o88872.ingest.us.sentry.io/4509997697073152"
    sentry_environment: str = "development"
    
    # OpenTelemetry OTLP configuration (for hybrid instrumentation)
    sentry_otlp_endpoint: Optional[str] = None
    sentry_public_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
