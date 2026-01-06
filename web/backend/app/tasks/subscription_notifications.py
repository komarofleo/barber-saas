"""
Задачи для отправки уведомлений о подписках для SaaS архитектуры.

Этот модуль содержит Celery задачи для:
- Напоминаний за 7 дней до окончания подписки
- Напоминаний за 1 день до окончания подписки
- Уведомлений об истечении подписки
- Уведомлений о неактивных подписках
- Уведомлений о просроченных платежах
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from celery import shared_task
from aiogram import Bot

from app.database import get_db
from app.models.public_models import (
    Company,
    Subscription,
    Payment,
    Plan
)
from app.models.shared_models import Notification
from app.config import settings

logger = logging.getLogger(__name__)


# ==================== Helper функции ====================

_bot_instance = None

def get_bot():
    """Получить экземпляр бота (lazy initialization)"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=settings.BOT_TOKEN)
    return _bot_instance


async def get_companies_with_expiring_subscriptions(
    db: AsyncSession,
    days_before: int
) -> List[tuple]:
    """
    Получить компании с истекающими подписками.
    
    Args:
        db: Сессия базы данных
        days_before: Количество дней до истечения
        
    Returns:
        Список кортежей (Company, Subscription, days_remaining)
    """
    target_date = date.today() + timedelta(days=days_before)
    result = await db.execute(
        select(Company, Subscription)
        .join(Subscription, Company.id == Subscription.company_id)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(
            and_(
                Company.is_active == True,
                Company.subscription_status == "active",
                Company.admin_telegram_id.isnot(None),
                Subscription.status == "active",
                Subscription.end_date <= target_date,
                Subscription.end_date >= date.today()
            )
        )
    )
    companies_with_subs = result.all()
    
    # Добавляем информацию о днях до истечения
    result_list = []
    for company, subscription in companies_with_subs:
        days_remaining = (subscription.end_date - date.today()).days
        result_list.append((company, subscription, days_remaining))
    
    return result_list


async def get_companies_with_expired_subscriptions(
    db: AsyncSession
) -> List[tuple]:
    """
    Получить компании с истекшими подписками.
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Список кортежей (Company, Subscription, days_expired)
    """
    yesterday = date.today() - timedelta(days=1)
    result = await db.execute(
        select(Company, Subscription)
        .join(Subscription, Company.id == Subscription.company_id)
        .where(
            and_(
                Company.is_active == True,
                Company.subscription_status == "active",
                Company.admin_telegram_id.isnot(None),
                Subscription.end_date < yesterday  # Истекла вчера или раньше
            )
        )
    )
    companies_with_subs = result.all()
    
    # Добавляем информацию о днях с момента истечения
    result_list = []
    for company, subscription in companies_with_subs:
        days_expired = (date.today() - subscription.end_date).days
        result_list.append((company, subscription, days_expired))
    
    return result_list


async def get_companies_with_inactive_subscriptions(
    db: AsyncSession
) -> List[tuple]:
    """
    Получить компании с неактивными подписками (block/expired).
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Список кортежей (Company, Subscription)
    """
    result = await db.execute(
        select(Company, Subscription)
        .join(Subscription, Company.id == Subscription.company_id)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(
            and_(
                Company.is_active == True,
                Company.admin_telegram_id.isnot(None),
                Subscription.status.in_(["blocked", "expired"])
            )
        )
    )
    companies_with_subs = result.all()
    
    return companies_with_subs


async def get_failed_payments(
    db: AsyncSession
) -> List[tuple]:
    """
    Получить неудачные платежи за последние 7 дней.
    
    Args:
        db: Сессия базы данных
        
    Returns:
        Список кортежей (Company, Payment)
    """
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    result = await db.execute(
        select(Company, Payment)
        .join(Payment, Company.id == Payment.company_id)
        .where(
            and_(
                Company.is_active == True,
                Company.admin_telegram_id.isnot(None),
                Payment.status == "failed",
                Payment.created_at >= seven_days_ago
            )
        )
    )
    companies_with_payments = result.all()
    
    return companies_with_payments


# ==================== Celery задачи ====================

@shared_task
def send_reminder_7_days_before():
    """
    Отправить напоминания за 7 дней до окончания подписки.
    
    Запускается ежедневно в 9:00.
    """
    logger.info("Начало задачи напоминаний за 7 дней")
    
    try:
        asyncio.run(_send_reminder_7_days_before())
        logger.info("Задача напоминаний за 7 дней завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка в задаче напоминаний за 7 дней: {e}", exc_info=True)
        raise


@shared_task
def send_reminder_day_before():
    """
    Отправить напоминания за 1 день до окончания подписки.
    
    Запускается ежедневно в 9:00.
    """
    logger.info("Начало задачи напоминаний за 1 день")
    
    try:
        asyncio.run(_send_reminder_day_before())
        logger.info("Задача напоминаний за 1 день завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка в задаче напоминаний за 1 день: {e}", exc_info=True)
        raise


@shared_task
def send_expired_notification():
    """
    Отправить уведомления об истекших подписках.
    
    Запускается ежедневно в 9:00.
    """
    logger.info("Начало задачи уведомлений об истечении")
    
    try:
        asyncio.run(_send_expired_notification())
        logger.info("Задача уведомлений об истечении завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка в задаче уведомлений об истечении: {e}", exc_info=True)
        raise


@shared_task
def send_inactive_subscription_notification():
    """
    Отправить уведомления о неактивных подписках.
    
    Запускается ежедневно в 9:00.
    """
    logger.info("Начало задачи уведомлений о неактивных подписках")
    
    try:
        asyncio.run(_send_inactive_subscription_notification())
        logger.info("Задача уведомлений о неактивных подписках завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка в задаче уведомлений о неактивных подписках: {e}", exc_info=True)
        raise


@shared_task
def send_failed_payment_notification():
    """
    Отправить уведомления о неудачных платежах.
    
    Запускается ежедневно в 9:00.
    """
    logger.info("Начало задачи уведомлений о неудачных платежах")
    
    try:
        asyncio.run(_send_failed_payment_notification())
        logger.info("Задача уведомлений о неудачных платежах завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка в задаче уведомлений о неудачных платежах: {e}", exc_info=True)
        raise


# ==================== Асинхронные функции ====================

async def _send_reminder_7_days_before():
    """Внутренняя функция для отправки напоминаний за 7 дней"""
    async for db in get_db():
        companies_with_subs = await get_companies_with_expiring_subscriptions(db, 7)
        
        if not companies_with_subs:
            logger.info("Нет компаний с подписками, истекающими через 7 дней")
            return
        
        logger.info(f"Найдено {len(companies_with_subs)} компаний с подписками, истекающими через 7 дней")
        bot = get_bot()
        
        for company, subscription, days_remaining in companies_with_subs:
            try:
                # Формируем сообщение
                expiration_date = subscription.end_date.strftime("%d.%m.%Y")
                plan_name = subscription.plan.name if subscription.plan else "Тариф"
                plan_price = f"{subscription.plan.price_monthly} ₽/мес" if subscription.plan else ""
                
                text = f"""⚠️ Напоминание о подписке

💼 Компания: {company.name}

📋 Ваша подписка истекает через {days_remaining} дн.

📊 Подписка:
• План: {plan_name} ({plan_price})
• Дата окончания: {expiration_date}

💰 Для продления подписки, пожалуйста:
1. Войдите в админ-панель
2. Перейдите в раздел "Подписки"
3. Выберите подходящий план
4. Оплатите через Юкассу

🔗 Админ-панель: https://autoservice-saas.com/super-admin/companies/{company.id}

⚠️ Если подписка истечет, создание новых записей будет ограничено."""
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=company.admin_telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                
                logger.info(f"Напоминание за 7 дней отправлено компании {company.id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания за 7 дней компании {company.id}: {e}")
                
                # Сохраняем в историю уведомлений
                notification = Notification(
                    user_id=None,  # Для SaaS не привязано к конкретному пользователю
                    booking_id=None,
                    notification_type="subscription_reminder_7d",
                    message=text,
                    is_sent=False,
                    error_message=str(e),
                    sent_at=datetime.utcnow()
                )
                db.add(notification)


async def _send_reminder_day_before():
    """Внутренняя функция для отправки напоминаний за 1 день"""
    async for db in get_db():
        companies_with_subs = await get_companies_with_expiring_subscriptions(db, 1)
        
        if not companies_with_subs:
            logger.info("Нет компаний с подписками, истекающими через 1 день")
            return
        
        logger.info(f"Найдено {len(companies_with_subs)} компаний с подписками, истекающими через 1 день")
        bot = get_bot()
        
        for company, subscription, days_remaining in companies_with_subs:
            try:
                # Формируем сообщение
                expiration_date = subscription.end_date.strftime("%d.%m.%Y")
                plan_name = subscription.plan.name if subscription.plan else "Тариф"
                
                text = f"""🚨 Срочно! Подписка истекает завтра

💼 Компания: {company.name}

📋 Ваша подписка истекает {expiration_date}!

📊 Подписка:
• План: {plan_name}
• Статус: {subscription.status}

💰 Для продления подписки, пожалуйста:
1. Войдите в админ-панель
2. Перейдите в раздел "Подписки"
3. Выберите подходящий план
4. Оплатите через Юкассу

🔗 Админ-панель: https://autoservice-saas.com/super-admin/companies/{company.id}

⚠️ После истечения подписки функция создания записей будет отключена."""
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=company.admin_telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                
                logger.info(f"Напоминание за 1 день отправлено компании {company.id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания за 1 день компании {company.id}: {e}")
                
                # Сохраняем в историю уведомлений
                notification = Notification(
                    user_id=None,
                    booking_id=None,
                    notification_type="subscription_reminder_1d",
                    message=text,
                    is_sent=False,
                    error_message=str(e),
                    sent_at=datetime.utcnow()
                )
                db.add(notification)


async def _send_expired_notification():
    """Внутренняя функция для отправки уведомлений об истечении"""
    async for db in get_db():
        companies_with_subs = await get_companies_with_expired_subscriptions(db)
        
        if not companies_with_subs:
            logger.info("Нет компаний с истекшими подписками")
            return
        
        logger.info(f"Найдено {len(companies_with_subs)} компаний с истекшими подписками")
        bot = get_bot()
        
        for company, subscription, days_expired in companies_with_subs:
            try:
                # Формируем сообщение
                expiration_date = subscription.end_date.strftime("%d.%m.%Y")
                days_text = f"{days_expired} дн. назад"
                plan_name = subscription.plan.name if subscription.plan else "Тариф"
                
                text = f"""❌ Подписка истекла

💼 Компания: {company.name}

⏰ Ваша подписка истекла {expiration_date} ({days_text})

📊 Подписка:
• План: {plan_name}
• Статус: {subscription.status}

⚠️ Функция создания записей отключена!

💰 Для восстановления работы системы:
1. Войдите в админ-панель
2. Перейдите в раздел "Подписки"
3. Выберите и оплатите план
4. После оплаты подписка будет активирована

🔗 Админ-панель: https://autoservice-saas.com/super-admin/companies/{company.id}

📞 При возникновении вопросов, обратитесь в поддержку: support@autoservice-saas.com"""
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=company.admin_telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                
                logger.info(f"Уведомление об истечении отправлено компании {company.id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления об истечении компании {company.id}: {e}")
                
                # Сохраняем в историю уведомлений
                notification = Notification(
                    user_id=None,
                    booking_id=None,
                    notification_type="subscription_expired",
                    message=text,
                    is_sent=False,
                    error_message=str(e),
                    sent_at=datetime.utcnow()
                )
                db.add(notification)


async def _send_inactive_subscription_notification():
    """Внутренняя функция для отправки уведомлений о неактивных подписках"""
    async for db in get_db():
        companies_with_subs = await get_companies_with_inactive_subscriptions(db)
        
        if not companies_with_subs:
            logger.info("Нет компаний с неактивными подписками")
            return
        
        logger.info(f"Найдено {len(companies_with_subs)} компаний с неактивными подписками")
        bot = get_bot()
        
        for company, subscription in companies_with_subs:
            try:
                # Формируем сообщение
                plan_name = subscription.plan.name if subscription.plan else "Тариф"
                status_text = "заблокирована" if subscription.status == "blocked" else "истекла"
                
                text = f"""⚠️ Неактивная подписка

💼 Компания: {company.name}

📊 Ваша подписка {status_text}:
• План: {plan_name}
• Статус: {subscription.status}
• Дата окончания: {subscription.end_date.strftime("%d.%m.%Y") if subscription.end_date else "Не указана"}

⚠️ Функция создания записей может быть ограничена!

💰 Для восстановления работы системы:
1. Войдите в админ-панель
2. Перейдите в раздел "Подписки"
3. Выберите и оплатите план
4. После оплаты подписка будет активирована

🔗 Админ-панель: https://autoservice-saas.com/super-admin/companies/{company.id}

📞 При возникновении вопросов, обратитесь в поддержку: support@autoservice-saas.com"""
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=company.admin_telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                
                logger.info(f"Уведомление о неактивной подписке отправлено компании {company.id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о неактивной подписке компании {company.id}: {e}")
                
                # Сохраняем в историю уведомлений
                notification = Notification(
                    user_id=None,
                    booking_id=None,
                    notification_type="subscription_inactive",
                    message=text,
                    is_sent=False,
                    error_message=str(e),
                    sent_at=datetime.utcnow()
                )
                db.add(notification)


async def _send_failed_payment_notification():
    """Внутренняя функция для отправки уведомлений о неудачных платежах"""
    async for db in get_db():
        companies_with_payments = await get_failed_payments(db)
        
        if not companies_with_payments:
            logger.info("Нет неудачных платежей за последние 7 дней")
            return
        
        logger.info(f"Найдено {len(companies_with_payments)} неудачных платежей")
        bot = get_bot()
        
        for company, payment in companies_with_payments:
            try:
                # Формируем сообщение
                payment_date = payment.created_at.strftime("%d.%m.%Y %H:%M")
                amount_text = f"{payment.amount} ₽" if payment.amount else "0 ₽"
                
                text = f"""💰 Платеж не прошел

💼 Компания: {company.name}

💳 Детали платежа:
• Дата: {payment_date}
• Сумма: {amount_text}
• Статус: {payment.status}
• Описание: {payment.description or "Не указано"}

⚠️ Платеж не был успешным!

💰 Возможные причины:
1. Недостаточно средств на карте
2. Ошибка в платежной системе
3. Отказ банка
4. Технические проблемы

🔧 Для повторной оплаты:
1. Войдите в админ-панель
2. Перейдите в раздел "Подписки" или "Платежи"
3. Нажмите "Повторить платеж"

🔗 Админ-панель: https://autoservice-saas.com/super-admin/companies/{company.id}

📞 При возникновении вопросов, обратитесь в поддержку: support@autoservice-saas.com"""
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=company.admin_telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                
                logger.info(f"Уведомление о неудачном платеже отправлено компании {company.id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления о неудачном платеже компании {company.id}: {e}")
                
                # Сохраняем в историю уведомлений
                notification = Notification(
                    user_id=None,
                    booking_id=None,
                    notification_type="payment_failed",
                    message=text,
                    is_sent=False,
                    error_message=str(e),
                    sent_at=datetime.utcnow()
                )
                db.add(notification)

