#!/usr/bin/env python3
"""
Скрипт для поиска пользователя по Telegram ID.
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к web/backend для импорта app
sys.path.insert(0, str(Path(__file__).parent / "web" / "backend"))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models.public_models import Company, SuperAdmin, User
from app.config import settings


async def find_user_by_telegram_id():
    """Найти пользователя по Telegram ID."""
    
    # 1. Проверяем в таблице компаний
    print("\n📊 Проверяем таблицу компаний...")
    async with AsyncSession(settings.asyncpg_url) as session:
        result = await session.execute(
            select(Company).where(Company.admin_telegram_id == 406407955)
        )
        company = result.scalar_one_or_none()
        
        if company:
            print(f"✅ Компания найдена:")
            print(f"   ID: {company.id}")
            print(f"   Название: {company.name}")
            print(f"   admin_telegram_id: {company.admin_telegram_id}")
        else:
            print("❌ Компания с admin_telegram_id = 406407955 не найдена")
    
    # 2. Проверяем в таблице супер-админов
    print("\n👤 Проверяем таблицу супер-админов...")
    async with AsyncSession(settings.asyncpg_url) as session:
        result = await session.execute(
            select(SuperAdmin).where(SuperAdmin.telegram_id == 406407955)
        )
        super_admin = result.scalar_one_or_none()
        
        if super_admin:
            print(f"✅ Супер-админ найден:")
            print(f"   ID: {super_admin.id}")
            print(f"   Username: {super_admin.username}")
            print(f"   Telegram ID: {super_admin.telegram_id}")
            print(f"   Email: {super_admin.email}")
            print(f"   Пароль: {super_admin.password_hash[:20]}...")
        else:
            print("❌ Супер-админ с telegram_id = 406407955 не найден")
    
    # 3. Проверяем в таблице public.users
    print("\n👥 Проверяем таблицу public.users...")
    async with AsyncSession(settings.asyncpg_url) as session:
        result = await session.execute(
            select(User).where(User.telegram_id == 406407955)
        )
        users = result.scalars().all()
        
        if users:
            print(f"✅ Пользователи в public.users найдены ({len(users)}):")
            for user in users:
                print(f"   - ID: {user.id}, telegram_id: {user.telegram_id}")
        else:
            print("❌ Пользователи в public.users с telegram_id = 406407955 не найдены")


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Поиск пользователя с Telegram ID: 406407955")
    print("=" * 60)
    
    asyncio.run(find_user_by_telegram_id())
