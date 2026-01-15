"""
Конфигурация Celery для Barber SaaS.

Этот модуль обеспечивает:
- Настройку Celery App
- Настройку брокера сообщений (Redis)
- Настройку периодических задач (Celery Beat)
- Настройку расписания для напоминаний о подписках
"""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

# ==================== Celery App ====================

celery_app = Celery(
    "barber_saas",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    include=[
        "app.tasks.subscription_notifications",
    ]
)

# ==================== Настройки ====================

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# ==================== Celery Beat расписание ====================

# Расписание периодических задач
celery_app.conf.beat_schedule = {
    # Проверка подписок и отправка напоминаний (ежедневно в 00:00 UTC)
    "check-subscriptions-7-days": {
        "task": "app.tasks.subscription_notifications.send_reminder_7_days_before",
        "schedule": crontab(hour=0, minute=0),  # Каждый день в 00:00 UTC
    },
    # Отправка напоминаний за 3 дня (ежедневно в 00:00 UTC)
    "check-subscriptions-3-days": {
        "task": "app.tasks.subscription_notifications.send_reminder_3_days_before",
        "schedule": crontab(hour=0, minute=0),  # Каждый день в 00:00 UTC
    },
    # Отправка напоминаний за 1 день (ежедневно в 00:00 UTC)
    "check-subscriptions-1-day": {
        "task": "app.tasks.subscription_notifications.send_reminder_1_day_before",
        "schedule": crontab(hour=0, minute=0),  # Каждый день в 00:00 UTC
    },
    # Отправка напоминаний об окончании (ежедневно в 00:00 UTC)
    "check-subscriptions-expiration": {
        "task": "app.tasks.subscription_notifications.send_reminder_expiration",
        "schedule": crontab(hour=0, minute=0),  # Каждый день в 00:00 UTC
    },
    # Отправка напоминаний о неоплате (каждые 3 дня в 00:00 UTC)
    "check-subscriptions-payment-reminder": {
        "task": "app.tasks.subscription_notifications.send_payment_reminder",
        "schedule": crontab(hour=0, minute=0, day_of_week=[0, 2, 4]),  # Каждые 2 дня (Пн, Ср, Пт) в 00:00 UTC
    },
}

# ==================== Регистрация задач ====================

# Импортируем все задачи для регистрации в Celery
from app.tasks import subscription_notifications

# Примечание: Задачи автоматически регистрируются через @shared_task декоратор

