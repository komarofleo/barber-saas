"""Тестовый скрипт для проверки подключения к БД"""
import asyncio
from app.database import engine, async_session_maker
from sqlalchemy import text

async def test_db():
    """Проверить подключение к БД"""
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            print("✅ Подключение к БД успешно!")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_db())

