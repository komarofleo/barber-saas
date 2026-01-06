"""
Сервис для работы с компаниями в public схеме.

Обеспечивает:
- CRUD операции для Company модели
- Проверку статуса подписки
- Получение информации о компании
"""
import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.public_models import Company, Subscription, Plan

logger = logging.getLogger(__name__)


async def get_company_by_id(
    session: AsyncSession,
    company_id: int
) -> Optional[Company]:
    """
    Получить компанию по ID.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        Объект Company или None
    """
    result = await session.execute(
        select(Company).where(Company.id == company_id)
    )
    return result.scalar_one_or_none()


async def get_company_by_email(
    session: AsyncSession,
    email: str
) -> Optional[Company]:
    """
    Получить компанию по email.
    
    Args:
        session: Асинхронная сессия БД
        email: Email компании
        
    Returns:
        Объект Company или None
    """
    result = await session.execute(
        select(Company).where(Company.email == email)
    )
    return result.scalar_one_or_none()


async def get_all_companies(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
) -> List[Company]:
    """
    Получить список компаний.
    
    Args:
        session: Асинхронная сессия БД
        skip: Сколько записей пропустить (для пагинации)
        limit: Сколько записей получить
        active_only: Только активные компании
        
    Returns:
        Список компаний
    """
    query = select(Company)
    
    if active_only:
        query = query.where(Company.is_active == True)
    
    query = query.order_by(Company.created_at.desc())
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def check_company_subscription(
    session: AsyncSession,
    company_id: int
) -> dict:
    """
    Проверить статус подписки компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        Словарь с информацией о подписке:
        {
            "is_active": bool - активна ли подписка
            "end_date": date или None - дата окончания
            "days_left": int или None - дней до окончания
            "can_create_bookings": bool - может ли создавать записи
        }
    """
    company = await get_company_by_id(session, company_id)
    
    if not company:
        return {
            "is_active": False,
            "end_date": None,
            "days_left": None,
            "can_create_bookings": False
        }
    
    # Получаем последнюю подписку
    result = await session.execute(
        select(Subscription)
        .where(Subscription.company_id == company_id)
        .order_by(Subscription.start_date.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return {
            "is_active": False,
            "end_date": None,
            "days_left": None,
            "can_create_bookings": False
        }
    
    # Проверяем активна ли подписка
    from datetime import date, timedelta
    
    is_active = (
        subscription.status == "active" and
        subscription.start_date <= date.today() and
        (subscription.end_date is None or subscription.end_date >= date.today())
    )
    
    # Считаем дней до окончания
    days_left = None
    if subscription.end_date:
        days_left = (subscription.end_date - date.today()).days
    
    # Подписка истекла менее чем за 7 дней - блокируем создание записей
    can_create_bookings = is_active and (days_left is None or days_left > 7)
    
    return {
        "is_active": is_active,
        "end_date": subscription.end_date,
        "days_left": days_left,
        "can_create_bookings": can_create_bookings,
        "subscription_status": subscription.status,
        "plan_id": subscription.plan_id,
    }


async def create_company(
    session: AsyncSession,
    name: str,
    email: str,
    phone: str,
    telegram_bot_token: str,
    plan_id: int,
    admin_telegram_id: Optional[int] = None,
) -> Company:
    """
    Создать новую компанию.
    
    Args:
        session: Асинхронная сессия БД
        name: Название компании (автосервиса)
        email: Email компании
        phone: Телефон компании
        telegram_bot_token: Токен Telegram бота
        plan_id: ID тарифного плана
        admin_telegram_id: Telegram ID администратора (опционально)
        
    Returns:
        Созданный объект Company
    """
    company = Company(
        name=name,
        email=email,
        phone=phone,
        telegram_bot_token=telegram_bot_token,
        is_active=True,
        admin_telegram_id=admin_telegram_id,
        can_create_bookings=True,  # После оплаты подписки
    )
    
    session.add(company)
    await session.commit()
    await session.refresh(company)
    
    logger.info(f"Создана компания: {name} (ID: {company.id})")
    
    return company


async def update_company(
    session: AsyncSession,
    company_id: int,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    telegram_bot_token: Optional[str] = None,
    admin_telegram_id: Optional[int] = None,
) -> Optional[Company]:
    """
    Обновить информацию о компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        name: Новое название (опционально)
        email: Новый email (опционально)
        phone: Новый телефон (опционально)
        telegram_bot_token: Новый токен бота (опционально)
        admin_telegram_id: Новый Telegram ID администратора (опционально)
        
    Returns:
        Обновленный объект Company или None
    """
    company = await get_company_by_id(session, company_id)
    
    if not company:
        return None
    
    if name is not None:
        company.name = name
    if email is not None:
        company.email = email
    if phone is not None:
        company.phone = phone
    if telegram_bot_token is not None:
        company.telegram_bot_token = telegram_bot_token
    if admin_telegram_id is not None:
        company.admin_telegram_id = admin_telegram_id
    
    await session.commit()
    await session.refresh(company)
    
    logger.info(f"Обновлена компания: {company.name} (ID: {company.id})")
    
    return company


async def deactivate_company(
    session: AsyncSession,
    company_id: int,
) -> bool:
    """
    Деактивировать компанию.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        True, если компания успешно деактивирована, иначе False
    """
    company = await get_company_by_id(session, company_id)
    
    if not company:
        return False
    
    company.is_active = False
    company.can_create_bookings = False
    
    await session.commit()
    
    logger.warning(f"Деактивирована компания: {company.name} (ID: {company.id})")
    
    return True


async def activate_company(
    session: AsyncSession,
    company_id: int,
) -> bool:
    """
    Активировать компанию.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        True, если компания успешно активирована, иначе False
    """
    company = await get_company_by_id(session, company_id)
    
    if not company:
        return False
    
    company.is_active = True
    # can_create_bookings будет обновлен из статуса подписки
    
    await session.commit()
    
    logger.info(f"Активирована компания: {company.name} (ID: {company.id})")
    
    return True


async def get_company_with_subscription(
    session: AsyncSession,
    company_id: int,
) -> Optional[dict]:
    """
    Получить полную информацию о компании с подпиской.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        Словарь с информацией о компании и подписке или None
    """
    company = await get_company_by_id(session, company_id)
    
    if not company:
        return None
    
    subscription_status = await check_company_subscription(session, company_id)
    
    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "phone": company.phone,
            "is_active": company.is_active,
            "admin_telegram_id": company.admin_telegram_id,
            "created_at": company.created_at,
        },
        "subscription": subscription_status,
    }

