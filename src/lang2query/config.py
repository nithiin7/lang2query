"""Configuration settings for the Lang2Query system."""

from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
