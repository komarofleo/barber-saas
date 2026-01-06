"""
Скрипт для проверки и обновления пароля супер-админа.
"""

import asyncio
import sys
import os
import bcrypt

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings

async def fix_password():
    """Проверить и обновить пароль супер-админа."""
    
    # Создаем подключение к БД
    database_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_async_engine(database_url, echo=False)
    
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        # Получаем текущий хеш
        result = await session.execute(
            text("SELECT password_hash FROM super_admins WHERE username = 'admin'")
        )
        current_hash = result.scalar_one_or_none()
        
        if current_hash:
            print(f"Текущий хеш: {current_hash}")
            
            # Проверяем, соответствует ли пароль "admin123"
            test_password = "admin123"
            password_bytes = test_password.encode('utf-8')
            hash_bytes = current_hash.encode('utf-8')
            
            is_valid = bcrypt.checkpw(password_bytes, hash_bytes)
            print(f"Пароль 'admin123' валиден: {is_valid}")
            
            if not is_valid:
                print("Обновляю пароль на 'admin123'...")
                # Создаем новый хеш
                new_hash = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Обновляем в БД
                await session.execute(
                    text("UPDATE super_admins SET password_hash = :hash WHERE username = 'admin'"),
                    {"hash": new_hash}
                )
                await session.commit()
                print(f"Пароль обновлен! Новый хеш: {new_hash}")
            else:
                print("Пароль уже правильный!")
        else:
            print("Супер-админ не найден!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_password())

