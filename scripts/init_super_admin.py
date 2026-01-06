"""
Скрипт для создания дефолтного супер-администратора в базе данных.

Использование:
    cd web/backend
    python scripts/init_super_admin.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.public_models import SuperAdmin
from app.api.super_admin import get_password_hash


async def check_super_admin_exists(db: AsyncSession) -> bool:
    """
    Проверить, существует ли супер-администратор.
    
    Args:
        db: Сессия базы данных
        
    Returns:
        True, если супер-администратор существует, иначе False
    """
    result = await db.execute(select(SuperAdmin))
    admin = result.first()
    return admin is not None


async def create_super_admin(
    username: str = "admin",
    password: str = "admin123",
    email: str = "admin@autoservice-saas.com",
    telegram_id: int = None
) -> SuperAdmin:
    """
    Создать супер-администратора.
    
    Args:
        username: Имя пользователя
        password: Пароль
        email: Email адрес
        telegram_id: Telegram ID (опционально)
        
    Returns:
        Созданный супер-администратор
    """
    async for db in get_db():
        # Проверяем, существует ли уже супер-администратор
        if await check_super_admin_exists(db):
            result = await db.execute(select(SuperAdmin))
            existing_admin = result.scalar_one()
            
            print("⚠️  Супер-администратор уже существует!")
            print(f"   ID: {existing_admin.id}")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Telegram ID: {existing_admin.telegram_id}")
            print(f"   Active: {existing_admin.is_active}")
            print(f"   Created: {existing_admin.created_at}")
            print()
            return existing_admin
        
        # Создаем супер-администратора
        hashed_password = get_password_hash(password)
        
        super_admin = SuperAdmin(
            username=username,
            hashed_password=hashed_password,
            email=email,
            telegram_id=telegram_id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(super_admin)
        await db.commit()
        await db.refresh(super_admin)
        
        print("✅ Супер-администратор успешно создан!")
        print(f"   ID: {super_admin.id}")
        print(f"   Username: {super_admin.username}")
        print(f"   Email: {super_admin.email}")
        print(f"   Telegram ID: {super_admin.telegram_id}")
        print(f"   Active: {super_admin.is_active}")
        print(f"   Created: {super_admin.created_at}")
        print()
        
        return super_admin


async def main():
    """Главная функция скрипта."""
    print("=" * 60)
    print("Создание супер-администратора")
    print("=" * 60)
    print()
    
    # Создаем супер-администратора
    await create_super_admin(
        username="admin",
        password="admin123",
        email="admin@autoservice-saas.com",
        telegram_id=None
    )
    
    print("=" * 60)
    print("✅ Готово! Супер-администратор успешно создан.")
    print("=" * 60)
    print()
    print("Данные для входа:")
    print("  Username: admin")
    print("  Password: admin123")
    print()
    print("⚠️  Сохраните эти данные в безопасном месте!")
    print("⚠️  После входа рекомендуется сменить пароль.")
    print()


if __name__ == "__main__":
    asyncio.run(main())

