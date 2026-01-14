#!/usr/bin/env python3
"""
Скрипт для тестового создания платежа напрямую через БД.
Обходит проблему с enum статусами в public API.
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

async def test_create_payment():
    """Создать тестовый платеж напрямую через БД."""
    
    # Создаем engine для public схемы
    # Используем те же параметры, что и в docker-compose
    DATABASE_URL = "postgresql+asyncpg://postgres@postgres:5432/barber_db"
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        try:
            # Создаем платеж напрямую через SQL
            query = text("""
                INSERT INTO public.payments (
                    company_id, 
                    plan_id, 
                    subscription_id, 
                    amount, 
                    currency, 
                    status, 
                    yookassa_payment_id, 
                    yookassa_payment_status, 
                    yookassa_confirmation_url,
                    yookassa_return_url,
                    webhook_received_at,
                    webhook_signature_verified,
                    description,
                    extra_data,
                    updated_at
                ) VALUES (
                    :company_id,
                    :plan_id,
                    :subscription_id,
                    :amount,
                    :currency,
                    :status,
                    :yookassa_payment_id,
                    :yookassa_payment_status,
                    :yookassa_confirmation_url,
                    :yookassa_return_url,
                    NULL,
                    FALSE,
                    :description,
                    '{}'::jsonb,
                    NOW()
                )
                RETURNING id
            """)
            
            params = {
                'company_id': None,
                'plan_id': 1,
                'subscription_id': None,
                'amount': 2990.00,
                'currency': 'RUB',
                'status': 'pending',  # Используем строку напрямую
                'yookassa_payment_id': f'test_payment_{date.today()}',
                'yookassa_payment_status': 'pending',
                'yookassa_confirmation_url': 'https://yoomoney.ru/checkout/test',
                'yookassa_return_url': None,
                'description': 'Тестовый платеж для проверки',
            }
            
            result = await session.execute(query, params)
            payment_id = result.scalar()
            
            await session.commit()
            
            print(f"✅ Платеж успешно создан! ID: {payment_id}")
            return payment_id
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Ошибка создания платежа: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(test_create_payment())

