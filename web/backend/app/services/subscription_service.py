"""
Сервис для работы с подписками в public схеме.

Обеспечивает:
- CRUD операции для Subscription модели
- Проверку статуса подписки
- Управление тарифными планами
"""
import logging
from typing import Optional, List
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.models.public_models import Subscription, Company, Plan
from app.services.company_service import get_company_by_id, get_all_companies

logger = logging.getLogger(__name__)


async def get_subscription_by_id(
    session: AsyncSession,
    subscription_id: int
) -> Optional[Subscription]:
    """
    Получить подписку по ID.
    
    Args:
        session: Асинхронная сессия БД
        subscription_id: ID подписки
        
    Returns:
        Объект Subscription или None
    """
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    return result.scalar_one_or_none()


async def get_subscription_by_company(
    session: AsyncSession,
    company_id: int
) -> Optional[Subscription]:
    """
    Получить последнюю подписку компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        Объект Subscription или None
    """
    result = await session.execute(
        select(Subscription)
        .where(Subscription.company_id == company_id)
        .order_by(Subscription.start_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_all_subscriptions(
    session: AsyncSession,
    company_id: Optional[int] = None,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Subscription]:
    """
    Получить список подписок.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании (опционально)
        active_only: Только активные подписки
        skip: Сколько записей пропустить
        limit: Сколько записей получить
        
    Returns:
        Список подписок
    """
    query = select(Subscription).options(
        selectinload(Subscription.company),
        selectinload(Subscription.plan)
    )
    
    if company_id is not None:
        query = query.where(Subscription.company_id == company_id)
    
    if active_only:
        query = query.where(Subscription.status == "active")
    
    query = query.order_by(Subscription.start_date.desc())
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def check_subscription_status(
    session: AsyncSession,
    company_id: int
) -> dict:
    """
    Проверить статус подписки компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        
    Returns:
        Словарь с информацией о статусе:
        {
            "is_active": bool - активна ли подписка
            "days_left": int или None - дней до окончания
            "can_create_bookings": bool - может ли создавать записи
            "status": str - статус подписки
            "plan_id": int или None - ID тарифного плана
            "will_block_in": int или None - через сколько дней будет блокировка
        }
    """
    company = await get_company_by_id(session, company_id)
    
    if not company or not company.is_active:
        return {
            "is_active": False,
            "days_left": None,
            "can_create_bookings": False,
            "status": "inactive",
            "plan_id": None,
            "will_block_in": None,
        }
    
    # Получаем последнюю подписку
    subscription = await get_subscription_by_company(session, company_id)
    
    if not subscription:
        return {
            "is_active": False,
            "days_left": None,
            "can_create_bookings": False,
            "status": "no_subscription",
            "plan_id": None,
            "will_block_in": None,
        }
    
    # Проверяем активна ли подписка
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
    
    # Через сколько дней будет блокировка (если подписка истекла)
    will_block_in = None
    if days_left is not None and days_left <= 0:
        # Уже истекла
        will_block_in = 0
    elif days_left is not None and days_left <= 7:
        # Блокировка через 7 дней
        will_block_in = 7
    
    return {
        "is_active": is_active,
        "days_left": days_left,
        "can_create_bookings": can_create_bookings,
        "status": subscription.status,
        "plan_id": subscription.plan_id,
        "will_block_in": will_block_in,
    }


async def create_subscription(
    session: AsyncSession,
    company_id: int,
    plan_id: int,
    start_date: date = None,
) -> Subscription:
    """
    Создать новую подписку для компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        plan_id: ID тарифного плана
        start_date: Дата начала подписки (по умолчанию - сегодня)
        
    Returns:
        Созданный объект Subscription
    """
    company = await get_company_by_id(session, company_id)
    
    if not company:
        raise ValueError(f"Компания с ID {company_id} не найдена")
    
    if start_date is None:
        start_date = date.today()
    
    # Создаем подписку
    subscription = Subscription(
        company_id=company_id,
        plan_id=plan_id,
        status="active",
        start_date=start_date,
        end_date=None,  # Будет установлено после оплаты
    )
    
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    
    logger.info(f"Создана подписка для компании {company_id} (план {plan_id})")
    
    return subscription


async def activate_subscription(
    session: AsyncSession,
    subscription_id: int,
    end_date: date,
) -> bool:
    """
    Активировать подписку (после оплаты).
    
    Args:
        session: Асинхронная сессия БД
        subscription_id: ID подписки
        end_date: Дата окончания подписки (обычно +30 дней от начала)
        
    Returns:
        True, если подписка успешно активирована, иначе False
    """
    subscription = await get_subscription_by_id(session, subscription_id)
    
    if not subscription:
        raise ValueError(f"Подписка с ID {subscription_id} не найдена")
    
    # Получаем план
    result = await session.execute(
        select(Plan).where(Plan.id == subscription.plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise ValueError(f"Тарифный план с ID {subscription.plan_id} не найден")
    
    # Обновляем подписку
    subscription.status = "active"
    subscription.end_date = end_date
    
    await session.commit()
    
    logger.info(f"Активирована подписка {subscription_id} для компании {subscription.company_id}")
    
    return True


async def renew_subscription(
    session: AsyncSession,
    company_id: int,
    plan_id: int,
) -> bool:
    """
    Продлить подписку компании.
    
    Args:
        session: Асинхронная сессия БД
        company_id: ID компании
        plan_id: ID нового тарифного плана
        
    Returns:
        True, если подписка успешно продлена, иначе False
    """
    from datetime import timedelta
    
    # Получаем текущую подписку
    old_subscription = await get_subscription_by_company(session, company_id)
    
    if not old_subscription:
        # Если подписки нет, создаем новую
        await create_subscription(session, company_id, plan_id)
        return True
    
    # Деактивируем старую подписку
    old_subscription.status = "expired"
    await session.commit()
    
    # Создаем новую подписку
    new_subscription = await create_subscription(session, company_id, plan_id)
    
    logger.info(f"Продлена подписка для компании {company_id} (старая: {old_subscription.id}, новая: {new_subscription.id})")
    
    return True


async def cancel_subscription(
    session: AsyncSession,
    subscription_id: int,
) -> bool:
    """
    Отменить подписку.
    
    Args:
        session: Асинхронная сессия БД
        subscription_id: ID подписки
        
    Returns:
        True, если подписка успешно отменена, иначе False
    """
    subscription = await get_subscription_by_id(session, subscription_id)
    
    if not subscription:
        raise ValueError(f"Подписка с ID {subscription_id} не найдена")
    
    # Отменяем подписку
    subscription.status = "cancelled"
    
    await session.commit()
    
    logger.info(f"Отменена подписка {subscription_id} для компании {subscription.company_id}")
    
    # Обновляем can_create_bookings в компании
    company = await get_company_by_id(session, subscription.company_id)
    if company:
        company.can_create_bookings = False
        await session.commit()
    
    return True


async def get_expiring_subscriptions(
    session: AsyncSession,
    days_threshold: int = 7,
) -> List[dict]:
    """
    Получить список подписок, которые истекают через указанное количество дней.
    
    Args:
        session: Асинхронная сессия БД
        days_threshold: Порог в днях (по умолчанию 7)
        
    Returns:
        Список словарей с информацией о компаниях и подписках
    """
    threshold_date = date.today() + timedelta(days=days_threshold)
    
    query = select(Subscription).options(
        selectinload(Subscription.company)
    ).where(
        and_(
            Subscription.status == "active",
            Subscription.end_date.isnot(None),
            Subscription.end_date <= threshold_date
        )
    ).order_by(Subscription.end_date)
    
    result = await session.execute(query)
    subscriptions = result.scalars().all()
    
    # Формируем список
    expiring_subscriptions = []
    for subscription in subscriptions:
        days_left = (subscription.end_date - date.today()).days
        expiring_subscriptions.append({
            "subscription_id": subscription.id,
            "company_id": subscription.company_id,
            "company_name": subscription.company.name if subscription.company else "Неизвестно",
            "company_email": subscription.company.email if subscription.company else None,
            "end_date": subscription.end_date,
            "days_left": days_left,
            "admin_telegram_id": subscription.company.admin_telegram_id if subscription.company else None,
        })
    
    return expiring_subscriptions

