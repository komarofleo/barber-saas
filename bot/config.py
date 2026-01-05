"""Конфигурация Telegram бота"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "329621295").split(",") if id.strip()]

# Database
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "autoservice_db")
DB_USER = os.getenv("DB_USER", "autoservice_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# App Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

# Work Schedule
WORK_START_TIME = os.getenv("WORK_START_TIME", "09:00")
WORK_END_TIME = os.getenv("WORK_END_TIME", "18:00")
SLOT_DURATION = int(os.getenv("SLOT_DURATION", "30"))
ENABLE_MASTER_SPECIALIZATION = os.getenv("ENABLE_MASTER_SPECIALIZATION", "false").lower() == "true"

# Notifications
REMINDER_DAY_BEFORE_TIME = os.getenv("REMINDER_DAY_BEFORE_TIME", "18:00")
REMINDER_HOUR_BEFORE = os.getenv("REMINDER_HOUR_BEFORE", "true").lower() == "true"
NOTIFY_ADMIN_DELAY_MINUTES = int(os.getenv("NOTIFY_ADMIN_DELAY_MINUTES", "5"))
WORK_ORDER_TIME = os.getenv("WORK_ORDER_TIME", "08:00")

# Database URL
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"









