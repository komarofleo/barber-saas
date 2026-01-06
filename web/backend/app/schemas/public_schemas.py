"""
Pydantic схемы для публичного API (регистрация компаний).

Этот модуль содержит схемы для валидации данных при регистрации
и создании компаний, платежей и подписок.
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum
import re


class PlanResponse(BaseModel):
    """Схема ответа с информацией о тарифном плане."""
    id: int
    name: str
    description: Optional[str] = None
    price_monthly: float
    price_yearly: float
    max_bookings_per_month: int
    max_users: int
    max_masters: int
    is_active: bool = True
    
    class Config:
        from_attributes = True


class SubscriptionStatus(str, Enum):
    """Статусы подписки."""
    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    PENDING = "pending"


class PaymentStatus(str, Enum):
    """Статусы платежей."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class CompanyRegistration(BaseModel):
    """
    Схема для регистрации новой компании.
    
    Включает все необходимые данные для создания автосервиса:
    - Контактная информация
    - Данные бота
    - Выбор тарифа
    """
    name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Название автосервиса"
    )
    email: EmailStr = Field(
        ...,
        description="Email для входа в админ-панель и получения уведомлений"
    )
    phone: str = Field(
        ...,
        max_length=20,
        pattern=r'^\+?7\d{10}$',
        description="Телефон в формате +7XXXXXXXXXX"
    )
    telegram_bot_token: str = Field(
        ...,
        min_length=30,
        max_length=500,
        description="Токен Telegram бота (получить через @BotFather)"
    )
    admin_telegram_id: int = Field(
        ...,
        ge=1,
        description="Telegram ID владельца для получения уведомлений"
    )
    plan_id: int = Field(
        ...,
        ge=1,
        description="ID тарифного плана (1=Starter, 2=Basic, 3=Business)"
    )
    
    @validator('phone')
    def validate_phone(cls, v):
        """Валидировать номер телефона."""
        if not re.match(r'^\+?7\d{10}$', v):
            raise ValueError('Телефон должен быть в формате +7XXXXXXXXXX')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "name": "ООО 'Точка'",
                "email": "admin@avtoservis.ru",
                "phone": "+79001234567",
                "telegram_bot_token": "8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4",
                "admin_telegram_id": 329621295,
                "plan_id": 3
            }
        }


class PaymentCreate(BaseModel):
    """
    Схема для создания платежа через Юкассу.
    
    Используется внутренне при регистрации компании.
    """
    company_id: Optional[int] = None
    plan_id: int = Field(..., ge=1)
    amount: float = Field(..., gt=0)
    description: str = Field(..., max_length=500)
    return_url: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "plan_id": 3,
                "amount": 5000.00,
                "description": "Подписка на тариф Business для автосервиса ООО 'Точка'",
                "return_url": "https://autoservice-saas.com/success"
            }
        }


class PaymentResponse(BaseModel):
    """Схема ответа с данными платежа."""
    id: int
    company_id: Optional[int] = None
    plan_id: int
    amount: float
    currency: str = "RUB"
    status: PaymentStatus
    description: str
    
    # Данные Юкассы
    yookassa_payment_id: str
    yookassa_confirmation_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    """
    Схема для создания подписки.
    
    Создается автоматически после успешной оплаты.
    """
    company_id: int = Field(..., ge=1)
    plan_id: int = Field(..., ge=1)
    start_date: date = Field(default_factory=date.today)
    end_date: date
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    
    class Config:
        schema_extra = {
            "example": {
                "company_id": 1,
                "plan_id": 3,
                "start_date": "2024-01-06",
                "end_date": "2024-02-05",
                "status": "active"
            }
        }


class SubscriptionResponse(BaseModel):
    """Схема ответа с информацией о подписке."""
    id: int
    company_id: int
    plan: PlanResponse
    start_date: date
    end_date: date
    status: SubscriptionStatus
    
    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    """Схема ответа с данными компании."""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    admin_telegram_id: Optional[int] = None
    plan_id: Optional[int] = None
    
    # Данные подписки
    plan: Optional[PlanResponse] = None
    subscription_status: Optional[SubscriptionStatus] = None
    can_create_bookings: bool = True
    subscription_end_date: Optional[date] = None
    
    # Метаданные
    is_active: bool
    created_at: datetime
    # updated_at убран из схемы, так как может быть None и не критичен для MVP
    
    # Дополнительные данные
    subscriptions: List[dict] = Field(default_factory=list)
    payments: List[dict] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    """
    Схема для создания компании после успешной оплаты.
    
    Используется внутренне при обработке webhook от Юкассы.
    """
    name: str = Field(..., min_length=3, max_length=255)
    email: str
    phone: Optional[str] = None
    telegram_bot_token: str = Field(..., min_length=50, max_length=500)
    admin_telegram_id: Optional[int] = None
    plan_id: int = Field(..., ge=1)
    password_hash: str = Field(..., min_length=60, max_length=255)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "ООО 'Точка'",
                "email": "admin@avtoservis.ru",
                "phone": "+79001234567",
                "telegram_bot_token": "8332803813:AAGOpLJdSj5P6cKqseQPfcOAiypTxgVZSt4",
                "admin_telegram_id": 329621295,
                "plan_id": 3,
                "password_hash": "$2b$12$..."
            }
        }


class YookassaWebhook(BaseModel):
    """
    Схема webhook от Юкассы.
    
    Используется для проверки и обработки уведомлений о платежах.
    """
    event: str = Field(..., description="Тип события (payment.succeeded, payment.canceled)")
    object_: dict = Field(..., alias="object", description="Данные платежа")
    
    class Config:
        populate_by_name = True


class WebhookVerificationResponse(BaseModel):
    """Схема ответа на webhook."""
    success: bool = True
    
    class Config:
        schema_extra = {
            "example": {"success": True}
        }


class WelcomeEmailData(BaseModel):
    """
    Данные для приветственного письма.
    
    Включает информацию о компании, креденшалах для входа.
    """
    company_name: str
    email: str
    password: str = Field(..., description="Пароль в открытом виде для email")
    dashboard_url: str
    plan_name: str
    subscription_end_date: date
    
    class Config:
        schema_extra = {
            "example": {
                "company_name": "ООО 'Точка'",
                "email": "admin@avtoservis.ru",
                "password": "AbCd1234XyZ",
                "dashboard_url": "https://autoservice-saas.com/company/001/dashboard",
                "plan_name": "Business",
                "subscription_end_date": "2024-02-05"
            }
        }


class RegistrationResponse(BaseModel):
    """
    Схема ответа на запрос регистрации компании.
    
    Возвращает ссылку на оплату через Юкассу.
    """
    success: bool = True
    payment_id: int
    confirmation_url: str
    message: str = "Платеж создан. Ожидает оплаты."
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "payment_id": 123,
                "confirmation_url": "https://yoomoney.ru/checkout/...",
                "message": "Платеж создан. Ожидает оплаты."
            }
        }


class TelegramNotificationData(BaseModel):
    """
    Данные для Telegram уведомления владельцу.
    
    Отправляет сообщение об успешной регистрации и активации.
    """
    telegram_id: int
    company_name: str
    plan_name: str
    subscription_end_date: date
    dashboard_url: str
    can_create_bookings: bool = True
    
    class Config:
        schema_extra = {
            "example": {
                "telegram_id": 329621295,
                "company_name": "ООО 'Точка'",
                "plan_name": "Business",
                "subscription_end_date": "2024-02-05",
                "dashboard_url": "https://autoservice-saas.com/company/001/dashboard",
                "can_create_bookings": True
            }
        }


class SuperAdminLogin(BaseModel):
    """Схема для входа супер-администратора."""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    
    class Config:
        schema_extra = {
            "example": {
                "username": "admin",
                "password": "admin123"
            }
        }


class SuperAdminResponse(BaseModel):
    """Схема ответа с данными супер-администратора."""
    id: int
    username: str
    email: str
    telegram_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

