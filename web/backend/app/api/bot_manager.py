"""
API для управления мульти-ботами.

Обеспечивает:
- Запуск/остановку/перезапуск ботов
- Получение статуса ботов
- Управление всеми активными компаниями
- Глобальную статистику (для супер-админа)
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from fastapi import APIRouter, Depends, HTTPException, status
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database import get_db
from app.services.tenant_service import get_tenant_service
from app.models.public_models import Company, Subscription
from app.schemas.public_schemas import CompanyResponse, SubscriptionResponse
from bot.bot_manager import get_bot_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bot-manager", tags=["bot-manager"])


@router.get("/status", response_model=List[dict])
async def get_all_bots_status(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить статус всех ботов для всех компаний.
    
    Args:
        page: номер страницы
        page_size: количество элементов на странице
        db: Асинхронная сессия БД
        
    Returns:
        Список статусов ботов с информацией о компаниях
    """
    # Получаем всех активных компаний
    result = await db.execute(
        select(Company).where(Company.is_active == True)
    )
    companies = result.scalars().all()
    
    # Получаем BotManager
    bot_manager = get_bot_manager()
    
    # Формируем ответ
    bot_statuses = []
    
    for company in companies:
        # Проверяем подписку
        subscription = None
        if company.id:
            result = await db.execute(
                select(Subscription)
                .where(Subscription.company_id == company.id)
                .order_by(Subscription.start_date.desc())
                .limit(1)
            )
            subscription = result.scalar_one_or_none()
        
        # Проверяем статус бота
        bot_status = await bot_manager.get_bot_status(company.id)
        
        # Формируем информацию о компании
        company_info = {
            "company_id": company.id,
            "company_name": company.name,
            "is_active": company.is_active,
            "can_create_bookings": company.can_create_bookings,
        }
        
        # Добавляем информацию о подписке
        if subscription:
            from datetime import date, timedelta
            
            # Проверяем активна ли подписка
            is_active = (
                subscription.status == "active" and
                subscription.start_date <= date.today() and
                (subscription.end_date is None or subscription.end_date >= date.today())
            )
            
            days_left = None
            if subscription.end_date:
                days_left = (subscription.end_date - date.today()).days
            
            company_info["subscription"] = {
                "is_active": is_active,
                "status": subscription.status,
                "plan_id": subscription.plan_id,
                "end_date": subscription.end_date.strftime("%d.%m.%Y") if subscription.end_date else None,
                "days_left": days_left,
                "will_block_in": 7 if days_left and days_left <= 0 else days_left if days_left else None,
            }
        else:
            company_info["subscription"] = {
                "is_active": False,
                "status": "no_subscription",
                "plan_id": None,
                "end_date": None,
                "days_left": None,
                "will_block_in": None,
            }
        
        # Добавляем статус бота
        company_info["bot"] = bot_status
        
        bot_statuses.append(company_info)
    
    # Пагинация
    total = len(companies)
    paginated_statuses = bot_statuses[(page - 1) * page_size : page * page_size]
    
    logger.info(f"Получен статус ботов: {len(paginated_statuses)} из {total} компаний")
    
    return {
        "items": paginated_statuses,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/status/{company_id}", response_model=dict)
async def get_bot_status_by_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить статус бота для конкретной компании.
    
    Args:
        company_id: ID компании
        db: Асинхронная сессия БД
        
    Returns:
        Статус бота с информацией о компании
    """
    # Получаем компанию
    result = await db.execute(
        select(Company).options(
            selectinload(Company.subscription)
        ).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    
    # Проверяем подписку
    subscription = company.subscription
    company_info = {
        "company_id": company.id,
        "company_name": company.name,
        "is_active": company.is_active,
        "can_create_bookings": company.can_create_bookings,
    }
    
    if subscription:
        from datetime import date, timedelta
        
        # Проверяем активна ли подписка
        is_active = (
            subscription.status == "active" and
            subscription.start_date <= date.today() and
            (subscription.end_date is None or subscription.end_date >= date.today())
        )
        
        days_left = None
        if subscription.end_date:
            days_left = (subscription.end_date - date.today()).days
        
        company_info["subscription"] = {
            "is_active": is_active,
            "status": subscription.status,
            "plan_id": subscription.plan_id,
            "end_date": subscription.end_date.strftime("%d.%m.%Y") if subscription.end_date else None,
            "days_left": days_left,
            "will_block_in": 7 if days_left and days_left <= 0 else days_left if days_left else None,
        }
    else:
        company_info["subscription"] = {
            "is_active": False,
            "status": "no_subscription",
            "plan_id": None,
            "end_date": None,
            "days_left": None,
            "will_block_in": None,
        }
    
    # Получаем статус бота через BotManager
    bot_manager = get_bot_manager()
    bot_status = await bot_manager.get_bot_status(company_id)
    
    company_info["bot"] = bot_status
    
    logger.info(f"Получен статус бота компании {company_id}")
    
    return company_info


@router.post("/start-all", response_model=dict)
async def start_all_bots(
    db: AsyncSession = Depends(get_db),
):
    """
    Запустить все боты для всех активных компаний.
    
    Args:
        db: Асинхронная сессия БД
        
    Returns:
        Результат запуска
    """
    # Получаем BotManager
    bot_manager = get_bot_manager()
    
    # Запускаем всех ботов
    count = await bot_manager.start_all_bots()
    
    logger.info(f"Запущено {count} ботов")
    
    return {
        "success": True,
        "bots_started": count,
    }


@router.post("/stop-all", response_model=dict)
async def stop_all_bots(
    db: AsyncSession = Depends(get_db),
):
    """
    Остановить все боты.
    
    Args:
        db: Асинхронная сессия БД
        
    Returns:
        Результат остановки
    """
    # Получаем BotManager
    bot_manager = get_bot_manager()
    
    # Останавливаем всех ботов
    count = await bot_manager.stop_all_bots()
    
    logger.info(f"Остановлено {count} ботов")
    
    return {
        "success": True,
        "bots_stopped": count,
    }


@router.post("/restart/{company_id}", response_model=dict)
async def restart_bot(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Перезапустить бота для конкретной компании.
    
    Args:
        company_id: ID компании
        db: Асинхронная сессия БД
        
    Returns:
        Результат перезапуска
    """
    # Проверяем существование компании
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    
    if not company.telegram_bot_token:
        raise HTTPException(status_code=400, detail="У компании нет токена Telegram бота")
    
    if not company.is_active:
        raise HTTPException(status_code=400, detail="Компания не активна")
    
    # Получаем BotManager и перезапускаем бота
    bot_manager = get_bot_manager()
    await bot_manager.restart_bot(company_id)
    
    logger.info(f"Бот компании {company_id} перезапущен")
    
    return {
        "success": True,
        "bot_restarted": True,
    }


@router.post("/stop/{company_id}", response_model=dict)
async def stop_bot(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Остановить бота для конкретной компании.
    
    Args:
        company_id: ID компании
        db: Асинхронная сессия БД
        
    Returns:
        Результат остановки
    """
    # Проверяем существование компании
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    
    # Получаем BotManager и останавливаем бота
    bot_manager = get_bot_manager()
    await bot_manager.stop_bot(company_id)
    
    logger.info(f"Бот компании {company_id} остановлен")
    
    return {
        "success": True,
        "bot_stopped": True,
    }


@router.post("/start/{company_id}", response_model=dict)
async def start_bot(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Запустить бота для конкретной компании.
    
    Args:
        company_id: ID компании
        db: Асинхронная сессия БД
        
    Returns:
        Результат запуска
    """
    # Проверяем существование компании
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    
    if not company.telegram_bot_token:
        raise HTTPException(status_code=400, detail="У компании нет токена Telegram бота")
    
    if not company.is_active:
        raise HTTPException(status_code=400, detail="Компания не активна")
    
    # Получаем BotManager и запускаем бота
    bot_manager = get_bot_manager()
    await bot_manager.start_bot(company_id)
    
    logger.info(f"Бот компании {company_id} запущен")
    
    return {
        "success": True,
        "bot_started": True,
    }


@router.get("/stats", response_model=dict)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Получить статистику дэшборда для супер-админа.
    
    Args:
        db: Асинхронная сессия БД (public схема)
        
    Returns:
        Словарь со статистикой по всем компаниям
    """
    # Количество компаний
    companies_count = await db.scalar(
        select(func.count(Company.id)).where(Company.is_active == True)
    ) or 0
    
    # Количество активных подписок
    active_subs = await db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    ) or 0
    
    # Количество истекающих подписок (более 7 дней)
    from datetime import date, timedelta
    expiring_soon = await db.scalar(
        select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "active",
                Subscription.end_date.isnot(None),
                Subscription.end_date <= (date.today() + timedelta(days=7))
            )
        )
    ) or 0
    
    # Количество компаний с истекшей подпиской
    expired_subs = await db.scalar(
        select(func.count(Company.id)).where(Company.is_active == True)
    ) or 0
    
    if companies_count > 0:
        # Проверяем подписки каждой компании
        result = await db.execute(
            select(Company).options(
                selectinload(Company.subscription)
            ).where(Company.is_active == True)
        )
        companies = result.scalars().all()
        
        for company in companies:
            if company.subscription:
                sub = company.subscription
                if sub.status != "active" and sub.end_date < date.today():
                    expired_subs += 1
    
    # Количество ботов (примерно, равно количеству компаний)
    # В будущем можно получать точное количество из BotManager
    bots_count = companies_count
    
    # Общая выручка за месяц
    from sqlalchemy import extract
    total_revenue = await db.scalar(
        select(func.coalesce(
            extract("year", Payment.created_at) == datetime.utcnow().year,
            extract("month", Payment.created_at) == datetime.utcnow().month,
            sum(Payment.amount).label("revenue")
        )).where(Payment.status == "succeeded")
    ) or 0
    
    # Получаем BotManager
    bot_manager = get_bot_manager()
    running_bots = bot_manager.get_running_bots_count()
    
    stats = {
        "companies_count": companies_count,
        "active_subscriptions": active_subs,
        "expiring_soon_subscriptions": expiring_soon,
        "expired_subscriptions": expired_subs,
        "bots_count": bots_count,
        "running_bots": running_bots,
        "total_revenue_month": float(total_revenue),
    }
    
    logger.info(f"Статистика дэшборда получена: {stats}")
    
    return stats

