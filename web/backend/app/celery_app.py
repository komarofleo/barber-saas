"""Конфигурация Celery"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "autoservice",
    broker=f"redis://redis:6379/0",
    backend=f"redis://redis:6379/0",
    include=["app.tasks.notifications"]
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

# Расписание периодических задач
celery_app.conf.beat_schedule = {
    "send-reminders-day-before": {
        "task": "app.tasks.notifications.send_reminder_day_before_task",
        "schedule": 3600.0,  # Каждый час
    },
    "send-reminders-hour-before": {
        "task": "app.tasks.notifications.send_reminder_hour_before_task",
        "schedule": 300.0,  # Каждые 5 минут
    },
    "send-work-orders-to-masters": {
        "task": "app.tasks.notifications.send_work_orders_to_masters_task",
        "schedule": {"hour": 8, "minute": 0},  # Каждый день в 08:00
    },
    "notify-admin-new-bookings": {
        "task": "app.tasks.notifications.notify_admin_new_bookings_task",
        "schedule": 300.0,  # Каждые 5 минут
    },
}



