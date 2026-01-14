"""
Celery задачи для напоминаний о подписках и обработки webhook от Юкассы.

Этот модуль обеспечивает:
- Асинхронную отправку напоминаний о подписках
- Периодическую проверку статуса подписок
- Автоматическое обновление статуса подписок
- Отправку уведомлений через Telegram Bot API
- Обработку webhook от Юкассы
"""
import logging
from datetime import date, timedelta, datetime
from typing import List, Optional

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_async_session_maker
from app.models.public_models import Company, Subscription, Plan
from web.backend.app.api.bot_manager import get_bot_manager

logger = logging.getLogger(__name__)


# ==================== Helper функции ====================

async def get_active_companies() -> List[Company]:
    """
    Получить список всех активных компаний.
    
    Returns:
        Список активных компаний
    """
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        result = await session.execute(
            select(Company).where(
                and_(
                    Company.is_active == True,
                    Company.telegram_bot_token.isnot(None)
                )
            )
        )
        companies = result.scalars().all()
    
    logger.info(f"Найдено {len(companies)} активных компаний")
    return companies


async def get_company_subscription(session: AsyncSession, company_id: int) -> Optional[Subscription]:
    """
    Получить текущую подписку компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
    
    Returns:
        Объект подписки или None
    """
    result = await session.execute(
        select(Subscription)
        .where(Subscription.company_id == company_id)
        .order_by(Subscription.start_date.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    if subscription:
        logger.info(f"Подписка компании {company_id}: статус={subscription.status}, окончание={subscription.end_date}")
    
    return subscription


async def update_company_can_create_bookings(session: AsyncSession, company_id: int, can_create: bool) -> None:
    """
    Обновить флаг can_create_bookings компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        can_create: Может ли создавать записи
    
    Returns:
        None
    """
    result = await session.execute(
            select(Company).where(Company.id == company_id)
        )
    company = result.scalar_one_or_none()
    
    if company:
        company.can_create_bookings = can_create
        await session.commit()
        
        logger.info(f"Компания {company_id}: can_create_bookings обновлен на {can_create}")
    else:
        logger.warning(f"Компания {company_id} не найдена")


def format_reminder_text(company_name: str, days_left: int, end_date: date) -> str:
    """
    Сформировать текст напоминания.
    
    Args:
        company_name: Название компании
        days_left: Дней до окончания
        end_date: Дата окончания подписки
    
    Returns:
        Текст напоминания
    """
    formatted_date = end_date.strftime("%d.%m.%Y")
    
    if days_left <= 0:
        return f"""⚠️ **Напоминание о подписке**

💼 Компания: {company_name}

📅 Ваша подписка истекла!

Дата окончания: {formatted_date}

Пожалуйста, продлите подписку для продолжения работы сервиса.

🔗 Для оплаты перейдите в админ-панель.
"""
    else:
        return f"""📋 **Напоминание о подписке**

💼 Компания: {company_name}

⏰ Ваша подписка истекает через {days_left} дней!

Дата окончания: {formatted_date}

Пожалуйста, продлите подписку для продолжения работы сервиса.

🔗 Для оплаты перейдите в админ-панель.
"""


# ==================== Celery задачи ====================

@shared_task(name="tasks.send_reminder_7_days_before", bind=True)
async def send_reminder_7_days_before():
    """
    Отправить напоминание за 7 дней до окончания подписки.
    
    Процесс:
    1. Получить список всех активных компаний
    2. Для каждой компании проверить подписку
    3. Если до окончания ≤ 7 дней → отправить напоминание
    """
    logger.info("Запуск задачи: send_reminder_7_days_before")
    
    try:
        # Получаем активные компании
        companies = await get_active_companies()
        
        reminders_sent = 0
        
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as session:
            for company in companies:
                # Получаем текущую подписку
                subscription = await get_company_subscription(session, company.id)
                
                if not subscription:
                    logger.warning(f"У компании {company.name} нет подписки")
                    continue
                
                # Проверяем дату окончания
                if subscription.end_date:
                    days_left = (subscription.end_date - date.today()).days
                    
                    # Отправляем напоминание, если осталось 7 дней или меньше
                    if days_left <= 7 and days_left > 0:
                        # Получаем bot manager для получения токена бота
                        bot_manager = get_bot_manager()
                        bot_status = await bot_manager.get_bot_status(company.id)
                        
                        if bot_status.get("status") == "running" and company.admin_telegram_id:
                            try:
                                # Получаем токен бота компании
                                result = await session.execute(
                                    select(Company).where(Company.id == company.id)
                                )
                                company_obj = result.scalar_one_or_none()
                                
                                if company_obj and company_obj.telegram_bot_token:
                                    from aiogram import Bot
                                    
                                    bot = Bot(token=company_obj.telegram_bot_token)
                                    
                                    # Формируем текст напоминания
                                    reminder_text = format_reminder_text(
                                        company.name,
                                        days_left,
                                        subscription.end_date
                                    )
                                    
                                    # Отправляем напоминание через Telegram Bot API
                                    from web.backend.app.api.bot_manager import bot_manager
                                    
                                    # Получаем токен супер-админа
                                    super_admin_token = None
                                    
                                    # Создаем запрос через HTTP к боту компании
                                    import httpx
                                    
                                    response = await httpx.post(
                                        f"http://localhost:8000/api/bot-manager/send-notification",
                                        headers={
                                            "Authorization": f"Bearer {super_admin_token}",
                                            "Content-Type": "application/json"
                                        },
                                        json={
                                            "company_id": company.id,
                                            "message": reminder_text,
                                            "target_chat_id": company.admin_telegram_id
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        logger.info(f"Напоминание отправлено компании {company.name} (за 7 дней)")
                                        reminders_sent += 1
                                    else:
                                        logger.error(f"Ошибка отправки напоминания компании {company.name}: {response.status_code}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания компании {company.name}: {e}")
                        else:
                            logger.warning(f"Бот компании {company.name} не запущен или нет admin_telegram_id")
                    else:
                        logger.info(f"У компании {company.name} подписка истекла или нет даты окончания")
        
        logger.info(f"Завершено: отправлено {reminders_sent} напоминаний из {len(companies)} компаний")
        return f"Отправлено {reminders_sent} напоминаний"
    
    except Exception as e:
        logger.error(f"Ошибка в задаче send_reminder_7_days_before: {e}", exc_info=True)
        raise


@shared_task(name="tasks.send_reminder_3_days_before", bind=True)
async def send_reminder_3_days_before():
    """
    Отправить напоминание за 3 дня до окончания подписки.
    
    Процесс:
    1. Получить список всех активных компаний
    2. Для каждой компании проверить подписку
    3. Если до окончания ≤ 3 дней → отправить напоминание
    """
    logger.info("Запуск задачи: send_reminder_3_days_before")
    
    try:
        # Получаем активные компании
        companies = await get_active_companies()
        
        reminders_sent = 0
        
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as session:
            for company in companies:
                # Получаем текущую подписку
                subscription = await get_company_subscription(session, company.id)
                
                if not subscription:
                    logger.warning(f"У компании {company.name} нет подписки")
                    continue
                
                # Проверяем дату окончания
                if subscription.end_date:
                    days_left = (subscription.end_date - date.today()).days
                    
                    # Отправляем напоминание, если осталось 3 дня или меньше
                    if days_left <= 3 and days_left > 0:
                        # Получаем bot manager
                        bot_manager = get_bot_manager()
                        bot_status = await bot_manager.get_bot_status(company.id)
                        
                        if bot_status.get("status") == "running" and company.admin_telegram_id:
                            try:
                                from aiogram import Bot
                                
                                # Получаем токен бота
                                result = await session.execute(
                                    select(Company).where(Company.id == company.id)
                                )
                                company_obj = result.scalar_one_or_none()
                                
                                if company_obj and company_obj.telegram_bot_token:
                                    bot = Bot(token=company_obj.telegram_bot_token)
                                    
                                    # Формируем текст напоминания
                                    reminder_text = format_reminder_text(
                                        company.name,
                                        days_left,
                                        subscription.end_date
                                    )
                                    
                                    # Отправляем через HTTP
                                    import httpx
                                    
                                    response = await httpx.post(
                                        f"http://localhost:8000/api/bot-manager/send-notification",
                                        headers={
                                            "Authorization": f"Bearer {None}",
                                            "Content-Type": "application/json"
                                        },
                                        json={
                                            "company_id": company.id,
                                            "message": reminder_text,
                                            "target_chat_id": company.admin_telegram_id
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        logger.info(f"Напоминание отправлено компании {company.name} (за 3 дня)")
                                        reminders_sent += 1
                                    else:
                                        logger.error(f"Ошибка отправки напоминания компании {company.name}: {response.status_code}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания компании {company.name}: {e}")
                        else:
                            logger.warning(f"Бот компании {company.name} не запущен или нет admin_telegram_id")
                    else:
                        logger.info(f"У компании {company.name} подписка истекла или нет даты окончания")
        
        logger.info(f"Завершено: отправлено {reminders_sent} напоминаний из {len(companies)} компаний")
        return f"Отправлено {reminders_sent} напоминаний"
    
    except Exception as e:
        logger.error(f"Ошибка в задаче send_reminder_3_days_before: {e}", exc_info=True)
        raise


@shared_task(name="tasks.send_reminder_1_day_before", bind=True)
async def send_reminder_1_day_before():
    """
    Отправить напоминание за 1 день до окончания подписки.
    
    Процесс:
    1. Получить список всех активных компаний
    2. Для каждой компании проверить подписку
    3. Если до окончания ≤ 1 день → отправить напоминание
    """
    logger.info("Запуск задачи: send_reminder_1_day_before")
    
    try:
        # Получаем активные компании
        companies = await get_active_companies()
        
        reminders_sent = 0
        
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as session:
            for company in companies:
                # Получаем текущую подписку
                subscription = await get_company_subscription(session, company.id)
                
                if not subscription:
                    logger.warning(f"У компании {company.name} нет подписки")
                    continue
                
                # Проверяем дату окончания
                if subscription.end_date:
                    days_left = (subscription.end_date - date.today()).days
                    
                    # Отправляем напоминание, если остался 1 день или сегодня
                    if days_left <= 1:
                        # Получаем bot manager
                        bot_manager = get_bot_manager()
                        bot_status = await bot_manager.get_bot_status(company.id)
                        
                        if bot_status.get("status") == "running" and company.admin_telegram_id:
                            try:
                                from aiogram import Bot
                                
                                # Получаем токен бота
                                result = await session.execute(
                                    select(Company).where(Company.id == company.id)
                                )
                                company_obj = result.scalar_one_or_none()
                                
                                if company_obj and company_obj.telegram_bot_token:
                                    bot = Bot(token=company_obj.telegram_bot_token)
                                    
                                    # Формируем текст напоминания
                                    reminder_text = f"""🚨 **Последний день!**

💼 Компания: {company.name}

📅 Ваша подписка истекает сегодня!

Дата окончания: {subscription.end_date.strftime("%d.%m.%Y")}

⚠️ Срочно продлите подписку!

🔗 Для оплаты перейдите в админ-панель."""
                                    
                                    # Отправляем через HTTP
                                    import httpx
                                    
                                    response = await httpx.post(
                                        f"http://localhost:8000/api/bot-manager/send-notification",
                                        headers={
                                            "Authorization": f"Bearer {None}",
                                            "Content-Type": "application/json"
                                        },
                                        json={
                                            "company_id": company.id,
                                            "message": reminder_text,
                                            "target_chat_id": company.admin_telegram_id
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        logger.info(f"Напоминание отправлено компании {company.name} (за 1 день)")
                                        reminders_sent += 1
                                    else:
                                        logger.error(f"Ошибка отправки напоминания компании {company.name}: {response.status_code}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания компании {company.name}: {e}")
                        else:
                            logger.warning(f"Бот компании {company.name} не запущен или нет admin_telegram_id")
                    else:
                        logger.info(f"У компании {company.name} подписка истекла или нет даты окончания")
        
        logger.info(f"Завершено: отправлено {reminders_sent} напоминаний из {len(companies)} компаний")
        return f"Отправлено {reminders_sent} напоминаний"
    
    except Exception as e:
        logger.error(f"Ошибка в задаче send_reminder_1_day_before: {e}", exc_info=True)
        raise


@shared_task(name="tasks.send_reminder_expiration", bind=True)
async def send_reminder_expiration():
    """
    Отправить напоминание об окончании подписки.
    
    Процесс:
    1. Получить список всех активных компаний
    2. Для каждой компании проверить подписку
    3. Если подписка истекла сегодня → отправить напоминание
    """
    logger.info("Запуск задачи: send_reminder_expiration")
    
    try:
        # Получаем активные компании
        companies = await get_active_companies()
        
        reminders_sent = 0
        
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as session:
            for company in companies:
                # Получаем текущую подписку
                subscription = await get_company_subscription(session, company.id)
                
                if not subscription:
                    logger.warning(f"У компании {company.name} нет подписки")
                    continue
                
                # Проверяем дату окончания
                if subscription.end_date:
                    days_left = (subscription.end_date - date.today()).days
                    
                    # Отправляем напоминание, если подписка истекла сегодня
                    if days_left <= 0:
                        # Получаем bot manager
                        bot_manager = get_bot_manager()
                        bot_status = await bot_manager.get_bot_status(company.id)
                        
                        if bot_status.get("status") == "running" and company.admin_telegram_id:
                            try:
                                from aiogram import Bot
                                
                                # Получаем токен бота
                                result = await session.execute(
                                    select(Company).where(Company.id == company.id)
                                )
                                company_obj = result.scalar_one_or_none()
                                
                                if company_obj and company_obj.telegram_bot_token:
                                    bot = Bot(token=company_obj.telegram_bot_token)
                                    
                                    # Формируем текст напоминания
                                    reminder_text = f"""🚫 **Подписка истекла!**

💼 Компания: {company.name}

❌ Ваша подписка истекла!

Дата окончания: {subscription.end_date.strftime("%d.%m.%Y")}

⚠️ Сервис создания записей заблокирован!

🔗 Для продления подписки перейдите в админ-панель:
https://barber-saas.com/admin/billing"""
                                    
                                    # Отправляем через HTTP
                                    import httpx
                                    
                                    response = await httpx.post(
                                        f"http://localhost:8000/api/bot-manager/send-notification",
                                        headers={
                                            "Authorization": f"Bearer {None}",
                                            "Content-Type": "application/json"
                                        },
                                        json={
                                            "company_id": company.id,
                                            "message": reminder_text,
                                            "target_chat_id": company.admin_telegram_id
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        logger.info(f"Напоминание об окончании отправлено компании {company.name}")
                                        reminders_sent += 1
                                    else:
                                        logger.error(f"Ошибка отправки напоминания компании {company.name}: {response.status_code}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания компании {company.name}: {e}")
                        else:
                            logger.warning(f"Бот компании {company.name} не запущен или нет admin_telegram_id")
                    else:
                        logger.info(f"У компании {company.name} подписка неактивна или нет даты окончания")
        
        logger.info(f"Завершено: отправлено {reminders_sent} напоминаний из {len(companies)} компаний")
        return f"Отправлено {reminders_sent} напоминаний"
    
    except Exception as e:
        logger.error(f"Ошибка в задаче send_reminder_expiration: {e}", exc_info=True)
        raise


@shared_task(name="tasks.send_payment_reminder", bind=True)
async def send_payment_reminder():
    """
    Отправить напоминание о неоплате (каждые 3 дня после окончания).
    
    Процесс:
    1. Получить список компаний с истекшей подпиской
    2. Проверяем, прошло ли 3 дня с момента окончания
    3. Если прошло → отправить напоминание о неоплате
    """
    logger.info("Запуск задачи: send_payment_reminder")
    
    try:
        # Получаем активные компании
        companies = await get_active_companies()
        
        reminders_sent = 0
        
        async_session_maker = get_async_session_maker()
        async with async_session_maker() as session:
            for company in companies:
                # Получаем текущую подписку
                subscription = await get_company_subscription(session, company.id)
                
                if not subscription:
                    logger.warning(f"У компании {company.name} нет подписки")
                    continue
                
                # Проверяем дату окончания
                if subscription.end_date:
                    days_passed = (date.today() - subscription.end_date).days
                    
                    # Отправляем напоминание, если прошло 3 дня после окончания
                    # и если прошло 6, 9, 12 дней (кратные 3 дня)
                    if days_passed >= 3 and days_passed % 3 == 0:
                        # Получаем bot manager
                        bot_manager = get_bot_manager()
                        bot_status = await bot_manager.get_bot_status(company.id)
                        
                        if bot_status.get("status") == "running" and company.admin_telegram_id:
                            try:
                                from aiogram import Bot
                                
                                # Получаем токен бота
                                result = await session.execute(
                                    select(Company).where(Company.id == company.id)
                                )
                                company_obj = result.scalar_one_or_none()
                                
                                if company_obj and company_obj.telegram_bot_token:
                                    bot = Bot(token=company_obj.telegram_bot_token)
                                    
                                    # Формируем текст напоминания
                                    reminder_text = f"""📢 **Напоминание о неоплате**

💼 Компания: {company.name}

❌ Подписка истекла {days_passed} дней назад!

Дата окончания: {subscription.end_date.strftime("%d.%m.%Y")}

⚠️ Сервис создания записей заблокирован!

🔗 Для продления подписки перейдите в админ-панель:
https://barber-saas.com/admin/billing

📞 Пожалуйста, продлите подписку как можно скорее!"""
                                    
                                    # Отправляем через HTTP
                                    import httpx
                                    
                                    response = await httpx.post(
                                        f"http://localhost:8000/api/bot-manager/send-notification",
                                        headers={
                                            "Authorization": f"Bearer {None}",
                                            "Content-Type": "application/json"
                                        },
                                        json={
                                            "company_id": company.id,
                                            "message": reminder_text,
                                            "target_chat_id": company.admin_telegram_id
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        logger.info(f"Напоминание о неоплате отправлено компании {company.name}")
                                        reminders_sent += 1
                                    else:
                                        logger.error(f"Ошибка отправки напоминания компании {company.name}: {response.status_code}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания компании {company.name}: {e}")
                        else:
                            logger.warning(f"Бот компании {company.name} не запущен или нет admin_telegram_id")
                    else:
                        logger.info(f"У компании {company.name} подписка неактивна или нет даты окончания")
        
        logger.info(f"Завершено: отправлено {reminders_sent} напоминаний из {len(companies)} компаний")
        return f"Отправлено {reminders_sent} напоминаний"
    
    except Exception as e:
        logger.error(f"Ошибка в задаче send_payment_reminder: {e}", exc_info=True)
        raise
