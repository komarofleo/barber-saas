"""Конфигурация Celery"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "barber",
    broker=f"redis://redis:6379/0",
    backend=f"redis://redis:6379/0",
    include=["app.tasks.notifications", "app.tasks.subscription_notifications"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
)

# Импортируем расписание из celery_beat
from celery_beat import beat_schedule



