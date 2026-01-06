"""
API для работы с подписками в контексте текущего пользователя
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel

from app.database import get_db
from app.models.public_models import Company, Subscription, Plan
from app.api.auth import get_current_user
from app.config import settings
from shared.database.models import User

router = APIRouter(prefix="/api/subscription", tags=["subscription"])


class SubscriptionInfoResponse(BaseModel):
    """
    Информация о подписке компании.
    
    Используется для отображения статуса подписки в frontend.
    """
    id: int
    company_id: int
    plan_name: str
    status: str
    start_date: str
    end_date: str
    can_create_bookings: bool
    days_remaining: int


async def get_company_id_from_user(
    current_user: User,
    db: AsyncSession
) -> Optional[int]:
    """
    Получить company_id для пользователя.
    
    В мульти-тенантной архитектуре, пользователь принадлежит к одной компании.
    Для получения company_id, нужно:
    1. Проверить JWT токен (если company_id там есть)
    2. Проверить request.state (если middleware добавил)
    3. Найти компанию по admin_telegram_id или другим признакам
    
    Args:
        current_user: Текущий пользователь
        db: Сессия БД
        
    Returns:
        company_id или None
    """
    # Пока что, используем упрощенный подход:
    # Ищем компанию по admin_telegram_id
    if current_user.telegram_id:
        # Используем public схему для поиска компании
        result = await db.execute(
            text("""
                SELECT id FROM public.companies 
                WHERE admin_telegram_id = :telegram_id 
                OR :telegram_id = ANY(telegram_admin_ids)
                LIMIT 1
            """),
            {"telegram_id": current_user.telegram_id}
        )
        row = result.fetchone()
        if row:
            return row[0]
    
    return None


@router.get("", response_model=SubscriptionInfoResponse)
async def get_subscription_info(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Получить информацию о подписке текущего пользователя.
    
    Endpoint используется для:
    - Отображения статуса подписки в сайдбаре
    - Проверки возможности создания записей
    - Блокировки функций при истекшей подписке
    
    Returns:
        SubscriptionInfoResponse: Информация о подписке
        
    Raises:
        HTTPException: 401 если пользователь не авторизован
        HTTPException: 404 если подписка не найдена
    """
    try:
        from datetime import date
        
        # Получаем company_id для пользователя
        company_id = await get_company_id_from_user(current_user, db)
        
        if company_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found for user"
            )
        
        # Получаем активную подписку для компании (используем public схему)
        result = await db.execute(
            text("""
                SELECT s.id, s.company_id, s.start_date, s.end_date, s.status,
                       p.name as plan_name
                FROM public.subscriptions s
                JOIN public.plans p ON s.plan_id = p.id
                WHERE s.company_id = :company_id
                ORDER BY s.end_date DESC
                LIMIT 1
            """),
            {"company_id": company_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found for company"
            )
        
        subscription_id, sub_company_id, start_date, end_date, sub_status, plan_name = row
        
        # Определяем статус подписки
        today = date.today()
        
        if sub_status == 'cancelled':
            status_str = 'cancelled'
        elif end_date < today:
            status_str = 'expired'
        elif sub_status == 'blocked':
            status_str = 'blocked'
        else:
            status_str = 'active'
        
        # Проверяем можно ли создавать записи
        can_create_bookings = (
            status_str == 'active' and
            end_date >= today
        )
        
        # Вычисляем дней до окончания подписки
        days_remaining = (end_date - today).days
        
        return SubscriptionInfoResponse(
            id=subscription_id,
            company_id=sub_company_id,
            plan_name=plan_name or 'Неизвестно',
            status=status_str,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            can_create_bookings=can_create_bookings,
            days_remaining=days_remaining
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching subscription info: {str(e)}"
        )


@router.get("/check")
async def check_subscription_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Проверить статус подписки (упрощенный endpoint).
    
    Используется для быстрой проверки блокировки функций.
    
    Returns:
        dict: {"can_create_bookings": bool, "status": str}
    """
    try:
        from datetime import date
        
        company_id = await get_company_id_from_user(current_user, db)
        
        if company_id is None:
            return {
                "can_create_bookings": False,
                "status": "no_company"
            }
        
        result = await db.execute(
            text("""
                SELECT s.end_date, s.status
                FROM public.subscriptions s
                WHERE s.company_id = :company_id
                ORDER BY s.end_date DESC
                LIMIT 1
            """),
            {"company_id": company_id}
        )
        row = result.fetchone()
        
        if not row:
            return {
                "can_create_bookings": False,
                "status": "no_subscription"
            }
        
        end_date, sub_status = row
        today = date.today()
        
        if sub_status == 'cancelled':
            status_str = 'cancelled'
        elif end_date < today:
            status_str = 'expired'
        elif sub_status == 'blocked':
            status_str = 'blocked'
        else:
            status_str = 'active'
        
        can_create_bookings = (
            status_str == 'active' and
            end_date >= today
        )
        
        return {
            "can_create_bookings": can_create_bookings,
            "status": status_str
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking subscription status: {str(e)}"
        )
