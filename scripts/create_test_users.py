"""Скрипт создания тестовых пользователей"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import User
from bot.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_test_users():
    """Создать тестовых пользователей"""
    async with async_session_maker() as session:
        test_users = [
            {
                "telegram_id": 100000001,
                "first_name": "Иван",
                "last_name": "Петров",
                "username": "ivan_petrov",
                "phone": "+7 (999) 111-11-11",
                "is_admin": False,
                "is_master": False
            },
            {
                "telegram_id": 100000002,
                "first_name": "Мария",
                "last_name": "Сидорова",
                "username": "maria_sidorova",
                "phone": "+7 (999) 222-22-22",
                "is_admin": False,
                "is_master": True
            },
            {
                "telegram_id": 100000003,
                "first_name": "Алексей",
                "last_name": "Смирнов",
                "username": "alex_smirnov",
                "phone": "+7 (999) 333-33-33",
                "is_admin": True,
                "is_master": False
            },
            {
                "telegram_id": 100000004,
                "first_name": "Елена",
                "last_name": "Козлова",
                "username": "elena_kozlova",
                "phone": "+7 (999) 444-44-44",
                "is_admin": False,
                "is_master": False
            },
            {
                "telegram_id": 100000005,
                "first_name": "Дмитрий",
                "last_name": "Волков",
                "username": "dmitry_volkov",
                "phone": "+7 (999) 555-55-55",
                "is_admin": False,
                "is_master": True
            },
        ]

        created_count = 0
        for user_data in test_users:
            result = await session.execute(
                select(User).where(User.telegram_id == user_data["telegram_id"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                user = User(**user_data)
                session.add(user)
                created_count += 1
                print(f"✅ Создан пользователь: {user_data['first_name']} {user_data['last_name']} (TG: {user_data['telegram_id']})")
            else:
                print(f"⏭️  Пользователь с TG ID {user_data['telegram_id']} уже существует")
        
        await session.commit()
        print(f"\n✅ Всего создано новых пользователей: {created_count}")


async def main():
    """Главная функция"""
    try:
        await create_test_users()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())









