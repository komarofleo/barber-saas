"""
API для супер-администратора.

Этот модуль содержит endpoints для:
- Авторизации супер-администратора
- Получения статистики дашборда
- Управления компаниями
- Управления подписками
- Управления платежами
"""

import logging
from typing import Annotated, List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, text
from sqlalchemy.orm import selectinload
from jose import jwt, JWTError
import bcrypt

from app.database import get_db
from app.models.public_models import (
    Company,
    Plan,
    Subscription,
    Payment,
    SuperAdmin,
    PaymentStatus,
    SubscriptionStatus
)
from app.schemas.public_schemas import (
    PlanResponse
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])

# OAuth2 схема для авторизации
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/super-admin/auth/login")


# ==================== Helper функции ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль.
    
    Args:
        plain_password: Введенный пароль
        hashed_password: Хешированный пароль
        
    Returns:
        True, если пароли совпадают, иначе False
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Ошибка при проверке пароля: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Получить хеш пароля.
    
    Args:
        password: Пароль
        
    Returns:
        Хешированный пароль
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode('utf-8')


def create_access_token(data: dict) -> str:
    """
    Создать JWT токен.
    
    Args:
        data: Данные для токена
        
    Returns:
        JWT токен
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm="HS256"  # Исправлено: используем HS256 вместо settings.ALGORITHM
    )
    return encoded_jwt


async def get_current_super_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> SuperAdmin:
    """
    Получить текущего супер-администратора по токену.
    
    Args:
        token: JWT токен
        db: Сессия базы данных
        
    Returns:
        Объект супер-администратора
        
    Raises:
        HTTPException, если токен неверный или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]  # Исправлено: используем HS256 вместо settings.ALGORITHM
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(
        select(SuperAdmin).where(SuperAdmin.username == username)
    )
    super_admin = result.scalar_one_or_none()
    
    if super_admin is None:
        raise credentials_exception
    
    return super_admin


# ==================== Pydantic схемы ====================

from pydantic import BaseModel, EmailStr, Field


class SuperAdminLogin(BaseModel):
    """Данные для входа супер-администратора"""
    username: str = Field(..., min_length=3, max_length=100, description="Имя пользователя")
    password: str = Field(..., min_length=6, max_length=100, description="Пароль")


class SuperAdminLoginResponse(BaseModel):
    """Ответ на запрос входа"""
    access_token: str
    token_type: str = "bearer"
    super_admin: dict


class DashboardStats(BaseModel):
    """Статистика дашборда"""
    total_companies: int = 0
    active_companies: int = 0
    total_subscriptions: int = 0
    active_subscriptions: int = 0
    total_revenue: Decimal = Decimal("0")
    monthly_revenue: Decimal = Decimal("0")
    companies_with_expiring_subscription: int = 0
    new_companies_this_month: int = 0


class CompanyResponse(BaseModel):
    """Ответ с данными компании"""
    id: int
    name: str
    email: str
    phone: Optional[str]
    telegram_bot_token: str
    admin_telegram_id: Optional[int]
    plan_id: Optional[int]
    subscription_status: Optional[str]
    can_create_bookings: bool
    subscription_end_date: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    plan: Optional[PlanResponse]
    subscriptions: List[dict]
    payments: List[dict]


class CompaniesResponse(BaseModel):
    """Ответ со списком компаний"""
    companies: List[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SubscriptionResponse(BaseModel):
    """Ответ с данными подписки"""
    id: int
    company_id: int
    plan: PlanResponse
    start_date: date
    end_date: date
    status: str


class PaymentResponse(BaseModel):
    """Ответ с данными платежа"""
    id: int
    company_id: Optional[int]
    plan_id: int
    amount: Decimal
    currency: str
    status: str
    description: Optional[str]
    yookassa_payment_id: str
    yookassa_confirmation_url: Optional[str]
    yookassa_payment_status: Optional[str]
    webhook_received_at: Optional[datetime]
    webhook_signature_verified: bool
    created_at: datetime


class CompanyUpdateData(BaseModel):
    """Данные для обновления компании"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    plan_id: Optional[int] = Field(None, ge=1)
    subscription_status: Optional[str] = Field(None, description="Статус подписки")
    can_create_bookings: Optional[bool] = None
    subscription_end_date: Optional[date] = None
    is_active: Optional[bool] = None


class ManualPaymentRequest(BaseModel):
    """Данные для создания ручного платежа"""
    company_id: int = Field(..., ge=1, description="ID компании")
    plan_id: int = Field(..., ge=1, description="ID тарифного плана")
    amount: Decimal = Field(..., ge=0, description="Сумма платежа")
    description: str = Field(..., min_length=1, max_length=255, description="Описание платежа")


# ==================== Авторизация ====================

@router.post("/auth/login", response_model=SuperAdminLoginResponse)
async def login(
    login_data: SuperAdminLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Войти в систему как супер-администратор.
    
    Проверяет логин и пароль, создает JWT токен и возвращает данные супер-админа.
    
    Args:
        login_data: Данные для входа
        db: Сессия базы данных
        
    Returns:
        Данные супер-админа и токен доступа
        
    Raises:
        HTTPException, если логин или пароль неверные
    """
    logger.info(f"Попытка входа супер-админа: {login_data.username}")
    
    # Ищем супер-админа
    result = await db.execute(
        select(SuperAdmin).where(SuperAdmin.username == login_data.username)
    )
    super_admin = result.scalar_one_or_none()
    
    if not super_admin:
        logger.warning(f"Супер-администратор не найден: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    # Проверяем пароль
    if not verify_password(login_data.password, super_admin.password_hash):
        logger.warning(f"Неверный пароль для супер-админа: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    # Проверяем, активен ли супер-администратор
    if not super_admin.is_active:
        logger.warning(f"Супер-администратор неактивен: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт супер-администратора отключен"
        )
    
    logger.info(f"Успешный вход супер-админа: {login_data.username}")
    
    # Создаем токен
    access_token = create_access_token(
        data={"sub": super_admin.username}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "super_admin": {
            "id": super_admin.id,
            "username": super_admin.username,
            "email": super_admin.email,
            "telegram_id": super_admin.telegram_id,
            "is_active": super_admin.is_active,
            "created_at": super_admin.created_at.isoformat(),
        }
    }


@router.post("/auth/logout")
async def logout(
    current_admin: SuperAdmin = Depends(get_current_super_admin)
):
    """
    Выйти из системы.
    
    Args:
        current_admin: Текущий супер-администратор
        
    Returns:
        Сообщение об успешном выходе
    """
    logger.info(f"Супер-администратор вышел: {current_admin.username}")
    return {"message": "Успешный выход из системы"}


# ==================== Статистика дашборда ====================

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить статистику дашборда.
    
    Возвращает:
    - Общее количество компаний
    - Количество активных компаний
    - Общее количество подписок
    - Количество активных подписок
    - Общий доход
    - Доход за текущий месяц
    - Количество компаний с истекающими подписками
    - Количество новых компаний за текущий месяц
    
    Args:
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Статистика дашборда
    """
    # Проверяем авторизацию
    if not current_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    logger.info(f"Получение статистики дашборда от: {current_admin.username}")
    
    # Общее количество компаний
    total_companies_result = await db.execute(
        select(func.count(Company.id))
    )
    total_companies = total_companies_result.scalar()
    
    # Количество активных компаний
    active_companies_result = await db.execute(
        select(func.count(Company.id)).where(Company.is_active == True)
    )
    active_companies = active_companies_result.scalar()
    
    # Общее количество подписок
    total_subscriptions_result = await db.execute(
        select(func.count(Subscription.id))
    )
    total_subscriptions = total_subscriptions_result.scalar()
    
    # Количество активных подписок
    active_subscriptions_result = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.status == 'active')
    )
    active_subscriptions = active_subscriptions_result.scalar()
    
    # Общий доход
    total_revenue_result = await db.execute(
        select(func.coalesce(Payment.amount, 0)).where(Payment.status == "succeeded")  # Исправлено: строка вместо enum
    )
    total_revenue = Decimal(str(total_revenue_result.scalar() or 0))
    
    # Доход за текущий месяц
    current_month_start = date.today().replace(day=1)
    monthly_revenue_result = await db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            and_(
                Payment.status == "succeeded",  # Исправлено: строка вместо enum
                Payment.created_at >= current_month_start
            )
        )
    )
    monthly_revenue = Decimal(str(monthly_revenue_result.scalar() or 0))
    
    # Компании с истекающими подписками (через 7 дней)
    expiring_date = date.today() + timedelta(days=7)
    expiring_companies_result = await db.execute(
        text("""
            SELECT COUNT(*) as count 
            FROM public.companies 
            WHERE is_active = true 
            AND subscription_end_date <= :expiring_date
            AND subscription_end_date >= :today
            AND subscription_status = 'active'
        """),
        {"expiring_date": expiring_date, "today": date.today()}
    )
    companies_with_expiring_subscription = expiring_companies_result.scalar()
    
    # Новые компании за текущий месяц
    new_companies_result = await db.execute(
        select(func.count(Company.id)).where(
            Company.created_at >= current_month_start
        )
    )
    new_companies_this_month = new_companies_result.scalar()
    
    return DashboardStats(
        total_companies=total_companies or 0,
        active_companies=active_companies or 0,
        total_subscriptions=total_subscriptions or 0,
        active_subscriptions=active_subscriptions or 0,
        total_revenue=total_revenue,
        monthly_revenue=monthly_revenue,
        companies_with_expiring_subscription=companies_with_expiring_subscription or 0,
        new_companies_this_month=new_companies_this_month or 0
    )


# ==================== Управление компаниями ====================

@router.get("/companies", response_model=CompaniesResponse)
async def get_companies(
    search: Optional[str] = None,
    subscription_status: Optional[str] = None,
    is_active: Optional[bool] = None,
    plan_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список компаний с фильтрацией и пагинацией.
    
    Args:
        search: Поиск по названию или email
        subscription_status: Фильтр по статусу подписки
        is_active: Фильтр по активности компании
        plan_id: Фильтр по тарифному плану
        page: Номер страницы
        page_size: Количество элементов на странице
        sort_by: Поле сортировки
        sort_order: Порядок сортировки (asc/desc)
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Список компаний с пагинацией
    """
    logger.info(f"Получение списка компаний от: {current_admin.username}")
    
    # Базовый запрос
    query = select(Company)
    
    # Загружаем связанные данные
    query = query.options(
        selectinload(Company.plan),
        selectinload(Company.subscriptions).selectinload(Subscription.plan),
        selectinload(Company.payments)
    )
    
    # Применяем фильтры
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Company.name.ilike(search_pattern),
                Company.email.ilike(search_pattern)
            )
        )
    
    if subscription_status:
        query = query.where(Company.subscription_status == subscription_status)
    
    if is_active is not None:
        query = query.where(Company.is_active == is_active)
    
    if plan_id:
        query = query.where(Company.plan_id == plan_id)
    
    # Сортировка
    sort_column = getattr(Company, sort_by, Company.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Получаем общее количество
    total_result = await db.execute(
        select(func.count(Company.id)).where(
            query.whereclause
        )
    )
    total = total_result.scalar() or 0
    
    # Пагинация
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Выполняем запрос
    result = await db.execute(query)
    companies = result.scalars().all()
    
    # Формируем ответ
    company_responses = []
    for company in companies:
        company_data = {
            "id": company.id,
            "name": company.name,
            "email": company.email,
            "phone": company.phone,
            "telegram_bot_token": company.telegram_bot_token,
            "admin_telegram_id": company.admin_telegram_id,
            "plan_id": company.plan_id,
            "subscription_status": company.subscription_status,
            "can_create_bookings": company.can_create_bookings,
            "subscription_end_date": company.subscription_end_date,
            "is_active": company.is_active,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
            "plan": None,
            "subscriptions": [],
            "payments": []
        }
        
        if company.plan:
            company_data["plan"] = {
                "id": company.plan.id,
                "name": company.plan.name,
                "description": company.plan.description,
                "price_monthly": company.plan.price_monthly,
                "price_yearly": company.plan.price_yearly,
                "max_bookings_per_month": company.plan.max_bookings_per_month,
                "max_users": company.plan.max_users,
                "max_masters": company.plan.max_masters,
                "is_active": company.plan.is_active,
                "display_order": company.plan.display_order
            }
        
        for subscription in company.subscriptions:
            company_data["subscriptions"].append({
                "id": subscription.id,
                "company_id": subscription.company_id,
                "plan": {
                    "id": subscription.plan.id,
                    "name": subscription.plan.name,
                    "description": subscription.plan.description,
                    "price_monthly": subscription.plan.price_monthly,
                    "price_yearly": subscription.plan.price_yearly,
                    "max_bookings_per_month": subscription.plan.max_bookings_per_month,
                    "max_users": subscription.plan.max_users,
                    "max_masters": subscription.plan.max_masters,
                    "is_active": subscription.plan.is_active,
                    "display_order": subscription.plan.display_order
                },
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
                "status": subscription.status
            })
        
        for payment in company.payments:
            company_data["payments"].append({
                "id": payment.id,
                "company_id": payment.company_id,
                "plan_id": payment.plan_id,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "description": payment.description,
                "yookassa_payment_id": payment.yookassa_payment_id,
                "yookassa_confirmation_url": payment.yookassa_confirmation_url,
                "yookassa_payment_status": payment.yookassa_payment_status,
                "webhook_received_at": payment.webhook_received_at,
                "webhook_signature_verified": payment.webhook_signature_verified,
                "created_at": payment.created_at
            })
        
        company_responses.append(CompanyResponse(**company_data))
    
    total_pages = (total + page_size - 1) // page_size
    
    return CompaniesResponse(
        companies=company_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить детальную информацию о компании.
    
    Args:
        company_id: ID компании
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Детальная информация о компании
        
    Raises:
        HTTPException, если компания не найдена
    """
    logger.info(f"Получение компании {company_id} от: {current_admin.username}")
    
    result = await db.execute(
        select(Company)
        .options(
            selectinload(Company.plan),
            selectinload(Company.subscriptions).selectinload(Subscription.plan),
            selectinload(Company.payments)
        )
        .where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        logger.warning(f"Компания не найдена: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )
    
    company_data = {
        "id": company.id,
        "name": company.name,
        "email": company.email,
        "phone": company.phone,
        "telegram_bot_token": company.telegram_bot_token,
        "admin_telegram_id": company.admin_telegram_id,
        "plan_id": company.plan_id,
        "subscription_status": company.subscription_status,
        "can_create_bookings": company.can_create_bookings,
        "subscription_end_date": company.subscription_end_date,
        "is_active": company.is_active,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "plan": None,
        "subscriptions": [],
        "payments": []
    }
    
    if company.plan:
        company_data["plan"] = {
            "id": company.plan.id,
            "name": company.plan.name,
            "description": company.plan.description,
            "price_monthly": company.plan.price_monthly,
            "price_yearly": company.plan.price_yearly,
            "max_bookings_per_month": company.plan.max_bookings_per_month,
            "max_users": company.plan.max_users,
            "max_masters": company.plan.max_masters,
            "is_active": company.plan.is_active,
            "display_order": company.plan.display_order
        }
    
    for subscription in company.subscriptions:
        company_data["subscriptions"].append({
            "id": subscription.id,
            "company_id": subscription.company_id,
            "plan": {
                "id": subscription.plan.id,
                "name": subscription.plan.name,
                "description": subscription.plan.description,
                "price_monthly": subscription.plan.price_monthly,
                "price_yearly": subscription.plan.price_yearly,
                "max_bookings_per_month": subscription.plan.max_bookings_per_month,
                "max_users": subscription.plan.max_users,
                "max_masters": subscription.plan.max_masters,
                "is_active": subscription.plan.is_active,
                "display_order": subscription.plan.display_order
            },
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "status": subscription.status
        })
    
    for payment in company.payments:
        company_data["payments"].append({
            "id": payment.id,
            "company_id": payment.company_id,
            "plan_id": payment.plan_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "description": payment.description,
            "yookassa_payment_id": payment.yookassa_payment_id,
            "yookassa_confirmation_url": payment.yookassa_confirmation_url,
            "yookassa_payment_status": payment.yookassa_payment_status,
            "webhook_received_at": payment.webhook_received_at,
            "webhook_signature_verified": payment.webhook_signature_verified,
            "created_at": payment.created_at
        })
    
    return CompanyResponse(**company_data)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    update_data: CompanyUpdateData,
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Обновить информацию о компании.
    
    Args:
        company_id: ID компании
        update_data: Данные для обновления
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Обновленная компания
        
    Raises:
        HTTPException, если компания не найдена или данные неверные
    """
    logger.info(f"Обновление компании {company_id} от: {current_admin.username}")
    
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        logger.warning(f"Компания не найдена для обновления: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )
    
    # Обновляем только предоставленные поля
    if update_data.name is not None:
        company.name = update_data.name
    
    if update_data.email is not None:
        company.email = update_data.email
    
    if update_data.phone is not None:
        company.phone = update_data.phone
    
    if update_data.plan_id is not None:
        company.plan_id = update_data.plan_id
    
    if update_data.subscription_status is not None:
        company.subscription_status = update_data.subscription_status
    
    if update_data.can_create_bookings is not None:
        company.can_create_bookings = update_data.can_create_bookings
    
    if update_data.subscription_end_date is not None:
        company.subscription_end_date = update_data.subscription_end_date
    
    if update_data.is_active is not None:
        company.is_active = update_data.is_active
    
    company.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(company)
    
    logger.info(f"Компания {company_id} успешно обновлена")
    
    # Формируем ответ
    return await get_company(company_id, current_admin, db)


@router.patch("/companies/{company_id}/deactivate")
async def deactivate_company(
    company_id: int,
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Деактивировать компанию.
    
    Args:
        company_id: ID компании
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Деактивированная компания
        
    Raises:
        HTTPException, если компания не найдена или уже деактивирована
    """
    logger.info(f"Деактивация компании {company_id} от: {current_admin.username}")
    
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        logger.warning(f"Компания не найдена для деактивации: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )
    
    if not company.is_active:
        logger.warning(f"Компания уже деактивирована: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Компания уже деактивирована"
        )
    
    company.is_active = False
    company.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(company)
    
    logger.info(f"Компания {company_id} успешно деактивирована")
    
    return {"message": "Компания успешно деактивирована", "company_id": company_id}


@router.get("/companies/{company_id}/subscriptions", response_model=List[SubscriptionResponse])
async def get_company_subscriptions(
    company_id: int,
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить подписки компании.
    
    Args:
        company_id: ID компании
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Список подписок компании
        
    Raises:
        HTTPException, если компания не найдена
    """
    logger.info(f"Получение подписок компании {company_id} от: {current_admin.username}")
    
    # Проверяем существование компании
    company_result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = company_result.scalar_one_or_none()
    
    if not company:
        logger.warning(f"Компания не найдена: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )
    
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.company_id == company_id)
        .order_by(Subscription.end_date.desc())
    )
    subscriptions = result.scalars().all()
    
    subscription_responses = []
    for subscription in subscriptions:
        subscription_responses.append(SubscriptionResponse(
            id=subscription.id,
            company_id=subscription.company_id,
            plan=PlanResponse(
                id=subscription.plan.id,
                name=subscription.plan.name,
                description=subscription.plan.description,
                price_monthly=subscription.plan.price_monthly,
                price_yearly=subscription.plan.price_yearly,
                max_bookings_per_month=subscription.plan.max_bookings_per_month,
                max_users=subscription.plan.max_users,
                max_masters=subscription.plan.max_masters,
                is_active=subscription.plan.is_active,
                display_order=subscription.plan.display_order
            ),
            start_date=subscription.start_date,
            end_date=subscription.end_date,
            status=subscription.status
        ))
    
    return subscription_responses


@router.get("/companies/{company_id}/payments", response_model=List[PaymentResponse])
async def get_company_payments(
    company_id: int,
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить платежи компании.
    
    Args:
        company_id: ID компании
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Список платежей компании
        
    Raises:
        HTTPException, если компания не найдена
    """
    logger.info(f"Получение платежей компании {company_id} от: {current_admin.username}")
    
    # Проверяем существование компании
    company_result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = company_result.scalar_one_or_none()
    
    if not company:
        logger.warning(f"Компания не найдена: {company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )
    
    result = await db.execute(
        select(Payment)
        .where(Payment.company_id == company_id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    
    payment_responses = []
    for payment in payments:
        payment_responses.append(PaymentResponse(
            id=payment.id,
            company_id=payment.company_id,
            plan_id=payment.plan_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            description=payment.description,
            yookassa_payment_id=payment.yookassa_payment_id,
            yookassa_confirmation_url=payment.yookassa_confirmation_url,
            yookassa_payment_status=payment.yookassa_payment_status,
            webhook_received_at=payment.webhook_received_at,
            webhook_signature_verified=payment.webhook_signature_verified,
            created_at=payment.created_at
        ))
    
    return payment_responses


@router.post("/companies/manual-payment", response_model=PaymentResponse)
async def create_manual_payment(
    payment_data: ManualPaymentRequest,
    current_admin: SuperAdmin = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Создать ручной платеж.
    
    Args:
        payment_data: Данные для создания платежа
        current_admin: Текущий супер-администратор
        db: Сессия базы данных
        
    Returns:
        Созданный платеж
        
    Raises:
        HTTPException, если данные неверные или компания не найдена
    """
    logger.info(f"Создание ручного платежа для компании {payment_data.company_id} от: {current_admin.username}")
    
    # Проверяем существование компании
    company_result = await db.execute(
        select(Company).where(Company.id == payment_data.company_id)
    )
    company = company_result.scalar_one_or_none()
    
    if not company:
        logger.warning(f"Компания не найдена для создания платежа: {payment_data.company_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена"
        )
    
    # Создаем платеж
    payment = Payment(
        company_id=payment_data.company_id,
        plan_id=payment_data.plan_id,
        amount=payment_data.amount,
        currency="RUB",
        status="succeeded",  # Исправлено: используем строку "succeeded" вместо enum
        description=payment_data.description,
        yookassa_payment_id=f"manual_{datetime.utcnow().timestamp()}",
        yookassa_payment_status="succeeded",  # Исправлено: используем succeeded вместо completed
        webhook_received_at=datetime.utcnow(),
        webhook_signature_verified=True,
        created_at=datetime.utcnow()
    )
    
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    logger.info(f"Ручной платеж успешно создан для компании {payment_data.company_id}")
    
    return PaymentResponse(
        id=payment.id,
        company_id=payment.company_id,
        plan_id=payment.plan_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        description=payment.description,
        yookassa_payment_id=payment.yookassa_payment_id,
        yookassa_confirmation_url=payment.yookassa_confirmation_url,
        yookassa_payment_status=payment.yookassa_payment_status,
        webhook_received_at=payment.webhook_received_at,
        webhook_signature_verified=payment.webhook_signature_verified,
        created_at=payment.created_at
    )

