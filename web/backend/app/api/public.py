"""
Публичный API для регистрации новых компаний.

Этот модуль содержит endpoints для:
- Регистрации новых автосервисов
- Создания платежей через Юкассу
- Обработки webhooks от платежной системы
"""

import secrets
import string
import httpx
import logging
from typing import Annotated
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.schemas.public_schemas import (
    CompanyRegistration,
    RegistrationResponse,
    CompanyCreate,
    PaymentCreate,
    SubscriptionCreate,
    PlanResponse,
    SubscriptionResponse,
    PaymentStatus,
    SubscriptionStatus
)

from app.models.public_models import Company, Plan, Payment, Subscription
from app.services.yookassa_service import YooKassaService, create_payment

yookassa_service = YooKassaService()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["public"])


def generate_password(length: int = 12) -> str:
    """
    Генерировать случайный пароль.
    
    Args:
        length: Длина пароля (по умолчанию 12)
    
    Returns:
        Случайный пароль
    """
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


async def validate_bot_token(token: str) -> bool:
    """
    Валидировать токен Telegram бота через API Telegram.
    
    Args:
        token: Токен бота
    
    Returns:
        True если токен валиден, False в противном случае
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка валидации токена бота: {e}")
        return False


async def check_email_exists(email: str, db: AsyncSession) -> bool:
    """
    Проверить, существует ли компания с таким email.
    
    Args:
        email: Email для проверки
        db: Сессия БД
    
    Returns:
        True если email занят, False в противном случае
    """
    result = await db.execute(
        select(Company).where(Company.email == email)
    )
    return result.scalar_one_or_none() is not None


async def check_bot_token_exists(token: str, db: AsyncSession) -> bool:
    """
    Проверить, существует ли компания с таким токеном бота.
    
    Args:
        token: Токен бота для проверки
        db: Сессия БД
    
    Returns:
        True если токен занят, False в противном случае
    """
    result = await db.execute(
        select(Company).where(Company.telegram_bot_token == token)
    )
    return result.scalar_one_or_none() is not None


async def get_active_plan(plan_id: int, db: AsyncSession) -> Plan:
    """
    Получить активный тарифный план по ID.
    
    Args:
        plan_id: ID плана
        db: Сессия БД
    
    Returns:
        Объект плана
    
    Raises:
        HTTPException: Если план не существует или не активен
    """
    result = await db.execute(
        select(Plan).where(
            and_(Plan.id == plan_id, Plan.is_active == True)
        )
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Тарифный план с ID {plan_id} не существует или не активен"
        )
    
    return plan


@router.post("/companies/register", response_model=RegistrationResponse, status_code=201)
async def register_company(
    registration_data: CompanyRegistration,
    db: AsyncSession = Depends(get_db)
):
    """
    Публичная регистрация новой компании.
    
    Проверяет валидность токена бота, создает платеж через Юкассу,
    возвращает ссылку на оплату.
    
    Args:
        registration_data: Данные регистрации компании
        db: Асинхронная сессия БД
    
    Returns:
        Данные для перенаправления на оплату
    
    Raises:
        HTTPException: При ошибках валидации или создании платежа
    
    Example:
        >>> # Запрос регистрации
        >>> {
        ...     "name": "ООО 'Точка'",
        ...     "email": "admin@avtoservis.ru",
        ...     "phone": "+79001234567",
        ...     "telegram_bot_token": "8332803813:AAG...",
        ...     "admin_telegram_id": 329621295,
        ...     "plan_id": 3
        ... }
        >>> 
        >>> # Ответ
        >>> {
        ...     "success": true,
        ...     "payment_id": 123,
        ...     "confirmation_url": "https://yoomoney.ru/checkout/...",
        ...     "message": "Платеж создан. Ожидает оплаты."
        ... }
    """
    logger.info(f"Попытка регистрации компании: {registration_data.name}")
    
    # 1. Валидация данных формы
    if not registration_data.name or len(registration_data.name) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название салона красоты должно содержать минимум 3 символа"
        )
    
    # 2. Проверка токена бота через Telegram API
    logger.info(f"Валидация токена бота для {registration_data.name}")
    is_bot_token_valid = await validate_bot_token(registration_data.telegram_bot_token)
    
    if not is_bot_token_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный токен Telegram бота"
        )
    
    # 3. Проверка уникальности email
    logger.info(f"Проверка уникальности email: {registration_data.email}")
    email_exists = await check_email_exists(registration_data.email, db)
    
    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Компания с таким email уже зарегистрирована"
        )
    
    # 4. Проверка уникальности токена бота
    logger.info(f"Проверка уникальности токена бота")
    bot_token_exists = await check_bot_token_exists(registration_data.telegram_bot_token, db)
    
    if bot_token_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот токен бота уже используется"
        )
    
    # 5. Получение тарифного плана
    logger.info(f"Получение тарифного плана: {registration_data.plan_id}")
    plan = await get_active_plan(registration_data.plan_id, db)
    
    # 6. Генерация пароля для компании
    import bcrypt
    password = generate_password(12)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    logger.info(f"Сгенерирован пароль для компании: {registration_data.name}")
    
    # 7. Создание платежа через Юкассу
    logger.info(f"Создание платежа через Юкассу для {registration_data.name}")
    # Временно используем payment_id=0, потом заменим на реальный после создания платежа
    payment_data = await create_payment(
        amount=Decimal(str(plan.price_monthly)),
        description=f"Подписка на тариф {plan.name} для салона красоты '{registration_data.name}'",
        return_url=f"{settings.YOOKASSA_RETURN_URL}?payment_id=0"  # Будет обновлено после создания платежа
    )
    
    # 8. Сохранение данных регистрации в extra_data для использования в webhook
    import json
    registration_metadata = {
        "company_name": registration_data.name,
        "email": registration_data.email,
        "phone": registration_data.phone,
        "telegram_bot_token": registration_data.telegram_bot_token,
        "admin_telegram_id": registration_data.admin_telegram_id,
        "password": password,  # Сохраняем пароль в открытом виде для отправки на email
        "password_hash": password_hash  # Сохраняем хеш для сохранения в БД
    }
    
    # 9. Сохранение платежа в БД
    logger.info(f"Сохранение платежа в БД: {payment_data['id']}")
    logger.info(f"Данные регистрации для сохранения: {registration_metadata}")
    payment = Payment(
        company_id=None,  # Будет заполнено после успешной оплаты
        plan_id=plan.id,
        amount=payment_data["amount"],
        currency=payment_data.get("currency", "RUB"),
        status="pending",  # Исправлено: используем строку напрямую
        yookassa_payment_id=payment_data["id"],
        yookassa_payment_status=payment_data.get("status", "pending"),
        yookassa_confirmation_url=payment_data.get("confirmation_url"),
        yookassa_return_url=payment_data.get("return_url"),
        description=f"Подписка на тариф {plan.name}",
        extra_data=registration_metadata  # Сохраняем данные регистрации для webhook
    )
    logger.info(f"Payment extra_data после создания: {payment.extra_data}")
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    # Обновляем return_url с реальным payment_id
    if payment.yookassa_return_url:
        payment.yookassa_return_url = payment.yookassa_return_url.replace("payment_id=0", f"payment_id={payment.id}")
        await db.commit()
    
    logger.info(f"Платеж создан успешно: {payment.id}")
    
    # 8. Возврат ответа со ссылкой на оплату
    return RegistrationResponse(
        success=True,
        payment_id=payment.id,
        confirmation_url=payment_data["confirmation_url"],
        message="Платеж создан. Ожидает оплаты."
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan_by_id(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить тарифный план по ID.
    
    Args:
        plan_id: ID плана
        db: Асинхронная сессия БД
        
    Returns:
        Объект плана с полной информацией
    """
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="План не найден")
    
    logger.info(f"Получение плана: {plan_id}")
    
    return PlanResponse.model_validate(plan)


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список активных тарифных планов.
    
    Returns:
        Список активных тарифных планов
    
    Example:
        >>> [
        ...     {
        ...         "id": 1,
        ...         "name": "Starter",
        ...         "description": "Базовый тариф",
        ...         "price_monthly": 1000.00,
        ...         "price_yearly": 10000.00,
        ...         "max_bookings_per_month": 50,
        ...         "max_users": 5,
        ...         "max_masters": 2,
        ...         "is_active": true
        ...     },
        ...     # ... другие планы
        ... ]
    """
    logger.info("Получение списка тарифных планов")
    
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.display_order)
    )
    plans = result.scalars().all()
    
    return plans


@router.get("/payments/{payment_id}/status")
async def get_payment_status(
    payment_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статус платежа и данные компании (если создана).
    
    Args:
        payment_id: ID платежа
        db: Асинхронная сессия БД
        
    Returns:
        Объект со статусом платежа и данными компании (если создана)
    """
    logger.info(f"Проверка статуса платежа: {payment_id}")
    
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Платеж не найден")
    
    response = {
        "payment_id": payment.id,
        "status": payment.status,
        "yookassa_payment_status": payment.yookassa_payment_status,
        "company_created": False,
        "company_id": None,
        "company_name": None,
        "email": None
    }
    
    # Если компания создана, добавляем её данные
    if payment.company_id:
        company_result = await db.execute(
            select(Company).where(Company.id == payment.company_id)
        )
        company = company_result.scalar_one_or_none()
        
        if company:
            response.update({
                "company_created": True,
                "company_id": company.id,
                "company_name": company.name,
                "email": company.email,
                "subscription_status": company.subscription_status,
                "can_create_bookings": company.can_create_bookings
            })
    
    return response


@router.get("/health")
async def public_health_check():
    """
    Проверка здоровья публичного API.
    
    Returns:
        Статус "ok"
    """
    return {"status": "ok"}


# Import settings после создания импортов
from app.config import settings

