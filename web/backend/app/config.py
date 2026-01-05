"""Конфигурация приложения"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    # Web
    SECRET_KEY: str = os.getenv("WEB_SECRET_KEY", "")
    HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WEB_PORT", "8000"))
    CORS_ORIGINS: List[str] = os.getenv("WEB_CORS_ORIGINS", "http://localhost:3000").split(",")

    class Config:
        env_file = ".env"


settings = Settings()









