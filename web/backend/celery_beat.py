"""
Конфигурация Celery Beat для Barber SaaS.

Задачи:
- напоминания клиентам о записи (за день / за час)
- напоминания по подпискам SaaS
- лист-наряды / уведомления админам
"""

from celery.schedules import crontab

# Импорт задач регистрирует их в Celery app
from app.tasks.notifications import (  # noqa: F401
    notify_admin_new_bookings_task,
    send_reminder_3_hours_before_task,
    send_reminder_day_before_task,
    send_work_orders_to_masters_task,
)
from app.tasks.subscription_notifications import (  # noqa: F401
    send_payment_reminder,
    send_reminder_1_day_before,
    send_reminder_3_days_before,
    send_reminder_7_days_before,
    send_reminder_expiration,
)

# ==================== Подписки SaaS ====================

schedule_reminder_7_days = {
    "task": "app.tasks.subscription_notifications.send_reminder_7_days_before",
    "schedule": crontab(hour=9, minute=0),
    "options": {"expires": 86400},
}

schedule_reminder_3_days = {
    "task": "app.tasks.subscription_notifications.send_reminder_3_days_before",
    "schedule": crontab(hour=9, minute=5),
    "options": {"expires": 86400},
}

schedule_reminder_1_day_sub = {
    "task": "app.tasks.subscription_notifications.send_reminder_1_day_before",
    "schedule": crontab(hour=9, minute=10),
    "options": {"expires": 86400},
}

schedule_expired_notification = {
    "task": "app.tasks.subscription_notifications.send_reminder_expiration",
    "schedule": crontab(hour=9, minute=15),
    "options": {"expires": 86400},
}

schedule_payment_reminder = {
    "task": "app.tasks.subscription_notifications.send_payment_reminder",
    "schedule": crontab(hour=10, minute=0),
    "options": {"expires": 86400},
}

# ==================== Записи клиентов ====================

# Каждые 15 мин: внутри задачи сверяем reminder_day_before_time компании
schedule_reminder_1_day_booking = {
    "task": "app.tasks.notifications.send_reminder_day_before_task",
    "schedule": crontab(minute="*/15"),
    "options": {"expires": 900},
}

# Каждые 5 мин 06–21: окно «через час»
schedule_reminder_hour_booking = {
    "task": "app.tasks.notifications.send_reminder_3_hours_before_task",
    "schedule": crontab(minute="*/5", hour="6-21"),
    "options": {"expires": 600},
}

schedule_work_orders = {
    "task": "app.tasks.notifications.send_work_orders_to_masters_task",
    "schedule": crontab(hour=8, minute=0),
    "options": {"expires": 86400},
}

schedule_admin_new_bookings = {
    "task": "app.tasks.notifications.notify_admin_new_bookings_task",
    "schedule": crontab(minute="*/10"),
    "options": {"expires": 3600},
}

beat_schedule = {
    "subscription-reminder-7-days": schedule_reminder_7_days,
    "subscription-reminder-3-days": schedule_reminder_3_days,
    "subscription-reminder-1-day": schedule_reminder_1_day_sub,
    "subscription-expired": schedule_expired_notification,
    "subscription-payment-reminder": schedule_payment_reminder,
    "booking-reminder-1-day": schedule_reminder_1_day_booking,
    "booking-reminder-hour": schedule_reminder_hour_booking,
    "work-orders": schedule_work_orders,
    "admin-new-bookings": schedule_admin_new_bookings,
}
