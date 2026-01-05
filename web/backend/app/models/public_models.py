"""
Модели для public схемы (мульти-тенантность).

Этот модуль содержит модели для глобальных данных, общих для всех тенантов:
- Company - компании (автосервисы)
- Plan - тарифные планы
- Subscription - подписки компаний
- Payment - платежи через Юкассу
- SuperAdmin - супер-администраторы системы
"""

from datetime import date
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum


class SubscriptionStatus(str, enum.Enum):
    """Статусы подписки."""
    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    PENDING = "pending"


class PaymentStatus(str, enum.Enum):
    """Статусы платежей."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Company(Base):
    """
    Модель компании (автосервиса) в public схеме.
    
    Каждая компания имеет свою tenant схему с изолированными данными.
    """
    __tablename__ = "companies"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    telegram_bot_token = Column(String(500), nullable=False, unique=True)
    admin_telegram_id = Column(Integer, nullable=True)
    password_hash = Column(String(255), nullable=True)  # Хэшированный пароль
    
    # Поля подписки
    plan_id = Column(Integer, ForeignKey("public.plans.id"), nullable=True)
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING)
    can_create_bookings = Column(Boolean, default=True)
    subscription_end_date = Column(Date, nullable=True)
    
    # Метаданные
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    plan = relationship("Plan", back_populates="companies")
    subscriptions = relationship("Subscription", back_populates="company")
    payments = relationship("Payment", back_populates="company")


class Plan(Base):
    """
    Тарифные планы для подписок.
    
    Определяют стоимость и доступные возможности для разных уровней подписки.
    """
    __tablename__ = "plans"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    
    # Ценообразование
    price_monthly = Column(Numeric(10, 2), nullable=False)  # Цена за месяц
    price_yearly = Column(Numeric(10, 2), nullable=False)  # Цена за год
    
    # Лимиты и возможности
    max_bookings_per_month = Column(Integer, default=100)
    max_users = Column(Integer, default=10)
    max_masters = Column(Integer, default=5)
    is_active = Column(Boolean, default=True)
    
    # Порядок отображения
    display_order = Column(Integer, default=0)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    companies = relationship("Company", back_populates="plan")
    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    """
    Подписка компании на тарифный план.
    
    Отслеживает историю подписок и их статусы.
    """
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("public.companies.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("public.plans.id"), nullable=False, index=True)
    
    # Даты подписки
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Статус
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    company = relationship("Company", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")


class Payment(Base):
    """
    Платеж через Юкассу.
    
    Отслеживает все платежи и их статусы для интеграции с Юкассой.
    """
    __tablename__ = "payments"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("public.companies.id"), nullable=True, index=True)
    plan_id = Column(Integer, ForeignKey("public.plans.id"), nullable=False, index=True)
    
    # Данные платежа
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    
    # Статус платежа в нашей системе
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    
    # Данные от Юкассы
    yookassa_payment_id = Column(String(100), unique=True, index=True, nullable=False)
    yookassa_payment_status = Column(String(50), nullable=True)
    yookassa_confirmation_url = Column(String(500), nullable=True)
    yookassa_return_url = Column(String(500), nullable=True)
    
    # Webhook данные
    webhook_received_at = Column(DateTime(timezone=True), nullable=True)
    webhook_signature_verified = Column(Boolean, default=False)
    
    # Метаданные
    description = Column(String(500), nullable=True)
    metadata = Column(String(1000), nullable=True)  # JSON метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    company = relationship("Company", back_populates="payments")


class SuperAdmin(Base):
    """
    Супер-администратор системы.
    
    Имеет полный доступ ко всем данным системы и управлению компаниями.
    """
    __tablename__ = "super_admins"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Telegram для уведомлений
    telegram_id = Column(Integer, nullable=True, unique=True)
    
    # Права доступа
    is_active = Column(Boolean, default=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

