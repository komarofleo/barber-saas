"""Конфигурация приложения"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    # База данных
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "autoservice_db")
    DB_USER: str = os.getenv("DB_USER", "autoservice_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    # Web
    SECRET_KEY: str = os.getenv("WEB_SECRET_KEY", "")
    HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WEB_PORT", "8000"))
    CORS_ORIGINS: List[str] = os.getenv("WEB_CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Юкасса (Платежная система)
    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SECRET_KEY: str = os.getenv("YOOKASSA_SECRET_KEY", "")
    YOOKASSA_API_URL: str = os.getenv("YOOKASSA_API_URL", "https://api.yookassa.ru/v3")
    YOOKASSA_RETURN_URL: str = os.getenv("YOOKASSA_RETURN_URL", "https://autoservice-saas.com/success")
    YOOKASSA_WEBHOOK_URL: str = os.getenv("YOOKASSA_WEBHOOK_URL", "https://autoservice-saas.com/api/public/webhooks/yookassa")
    
    class Config:
        env_file = ".env"


settings = Settings()









