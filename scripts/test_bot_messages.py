"""
Скрипт для тестирования отправки сообщений через Telegram бот.

Использование:
    python scripts/test_bot_messages.py <company_id> <telegram_user_id> [message]
    
Пример:
    python scripts/test_bot_messages.py 8 123456789 "Тестовое сообщение"
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к корневой директории проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "web" / "backend"))

from aiogram import Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from app.config import settings
from app.models.public_models import Company


async def test_bot_message(company_id: int, telegram_user_id: int, message_text: str = "Тестовое сообщение от бота"):
    """
    Отправить тестовое сообщение через бот компании.
    
    Args:
        company_id: ID компании
        telegram_user_id: Telegram ID пользователя для отправки сообщения
        message_text: Текст сообщения
    """
    print(f"🔍 Поиск компании с ID {company_id}...")
    
    # Подключаемся к БД
    database_url = (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        # Получаем компанию
        result = await session.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        
        if not company:
            print(f"❌ Компания с ID {company_id} не найдена")
            return
        
        print(f"✅ Компания найдена: {company.name}")
        print(f"   Email: {company.email}")
        print(f"   Токен бота: {company.telegram_bot_token[:20]}...")
        print(f"   Активна: {company.is_active}")
        print(f"   Статус подписки: {company.subscription_status}")
        
        if not company.telegram_bot_token:
            print(f"❌ У компании нет токена Telegram бота")
            return
        
        if not company.is_active:
            print(f"⚠️  Компания не активна")
        
        # Создаем бота
        print(f"\n🤖 Создание бота...")
        bot = Bot(token=company.telegram_bot_token)
        
        try:
            # Получаем информацию о боте
            bot_info = await bot.get_me()
            print(f"✅ Бот создан: @{bot_info.username} ({bot_info.first_name})")
            
            # Отправляем тестовое сообщение
            print(f"\n📤 Отправка сообщения пользователю {telegram_user_id}...")
            print(f"   Текст: {message_text}")
            
            sent_message = await bot.send_message(
                chat_id=telegram_user_id,
                text=message_text
            )
            
            print(f"✅ Сообщение отправлено!")
            print(f"   Message ID: {sent_message.message_id}")
            print(f"   Дата: {sent_message.date}")
            
            # Отправляем еще одно сообщение с кнопками
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Тест кнопка 1", callback_data="test_1")],
                [InlineKeyboardButton(text="✅ Тест кнопка 2", callback_data="test_2")]
            ])
            
            print(f"\n📤 Отправка сообщения с кнопками...")
            sent_message2 = await bot.send_message(
                chat_id=telegram_user_id,
                text="Тестовое сообщение с кнопками",
                reply_markup=keyboard
            )
            
            print(f"✅ Сообщение с кнопками отправлено!")
            print(f"   Message ID: {sent_message2.message_id}")
            
        except Exception as e:
            print(f"❌ Ошибка при отправке сообщения: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await bot.session.close()
    
    await engine.dispose()
    print(f"\n✅ Тестирование завершено")


async def find_company_by_token(token: str):
    """Найти компанию по токену бота."""
    print(f"🔍 Поиск компании с токеном {token[:20]}...")
    
    database_url = (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(Company).where(Company.telegram_bot_token == token)
        )
        company = result.scalar_one_or_none()
        
        if company:
            print(f"✅ Компания найдена:")
            print(f"   ID: {company.id}")
            print(f"   Название: {company.name}")
            print(f"   Email: {company.email}")
            print(f"   Активна: {company.is_active}")
            print(f"   Статус подписки: {company.subscription_status}")
            return company.id
        else:
            print(f"❌ Компания с таким токеном не найдена")
            return None
    
    await engine.dispose()


async def main():
    """Главная функция."""
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python scripts/test_bot_messages.py <company_id> <telegram_user_id> [message]")
        print("  python scripts/test_bot_messages.py --find <bot_token>")
        print("\nПримеры:")
        print("  python scripts/test_bot_messages.py 8 123456789")
        print("  python scripts/test_bot_messages.py 8 123456789 'Привет! Это тестовое сообщение'")
        print("  python scripts/test_bot_messages.py --find 8214331847:AAEV8pWvwvTNtlrRDBoNtu_w6ZLPmJMC25o")
        sys.exit(1)
    
    if sys.argv[1] == "--find":
        # Поиск компании по токену
        token = sys.argv[2]
        company_id = await find_company_by_token(token)
        if company_id:
            print(f"\n💡 Для отправки сообщения используйте:")
            print(f"   python scripts/test_bot_messages.py {company_id} <telegram_user_id>")
        return
    
    company_id = int(sys.argv[1])
    telegram_user_id = int(sys.argv[2])
    message_text = sys.argv[3] if len(sys.argv) > 3 else "Тестовое сообщение от бота"
    
    await test_bot_message(company_id, telegram_user_id, message_text)


if __name__ == "__main__":
    asyncio.run(main())
