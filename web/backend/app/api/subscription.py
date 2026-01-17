"""
API для работы с подписками в контексте текущего пользователя
"""
from typing import Annotated, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.public_models import Company, Subscription, Plan, Payment
from app.api.auth import get_current_user
from app.config import settings
from app.deps.tenant import resolve_company_id
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


class PaymentResponse(BaseModel):
    """
    Ответ с данными платежа для страницы биллинга.
    """
    id: int
    plan_id: int
    amount: float
    currency: str
    status: str
    description: Optional[str] = None
    yookassa_payment_status: Optional[str] = None
    yookassa_confirmation_url: Optional[str] = None
    created_at: str


class PaymentCreateRequest(BaseModel):
    """
    Запрос на создание платежа за подписку.
    """
    plan_id: int = Field(..., ge=1, description="ID тарифного плана")
    billing_period: Literal["monthly", "yearly"] = Field(
        "monthly",
        description="Период оплаты: monthly или yearly",
    )


class PaymentCreateResponse(BaseModel):
    """
    Ответ с ссылкой на оплату через Юкассу.
    """
    payment_id: int
    confirmation_url: str


async def get_company_id_from_user(
    current_user: User,
    db: AsyncSession,
    request: Optional[Request] = None,
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
    # 1) Пытаемся получить company_id из request/JWT (если доступен)
    if request is not None:
        company_id = await resolve_company_id(request, None)
        if company_id:
            return company_id

    # 2) Ищем компанию по admin_telegram_id
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
    request: Request,
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
        company_id = await get_company_id_from_user(current_user, db, request)
        
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


@router.get("/payments", response_model=list[PaymentResponse])
async def get_subscription_payments(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Получить историю платежей компании.
    """
    company_id = await get_company_id_from_user(current_user, db, request)
    if company_id is None:
        raise HTTPException(status_code=404, detail="Company not found for user")

    result = await db.execute(
        select(Payment)
        .where(Payment.company_id == company_id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()

    return [
        PaymentResponse(
            id=payment.id,
            plan_id=payment.plan_id,
            amount=float(payment.amount),
            currency=payment.currency,
            status=payment.status,
            description=payment.description,
            yookassa_payment_status=payment.yookassa_payment_status,
            yookassa_confirmation_url=payment.yookassa_confirmation_url,
            created_at=payment.created_at.isoformat() if payment.created_at else "",
        )
        for payment in payments
    ]


@router.post("/payments", response_model=PaymentCreateResponse)
async def create_subscription_payment(
    payment_data: PaymentCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Создать платеж для продления подписки через Юкассу.
    """
    company_id = await get_company_id_from_user(current_user, db, request)
    if company_id is None:
        raise HTTPException(status_code=404, detail="Company not found for user")

    plan_result = await db.execute(
        select(Plan).where(Plan.id == payment_data.plan_id, Plan.is_active == True)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Тарифный план не найден")

    amount = plan.price_monthly if payment_data.billing_period == "monthly" else plan.price_yearly
    description = f"Продление подписки: {plan.name}"
    return_url = f"{settings.YOOKASSA_RETURN_URL}?payment_id=0"

    from app.services.yookassa_service import create_payment

    yookassa_payment = await create_payment(
        amount=amount,
        description=description,
        return_url=return_url,
        metadata={
            "company_id": company_id,
            "plan_id": plan.id,
            "billing_period": payment_data.billing_period,
        },
    )

    if not yookassa_payment or "id" not in yookassa_payment:
        raise HTTPException(status_code=500, detail="Не удалось создать платеж")

    payment = Payment(
        company_id=company_id,
        plan_id=plan.id,
        subscription_id=None,
        amount=amount,
        currency=yookassa_payment.get("currency", "RUB"),
        status="pending",
        yookassa_payment_id=yookassa_payment["id"],
        yookassa_payment_status=yookassa_payment.get("status", "pending"),
        yookassa_confirmation_url=yookassa_payment.get("confirmation_url"),
        yookassa_return_url=return_url,
        description=description,
        extra_data={
            "company_id": company_id,
            "plan_id": plan.id,
            "billing_period": payment_data.billing_period,
        },
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    if payment.yookassa_return_url:
        payment.yookassa_return_url = payment.yookassa_return_url.replace("payment_id=0", f"payment_id={payment.id}")
        await db.commit()

    return PaymentCreateResponse(
        payment_id=payment.id,
        confirmation_url=yookassa_payment.get("confirmation_url", ""),
    )


@router.get("/check")
async def check_subscription_status(
    request: Request,
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
        
        company_id = await get_company_id_from_user(current_user, db, request)
        
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
