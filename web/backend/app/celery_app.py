"""Конфигурация Celery"""
from celery import Celery

from app.config import settings

_broker = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

celery_app = Celery(
    "barber",
    broker=_broker,
    backend=_broker,
    include=["app.tasks.notifications", "app.tasks.subscription_notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Расписание Celery Beat (напоминания записей + подписки)
from celery_beat import beat_schedule  # noqa: E402

celery_app.conf.beat_schedule = beat_schedule

