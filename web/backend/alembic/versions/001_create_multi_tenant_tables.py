"""Миграция для создания таблиц мульти-тенантности в public схеме.

Создает следующие таблицы:
- companies - автосервисы
- plans - тарифные планы
- subscriptions - подписки компаний
- payments - платежи через Юкассу
- super_admins - супер-администраторы
"""

from alembic import op
import sqlalchemy as sa
from datetime import date

# Импорт моделей (они будут созданы в этой же миграции)
from app.models.public_models import Company, Plan, Subscription, Payment, SuperAdmin
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, ForeignKey, Enum as SQLEnum
from app.schemas.public_schemas import SubscriptionStatus, PaymentStatus
import enum


def upgrade():
    """Создать таблицы мульти-тенантности в public схеме."""
    
    # Таблица тарифных планов
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('price_monthly', sa.Numeric(10, 2), nullable=False),
        sa.Column('price_yearly', sa.Numeric(10, 2), nullable=False),
        sa.Column('max_bookings_per_month', sa.Integer(), default=100),
        sa.Column('max_users', sa.Integer(), default=10),
        sa.Column('max_masters', sa.Integer(), default=5),
        sa.Column('max_posts', sa.Integer(), default=10),
        sa.Column('max_promotions', sa.Integer(), default=5),
        sa.Column('display_order', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )
    
    # Таблица компаний
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('telegram_bot_token', sa.String(500), nullable=False, unique=True),
        sa.Column('telegram_bot_username', sa.String(100), nullable=True),
        sa.Column('admin_telegram_id', sa.Integer(), nullable=True),
        sa.Column('telegram_admin_ids', sa.ARRAY(sa.Integer()), nullable=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('plans.id'), nullable=True),
        sa.Column('subscription_status', sa.Enum(SubscriptionStatus, name='subscriptionstatus'), default='pending'),
        sa.Column('subscription_end_date', sa.Date(), nullable=True),
        sa.Column('can_create_bookings', sa.Boolean(), default=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_reset_token', sa.String(100), nullable=True),
        sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('api_key', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('is_blocked', sa.Boolean(), default=False),
        sa.Column('blocked_reason', sa.String(500), nullable=True),
        sa.Column('blocked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )
    
    # Таблица подписок
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, index=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('plans.id'), nullable=False, index=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum(SubscriptionStatus, name='subscriptionstatus'), default='active'),
        sa.Column('trial_used', sa.Boolean(), default=False),
        sa.Column('auto_renewal', sa.Boolean(), default=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )
    
    # Таблица платежей
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=True, index=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('plans.id'), nullable=False, index=True),
        sa.Column('subscription_id', sa.Integer(), sa.ForeignKey('subscriptions.id'), nullable=True, index=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), default='RUB', nullable=False),
        sa.Column('status', sa.Enum(PaymentStatus, name='paymentstatus'), default='pending'),
        
        # Данные от Юкассы
        sa.Column('yookassa_payment_id', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('yookassa_payment_status', sa.String(50), nullable=True),
        sa.Column('yookassa_confirmation_url', sa.String(500), nullable=True),
        sa.Column('yookassa_return_url', sa.String(500), nullable=True),
        
        # Webhook данные
        sa.Column('webhook_payload', sa.JSON(), nullable=True),
        sa.Column('webhook_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_signature_verified', sa.Boolean(), default=False),
        
        # Описание
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()'))
    )
    
    # Таблица супер-администраторов
    op.create_table(
        'super_admins',
        sa.Column('id', sa.Integer(), primary_key=True),
        
        # Данные аккаунта
        sa.Column('username', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        
        # Telegram
        sa.Column('telegram_id', sa.Integer(), nullable=True, unique=True),
        sa.Column('phone', sa.String(20), nullable=True),
        
        # Права доступа
        sa.Column('is_super_admin', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        
        # Даты
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
    )
    
    # Создание индексов для производительности
    op.create_index('companies', 'companies_email_key', unique=True)
    op.create_index('companies', 'companies_subscription_status_key')
    op.create_index('subscriptions', 'subscriptions_company_id_key')
    op.create_index('subscriptions', 'subscriptions_status_key')
    op.create_index('subscriptions', 'subscriptions_end_date_key')
    op.create_index('payments', 'payments_company_id_key')
    op.create_index('payments', 'payments_status_key')
    op.create_index('payments', 'payments_yookassa_payment_id_key', unique=True)


def downgrade():
    """Откатить миграцию."""
    
    # Удаляем индексы
    op.drop_index('payments_yookassa_payment_id_key')
    op.drop_index('payments_status_key')
    op.drop_index('payments_company_id_key')
    op.drop_index('subscriptions_end_date_key')
    op.drop_index('subscriptions_status_key')
    op.drop_index('subscriptions_company_id_key')
    op.drop_index('companies_subscription_status_key')
    op.drop_index('companies_email_key')
    
    # Удаляем таблицы в обратном порядке
    op.drop_table('super_admins')
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('companies')
    op.drop_table('plans')

