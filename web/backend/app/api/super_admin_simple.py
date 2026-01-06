"""
API для супер-администратора (упрощенная версия без ORM).
Работает напрямую с БД через SQL запросы для избежания проблем с моделями.

⚠️ ВАЖНО: Этот файл временный! Обязательно нужно доделать:
1. Исправить архитектуру моделей public_models.py
2. Включить обратно полноценный super_admin.py с ORM моделями
3. Протестировать все endpoints
4. Удалить этот файл после исправления
"""
import logging
from typing import List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from jose import jwt, JWTError
import bcrypt

from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])

# OAuth2 схема для авторизации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/super-admin/auth/login")


def create_access_token(data: dict) -> str:
    """Создать JWT токен для супер-администратора."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_super_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить текущего супер-администратора из JWT токена.
    
    Args:
        token: JWT токен
        db: Сессия БД
        
    Returns:
        Данные супер-администратора
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Получаем супер-администратора из БД
    result = await db.execute(
        text("""
            SELECT id, username, email, is_active, is_super_admin
            FROM public.super_admins
            WHERE username = :username AND is_active = true
            LIMIT 1
        """),
        {"username": username}
    )
    admin = result.fetchone()
    
    if admin is None:
        raise credentials_exception
    
    return {
        "id": admin.id,
        "username": admin.username,
        "email": admin.email,
        "is_active": admin.is_active,
        "is_super_admin": admin.is_super_admin
    }


@router.post("/auth/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Авторизация супер-администратора.
    
    Args:
        form_data: Данные формы (username, password)
        db: Сессия БД
        
    Returns:
        JWT токен и тип токена
    """
    # Получаем супер-администратора из БД
    result = await db.execute(
        text("""
            SELECT id, username, email, password_hash, is_active, is_super_admin
            FROM public.super_admins
            WHERE username = :username
            LIMIT 1
        """),
        {"username": form_data.username}
    )
    admin = result.fetchone()
    
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )
    
    # Проверяем пароль
    try:
        # Преобразуем пароль и хеш в bytes
        password_bytes = form_data.password.encode('utf-8')
        hash_bytes = admin.password_hash.encode('utf-8')
        
        if not bcrypt.checkpw(password_bytes, hash_bytes):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль"
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке пароля: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    # Создаем JWT токен
    access_token = create_access_token(data={"sub": admin.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": admin.id,
            "username": admin.username,
            "email": admin.email,
            "is_super_admin": admin.is_super_admin
        }
    }


@router.get("/auth/me")
async def get_me(current_admin: dict = Depends(get_current_super_admin)):
    """
    Получить информацию о текущем супер-администраторе.
    
    Args:
        current_admin: Текущий супер-администратор (из зависимости)
        
    Returns:
        Данные супер-администратора
    """
    return current_admin


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_admin: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику для дашборда супер-администратора.
    
    Args:
        current_admin: Текущий супер-администратор
        db: Сессия БД
        
    Returns:
        Статистика дашборда
    """
    try:
        # Общее количество компаний
        result = await db.execute(
            text("SELECT COUNT(*) as count FROM public.companies")
        )
        total_companies = result.scalar()
        
        # Активные компании
        result = await db.execute(
            text("SELECT COUNT(*) as count FROM public.companies WHERE is_active = true")
        )
        active_companies = result.scalar()
        
        # Компании с активной подпиской
        result = await db.execute(
            text("""
                SELECT COUNT(DISTINCT company_id) as count
                FROM public.subscriptions
                WHERE status = 'active' AND end_date >= CURRENT_DATE
            """)
        )
        companies_with_active_subscription = result.scalar()
        
        # Общая сумма платежей за месяц
        result = await db.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM public.payments
                WHERE status = 'succeeded'
                AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
            """)
        )
        monthly_revenue = result.scalar() or 0
        
        # Общая сумма платежей за все время
        result = await db.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0) as total
                FROM public.payments
                WHERE status = 'succeeded'
            """)
        )
        total_revenue = result.scalar() or 0
        
        # Платежи в ожидании
        result = await db.execute(
            text("""
                SELECT COUNT(*) as count
                FROM public.payments
                WHERE status = 'pending'
            """)
        )
        pending_payments = result.scalar()
        
        return {
            "total_companies": total_companies,
            "active_companies": active_companies,
            "companies_with_active_subscription": companies_with_active_subscription,
            "monthly_revenue": float(monthly_revenue),
            "total_revenue": float(total_revenue),
            "pending_payments": pending_payments
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики"
        )


@router.get("/companies")
async def get_companies(
    skip: int = 0,
    limit: int = 100,
    current_admin: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех компаний.
    
    Args:
        skip: Количество записей для пропуска
        limit: Максимальное количество записей
        current_admin: Текущий супер-администратор
        db: Сессия БД
        
    Returns:
        Список компаний
    """
    try:
        result = await db.execute(
            text("""
                SELECT 
                    c.id, c.name, c.email, c.phone,
                    c.is_active, c.is_blocked, c.subscription_status,
                    c.subscription_end_date, c.can_create_bookings,
                    c.created_at, c.updated_at,
                    p.name as plan_name
                FROM public.companies c
                LEFT JOIN public.plans p ON c.plan_id = p.id
                ORDER BY c.created_at DESC
                LIMIT :limit OFFSET :skip
            """),
            {"limit": limit, "skip": skip}
        )
        companies = result.fetchall()
        
        # Получаем общее количество
        result = await db.execute(
            text("SELECT COUNT(*) as count FROM public.companies")
        )
        total = result.scalar()
        
        return {
            "items": [
                {
                    "id": c.id,
                    "name": c.name,
                    "email": c.email,
                    "phone": c.phone,
                    "is_active": c.is_active,
                    "is_blocked": c.is_blocked,
                    "subscription_status": c.subscription_status,
                    "subscription_end_date": str(c.subscription_end_date) if c.subscription_end_date else None,
                    "can_create_bookings": c.can_create_bookings,
                    "plan_name": c.plan_name,
                    "created_at": str(c.created_at) if c.created_at else None,
                    "updated_at": str(c.updated_at) if c.updated_at else None
                }
                for c in companies
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка компаний: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка компаний"
        )


@router.get("/companies/{company_id}")
async def get_company(
    company_id: int,
    current_admin: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о компании.
    
    Args:
        company_id: ID компании
        current_admin: Текущий супер-администратор
        db: Сессия БД
        
    Returns:
        Детальная информация о компании
    """
    try:
        result = await db.execute(
            text("""
                SELECT 
                    c.*, p.name as plan_name, p.price_monthly, p.price_yearly
                FROM public.companies c
                LEFT JOIN public.plans p ON c.plan_id = p.id
                WHERE c.id = :company_id
                LIMIT 1
            """),
            {"company_id": company_id}
        )
        company = result.fetchone()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Компания не найдена"
            )
        
        # Получаем подписки компании
        result = await db.execute(
            text("""
                SELECT 
                    s.id, s.start_date, s.end_date, s.status,
                    s.auto_renewal, s.created_at,
                    p.name as plan_name
                FROM public.subscriptions s
                LEFT JOIN public.plans p ON s.plan_id = p.id
                WHERE s.company_id = :company_id
                ORDER BY s.created_at DESC
            """),
            {"company_id": company_id}
        )
        subscriptions = result.fetchall()
        
        # Получаем платежи компании
        result = await db.execute(
            text("""
                SELECT 
                    id, amount, currency, status,
                    yookassa_payment_id, yookassa_payment_status,
                    created_at, updated_at
                FROM public.payments
                WHERE company_id = :company_id
                ORDER BY created_at DESC
                LIMIT 10
            """),
            {"company_id": company_id}
        )
        payments = result.fetchall()
        
        return {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "phone": company.phone,
            "is_active": company.is_active,
            "is_blocked": company.is_blocked,
            "subscription_status": company.subscription_status,
            "subscription_end_date": str(company.subscription_end_date) if company.subscription_end_date else None,
            "can_create_bookings": company.can_create_bookings,
            "plan": {
                "id": company.plan_id,
                "name": company.plan_name,
                "price_monthly": float(company.price_monthly) if company.price_monthly else None,
                "price_yearly": float(company.price_yearly) if company.price_yearly else None
            } if company.plan_id else None,
            "subscriptions": [
                {
                    "id": s.id,
                    "start_date": str(s.start_date),
                    "end_date": str(s.end_date),
                    "status": s.status,
                    "auto_renewal": s.auto_renewal,
                    "plan_name": s.plan_name,
                    "created_at": str(s.created_at)
                }
                for s in subscriptions
            ],
            "payments": [
                {
                    "id": p.id,
                    "amount": float(p.amount),
                    "currency": p.currency,
                    "status": p.status,
                    "yookassa_payment_id": p.yookassa_payment_id,
                    "yookassa_payment_status": p.yookassa_payment_status,
                    "created_at": str(p.created_at),
                    "updated_at": str(p.updated_at)
                }
                for p in payments
            ],
            "created_at": str(company.created_at) if company.created_at else None,
            "updated_at": str(company.updated_at) if company.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о компании: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении информации о компании"
        )


@router.get("/payments")
async def get_payments(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех платежей.
    
    Args:
        skip: Количество записей для пропуска
        limit: Максимальное количество записей
        status_filter: Фильтр по статусу платежа
        current_admin: Текущий супер-администратор
        db: Сессия БД
        
    Returns:
        Список платежей
    """
    try:
        query = """
            SELECT 
                p.id, p.amount, p.currency, p.status,
                p.yookassa_payment_id, p.yookassa_payment_status,
                p.created_at, p.updated_at,
                c.name as company_name, c.email as company_email,
                pl.name as plan_name
            FROM public.payments p
            LEFT JOIN public.companies c ON p.company_id = c.id
            LEFT JOIN public.plans pl ON p.plan_id = pl.id
        """
        
        params = {"limit": limit, "skip": skip}
        
        if status_filter:
            query += " WHERE p.status = :status_filter"
            params["status_filter"] = status_filter
        
        query += " ORDER BY p.created_at DESC LIMIT :limit OFFSET :skip"
        
        result = await db.execute(text(query), params)
        payments = result.fetchall()
        
        # Получаем общее количество
        count_query = "SELECT COUNT(*) as count FROM public.payments"
        if status_filter:
            count_query += " WHERE status = :status_filter"
        
        result = await db.execute(text(count_query), {"status_filter": status_filter} if status_filter else {})
        total = result.scalar()
        
        return {
            "items": [
                {
                    "id": p.id,
                    "amount": float(p.amount),
                    "currency": p.currency,
                    "status": p.status,
                    "yookassa_payment_id": p.yookassa_payment_id,
                    "yookassa_payment_status": p.yookassa_payment_status,
                    "company_name": p.company_name,
                    "company_email": p.company_email,
                    "plan_name": p.plan_name,
                    "created_at": str(p.created_at) if p.created_at else None,
                    "updated_at": str(p.updated_at) if p.updated_at else None
                }
                for p in payments
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка платежей: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка платежей"
        )


@router.get("/subscriptions")
async def get_subscriptions(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_admin: dict = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех подписок.
    
    Args:
        skip: Количество записей для пропуска
        limit: Максимальное количество записей
        status_filter: Фильтр по статусу подписки
        current_admin: Текущий супер-администратор
        db: Сессия БД
        
    Returns:
        Список подписок
    """
    try:
        query = """
            SELECT 
                s.id, s.start_date, s.end_date, s.status,
                s.auto_renewal, s.created_at, s.updated_at,
                c.name as company_name, c.email as company_email,
                p.name as plan_name, p.price_monthly, p.price_yearly
            FROM public.subscriptions s
            LEFT JOIN public.companies c ON s.company_id = c.id
            LEFT JOIN public.plans p ON s.plan_id = p.id
        """
        
        params = {"limit": limit, "skip": skip}
        
        if status_filter:
            query += " WHERE s.status = :status_filter"
            params["status_filter"] = status_filter
        
        query += " ORDER BY s.created_at DESC LIMIT :limit OFFSET :skip"
        
        result = await db.execute(text(query), params)
        subscriptions = result.fetchall()
        
        # Получаем общее количество
        count_query = "SELECT COUNT(*) as count FROM public.subscriptions"
        if status_filter:
            count_query += " WHERE status = :status_filter"
        
        result = await db.execute(text(count_query), {"status_filter": status_filter} if status_filter else {})
        total = result.scalar()
        
        return {
            "items": [
                {
                    "id": s.id,
                    "start_date": str(s.start_date),
                    "end_date": str(s.end_date),
                    "status": s.status,
                    "auto_renewal": s.auto_renewal,
                    "company_name": s.company_name,
                    "company_email": s.company_email,
                    "plan_name": s.plan_name,
                    "plan_price_monthly": float(s.price_monthly) if s.price_monthly else None,
                    "plan_price_yearly": float(s.price_yearly) if s.price_yearly else None,
                    "created_at": str(s.created_at) if s.created_at else None,
                    "updated_at": str(s.updated_at) if s.updated_at else None
                }
                for s in subscriptions
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка подписок: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении списка подписок"
        )

