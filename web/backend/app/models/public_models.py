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
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Date, Numeric, Text, ARRAY, func
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData
from sqlalchemy.dialects.postgresql import JSONB
import enum

# Импортируем Base и metadata из shared models
import sys
import os
# Правильный путь: от web/backend/app/models до shared = 4 уровня вверх
shared_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../shared'))
sys.path.insert(0, shared_path)
from shared.database.models import Base, public_metadata


class SubscriptionStatus(str, enum.Enum):
    """Статусы подписки."""
    ACTIVE = "active"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    PENDING = "pending"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class PaymentStatus(str, enum.Enum):
    """Статусы платежей."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"  # Исправлено: в БД используется "succeeded", а не "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


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
    telegram_bot_username = Column(String(100), nullable=True)
    admin_telegram_id = Column(Integer, nullable=True)
    telegram_admin_ids = Column(ARRAY(Integer), nullable=True)
    plan_id = Column(Integer, ForeignKey("public.plans.id"), nullable=True, index=True)
    subscription_status = Column(SQLEnum(SubscriptionStatus, name="subscriptionstatus"), default="pending", index=True)
    subscription_end_date = Column(Date, nullable=True, index=True)
    can_create_bookings = Column(Boolean, default=True)
    password_hash = Column(String(255), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(100), nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    webhook_url = Column(String(500), nullable=True)
    api_key = Column(String(100), nullable=True, unique=True)
    is_active = Column(Boolean, default=False, index=True)
    is_blocked = Column(Boolean, default=False)
    blocked_reason = Column(String(500), nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Отношения
    plan = relationship("Plan", back_populates="companies")
    subscriptions = relationship("Subscription", back_populates="company", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="company", cascade="all, delete-orphan")


class Plan(Base):
    """
    Модель тарифного плана в public схеме.
    
    Определяет ценовую политику и лимиты для автосервисов.
    """
    __tablename__ = "plans"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=True)
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_yearly = Column(Numeric(10, 2), nullable=False)
    max_bookings_per_month = Column(Integer, default=100)
    max_users = Column(Integer, default=10)
    max_masters = Column(Integer, default=5)
    max_posts = Column(Integer, default=10)
    max_promotions = Column(Integer, default=5)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Отношения
    companies = relationship("Company", back_populates="plan")
    subscriptions = relationship("Subscription", back_populates="plan")
    payments = relationship("Payment", back_populates="plan")


class Subscription(Base):
    """
    Модель подписки компании в public схеме.
    
    Связывает компанию с тарифным планом и отслеживает период действия подписки.
    """
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("public.companies.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("public.plans.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(SubscriptionStatus, name="subscriptionstatus"), default="active", index=True)
    trial_used = Column(Boolean, default=False)
    auto_renewal = Column(Boolean, default=False)
    extra_data = Column(JSONB, nullable=True)  # Переименовано из metadata (зарезервированное имя), тип JSONB
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Отношения
    company = relationship("Company", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")


class Payment(Base):
    """
    Модель платежа через Юкассу в public схеме.
    
    Отслеживает все платежи, связанные с подписками компаний.
    """
    __tablename__ = "payments"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("public.companies.id"), nullable=True, index=True)
    plan_id = Column(Integer, ForeignKey("public.plans.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("public.subscriptions.id"), nullable=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    status = Column(SQLEnum(PaymentStatus, name="paymentstatus"), default="pending", index=True)
    
    # Данные от Юкассы
    yookassa_payment_id = Column(String(100), unique=True, nullable=False, index=True)
    yookassa_payment_status = Column(String(50), nullable=True)
    yookassa_confirmation_url = Column(String(500), nullable=True)
    yookassa_return_url = Column(String(500), nullable=True)
    
    # Webhook данные
    webhook_payload = Column(Text, nullable=True)
    webhook_received_at = Column(DateTime(timezone=True), nullable=True)
    webhook_signature_verified = Column(Boolean, default=False)
    
    # Описание
    description = Column(String(500), nullable=True)
    extra_data = Column(JSONB, nullable=True)  # Переименовано из metadata (зарезервированное имя), тип JSONB
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Отношения
    company = relationship("Company", back_populates="payments")
    plan = relationship("Plan", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")  # Убран delete-orphan для many-to-one


class SuperAdmin(Base):
    """
    Модель супер-администратора в public схеме.
    
    Супер-администраторы имеют полный доступ ко всем компаниям.
    """
    __tablename__ = "super_admins"
    __table_args__ = {"schema": "public"}
    
    id = Column(Integer, primary_key=True)
    
    # Данные аккаунта
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Telegram
    telegram_id = Column(Integer, unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Права доступа
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Даты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
