"""
Скрипт для создания дефолтного супер-администратора.

Использование:
    python scripts/create_super_admin.py --username admin --password admin123 --email admin@autoservice-saas.com
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Добавляем родительскую директорию в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.models.public_models import SuperAdmin
from app.api.super_admin import get_password_hash


async def create_super_admin(
    username: str,
    password: str,
    email: str,
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
        from sqlalchemy import select
        result = await db.execute(
            select(SuperAdmin).where(SuperAdmin.username == username)
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"❌ Супер-администратор с именем пользователя '{username}' уже существует")
            return None
        
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
        
        print(f"✅ Супер-администратор успешно создан!")
        print(f"   ID: {super_admin.id}")
        print(f"   Username: {super_admin.username}")
        print(f"   Email: {super_admin.email}")
        print(f"   Telegram ID: {super_admin.telegram_id}")
        print(f"   Created: {super_admin.created_at}")
        
        return super_admin


async def main():
    """Главная функция скрипта."""
    parser = argparse.ArgumentParser(description='Создать дефолтного супер-администратора')
    parser.add_argument('--username', type=str, default='admin', help='Имя пользователя')
    parser.add_argument('--password', type=str, default='admin123', help='Пароль')
    parser.add_argument('--email', type=str, default='admin@autoservice-saas.com', help='Email')
    parser.add_argument('--telegram-id', type=int, help='Telegram ID (опционально)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Создание супер-администратора")
    print("=" * 60)
    print()
    
    super_admin = await create_super_admin(
        username=args.username,
        password=args.password,
        email=args.email,
        telegram_id=args.telegram_id
    )
    
    if super_admin:
        print()
        print("=" * 60)
        print("✅ Готово! Супер-администратор успешно создан.")
        print("=" * 60)
        print()
        print("Данные для входа:")
        print(f"  Username: {args.username}")
        print(f"  Password: {args.password}")
        print()
        print("⚠️  Сохраните эти данные в безопасном месте!")
        print("⚠️  После входа рекомендуется сменить пароль.")
        print()


if __name__ == '__main__':
    asyncio.run(main())

