"""
Публичный API для регистрации новых компаний (простая версия без ORM).
Работает напрямую с БД через SQL запросы для избежания проблем с моделями.

⚠️ ВАЖНО: Этот файл временный! Обязательно нужно доделать:
1. Исправить архитектуру моделей public_models.py (проблема с __table_args__ и metadata)
2. Включить обратно полноценный public.py с ORM моделями
3. Протестировать все endpoints
4. Удалить этот файл после исправления
"""
import secrets
import httpx
import logging
from typing import List
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.schemas.public_schemas import (
    CompanyRegistration,
    RegistrationResponse,
    PlanResponse,
)
from app.services.yookassa_service import YooKassaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/public", tags=["public"])

yookassa_service = YooKassaService()


async def verify_bot_token(token: str) -> bool:
    """
    Проверить валидность токена бота через Telegram API.
    
    Args:
        token: Токен бота
        
    Returns:
        True если токен валиден, False если нет
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return True
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке токена бота: {e}")
        return False


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """
    Получить список активных тарифных планов.
    
    Returns:
        Список тарифных планов
    """
    try:
        result = await db.execute(
            text("""
                SELECT 
                    id, name, description, 
                    price_monthly, price_yearly,
                    max_bookings_per_month, max_users, max_masters,
                    max_posts, max_promotions, display_order, is_active
                FROM public.plans
                WHERE is_active = true
                ORDER BY display_order ASC
            """)
        )
        plans = result.fetchall()
        
        return [
            PlanResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                price_monthly=float(p.price_monthly),
                price_yearly=float(p.price_yearly),
                max_bookings_per_month=p.max_bookings_per_month,
                max_users=p.max_users,
                max_masters=p.max_masters,
                max_posts=p.max_posts,
                max_promotions=p.max_promotions,
                display_order=p.display_order,
                is_active=p.is_active
            )
            for p in plans
        ]
    except Exception as e:
        logger.error(f"Ошибка при получении тарифных планов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении тарифных планов"
        )


@router.post("/companies/register", response_model=RegistrationResponse, status_code=201)
async def register_company(company_data: CompanyRegistration, db: AsyncSession = Depends(get_db)):
    """
    Публичная регистрация новой компании.
    
    Проверяет токен бота, создает платеж через Юкассу,
    возвращает ссылку на оплату.
    
    Args:
        company_data: Данные для регистрации компании
        
    Returns:
        RegistrationResponse с данными о платеже
    """
    try:
        # 1. Проверяем валидность токена бота
        if not await verify_bot_token(company_data.telegram_bot_token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный токен бота. Проверьте его в BotFather."
            )
        
        # 2. Проверяем, что компания с таким email уже существует
        result = await db.execute(
            text("""
                SELECT id FROM public.companies 
                WHERE email = :email
                LIMIT 1
            """),
            {"email": company_data.email}
        )
        existing_company = result.fetchone()
        
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Компания с таким email уже существует"
            )
        
        # 3. Проверяем, что компания с таким токеном уже существует
        result = await db.execute(
            text("""
                SELECT id FROM public.companies 
                WHERE telegram_bot_token = :token
                LIMIT 1
            """),
            {"token": company_data.telegram_bot_token}
        )
        existing_token = result.fetchone()
        
        if existing_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Компания с таким токеном бота уже зарегистрирована"
            )
        
        # 4. Получаем тарифный план
        result = await db.execute(
            text("""
                SELECT id, name, price_monthly, price_yearly 
                FROM public.plans 
                WHERE id = :plan_id 
                LIMIT 1
            """),
            {"plan_id": company_data.plan_id}
        )
        plan = result.fetchone()
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тарифный план не найден"
            )
        
        # 5. Создаем платеж через Юкассу
        payment = await yookassa_service.create_payment(
            amount=float(plan.price_monthly),
            description=f"Подписка AutoService - {plan.name}"
        )
        
        # 6. Сохраняем информацию о компании
        # В реальном webhook handler создаст компанию после оплаты
        api_key = secrets.token_urlsafe(32)
        
        result = await db.execute(
            text("""
                INSERT INTO public.companies 
                (name, email, phone, telegram_bot_token, telegram_bot_username, 
                 plan_id, subscription_status, password_hash, api_key, 
                 webhook_url, is_active, is_blocked, created_at, updated_at)
                VALUES 
                (:name, :email, :phone, :token, :username, :plan_id, 
                 'pending', :password_hash, :api_key, :webhook_url, 
                 false, false, NOW(), NOW())
                RETURNING id
            """),
            {
                "name": company_data.name,
                "email": company_data.email,
                "phone": company_data.phone or "",
                "token": company_data.telegram_bot_token,
                "username": "",
                "plan_id": company_data.plan_id,
                "password_hash": "",
                "api_key": api_key,
                "webhook_url": settings.WEBHOOK_URL
            }
        )
        
        company_id = result.scalar()
        await db.commit()
        
        logger.info(f"Компания зарегистрирована: {company_data.name}, ID: {company_id}")
        
        return RegistrationResponse(
            company_id=company_id,
            payment_id=payment.id,
            confirmation_url=payment.confirmation_url,
            payment_status="pending",
            message="Платеж создан. Пожалуйста, оплатите подписку."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при регистрации компании: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get("/companies/{company_id}/exists")
async def check_company_exists(company_id: int, db: AsyncSession = Depends(get_db)):
    """
    Проверить, существует ли компания с указанным ID.
    
    Args:
        company_id: ID компании
        
    Returns:
        JSON с информацией о существовании компании
    """
    try:
        result = await db.execute(
            text("""
                SELECT id, name, is_active 
                FROM public.companies 
                WHERE id = :company_id
                LIMIT 1
            """),
            {"company_id": company_id}
        )
        company = result.fetchone()
        
        if company:
            return {
                "exists": True,
                "company_id": company.id,
                "name": company.name,
                "is_active": company.is_active
            }
        else:
            return {
                "exists": False,
                "company_id": company_id
            }
    except Exception as e:
        logger.error(f"Ошибка при проверке компании: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке компании"
        )
