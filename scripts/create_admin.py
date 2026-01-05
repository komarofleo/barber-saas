"""Скрипт создания администратора"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from shared.database.models import User
from bot.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_admin(telegram_id: int):
    """Создать или обновить администратора"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.is_admin = True
            print(f"✅ Пользователь {telegram_id} назначен администратором")
        else:
            user = User(
                telegram_id=telegram_id,
                is_admin=True,
                first_name="Admin",
            )
            session.add(user)
            print(f"✅ Создан новый администратор с Telegram ID {telegram_id}")

        await session.commit()


async def main():
    """Главная функция"""
    if len(sys.argv) < 3 or sys.argv[1] != "--telegram-id":
        print("Использование: python create_admin.py --telegram-id <TELEGRAM_ID>")
        sys.exit(1)

    telegram_id = int(sys.argv[2])
    await create_admin(telegram_id)


if __name__ == "__main__":
    asyncio.run(main())









