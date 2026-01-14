"""
Скрипт для обновления токена Telegram бота компании.

Использование:
    python scripts/update_company_bot_token.py <company_id> <bot_token> [bot_username]
    
Пример:
    python scripts/update_company_bot_token.py 8 8214331847:AAEV8pWvwvTNtlrRDBoNtu_w6ZLPmJMC25o barber77_1_bot
"""
import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к корневой директории проекта
sys.path.insert(0, str(Path(__file__).parent.parent / "web" / "backend"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, text
from app.config import settings
from app.models.public_models import Company


async def update_company_bot_token(company_id: int, bot_token: str, bot_username: str = None):
    """
    Обновить токен Telegram бота для компании.
    
    Args:
        company_id: ID компании
        bot_token: Токен Telegram бота
        bot_username: Username бота (опционально)
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
        print(f"   Текущий токен: {company.telegram_bot_token[:20] if company.telegram_bot_token else 'Нет'}...")
        
        # Обновляем токен
        company.telegram_bot_token = bot_token
        if bot_username:
            company.telegram_bot_username = bot_username
        
        await session.commit()
        await session.refresh(company)
        
        print(f"✅ Токен обновлен!")
        print(f"   Новый токен: {company.telegram_bot_token[:20]}...")
        if company.telegram_bot_username:
            print(f"   Username: {company.telegram_bot_username}")
        
        # Проверяем валидность токена через Telegram API
        print(f"\n🔍 Проверка валидности токена...")
        try:
            from aiogram import Bot
            bot = Bot(token=bot_token)
            bot_info = await bot.get_me()
            print(f"✅ Токен валиден!")
            print(f"   Бот: @{bot_info.username} ({bot_info.first_name})")
            await bot.session.close()
        except Exception as e:
            print(f"⚠️  Ошибка проверки токена: {e}")
    
    await engine.dispose()
    print(f"\n✅ Обновление завершено")


async def find_or_create_company(name: str, email: str, bot_token: str, bot_username: str = None):
    """
    Найти или создать компанию с указанными данными.
    
    Args:
        name: Название компании
        email: Email компании
        bot_token: Токен Telegram бота
        bot_username: Username бота (опционально)
    """
    print(f"🔍 Поиск компании '{name}'...")
    
    # Подключаемся к БД
    database_url = (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        # Ищем по токену
        result = await session.execute(
            select(Company).where(Company.telegram_bot_token == bot_token)
        )
        company = result.scalar_one_or_none()
        
        if company:
            print(f"✅ Компания найдена по токену:")
            print(f"   ID: {company.id}")
            print(f"   Название: {company.name}")
            print(f"   Email: {company.email}")
            return company.id
        
        # Ищем по email
        result = await session.execute(
            select(Company).where(Company.email == email)
        )
        company = result.scalar_one_or_none()
        
        if company:
            print(f"✅ Компания найдена по email:")
            print(f"   ID: {company.id}")
            print(f"   Название: {company.name}")
            print(f"   Обновляем токен...")
            company.telegram_bot_token = bot_token
            if bot_username:
                company.telegram_bot_username = bot_username
            await session.commit()
            return company.id
        
        # Создаем новую компанию
        print(f"📝 Создание новой компании...")
        company = Company(
            name=name,
            email=email,
            telegram_bot_token=bot_token,
            telegram_bot_username=bot_username,
            is_active=True,
            subscription_status='active'
        )
        session.add(company)
        await session.commit()
        await session.refresh(company)
        
        print(f"✅ Компания создана:")
        print(f"   ID: {company.id}")
        print(f"   Название: {company.name}")
        print(f"   Email: {company.email}")
        return company.id
    
    await engine.dispose()


async def main():
    """Главная функция."""
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python scripts/update_company_bot_token.py <company_id> <bot_token> [bot_username]")
        print("  python scripts/update_company_bot_token.py --create <name> <email> <bot_token> [bot_username]")
        print("\nПримеры:")
        print("  python scripts/update_company_bot_token.py 8 8214331847:AAEV8pWvwvTNtlrRDBoNtu_w6ZLPmJMC25o barber77_1_bot")
        print("  python scripts/update_company_bot_token.py --create 'Barber 77' 'barber77@test.com' 8214331847:AAEV8pWvwvTNtlrRDBoNtu_w6ZLPmJMC25o barber77_1_bot")
        sys.exit(1)
    
    if sys.argv[1] == "--create":
        # Создание новой компании
        if len(sys.argv) < 5:
            print("❌ Недостаточно аргументов для создания компании")
            sys.exit(1)
        
        name = sys.argv[2]
        email = sys.argv[3]
        bot_token = sys.argv[4]
        bot_username = sys.argv[5] if len(sys.argv) > 5 else None
        
        company_id = await find_or_create_company(name, email, bot_token, bot_username)
        if company_id:
            print(f"\n💡 Для тестирования бота используйте:")
            print(f"   python scripts/test_bot_messages.py {company_id} <telegram_user_id>")
        return
    
    company_id = int(sys.argv[1])
    bot_token = sys.argv[2]
    bot_username = sys.argv[3] if len(sys.argv) > 3 else None
    
    await update_company_bot_token(company_id, bot_token, bot_username)


if __name__ == "__main__":
    asyncio.run(main())
