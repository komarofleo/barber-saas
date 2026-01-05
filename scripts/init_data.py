"""Скрипт инициализации начальных данных"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import (
    Service, Post, Master, User, Setting
)
from bot.config import DATABASE_URL

# Создаем движок
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_services(session: AsyncSession):
    """Создать услуги"""
    services_data = [
        {"name": "ТО", "description": "Техническое обслуживание автомобиля", "duration": 60, "price": Decimal("3000.00")},
        {"name": "Диагностика", "description": "Компьютерная диагностика", "duration": 30, "price": Decimal("1500.00")},
        {"name": "Ремонт двигателя", "description": "Ремонт и обслуживание двигателя", "duration": 60, "price": Decimal("5000.00")},
        {"name": "Шиномонтаж", "description": "Шиномонтаж и балансировка", "duration": 30, "price": Decimal("2000.00")},
        {"name": "Кузовной ремонт", "description": "Ремонт кузова", "duration": 60, "price": Decimal("8000.00")},
        {"name": "Электрика", "description": "Ремонт электрики", "duration": 60, "price": Decimal("4000.00")},
    ]

    for service_data in services_data:
        result = await session.execute(
            select(Service).where(Service.name == service_data["name"])
        )
        if not result.scalar_one_or_none():
            service = Service(**service_data)
            session.add(service)
    
    await session.commit()
    print("✅ Услуги созданы")


async def init_posts(session: AsyncSession):
    """Создать посты"""
    posts_data = [
        {"number": 1, "name": "Пост №1"},
        {"number": 2, "name": "Пост №2"},
        {"number": 3, "name": "Пост №3"},
        {"number": 4, "name": "Пост №4"},
        {"number": 5, "name": "Пост №5"},
    ]

    for post_data in posts_data:
        result = await session.execute(
            select(Post).where(Post.number == post_data["number"])
        )
        if not result.scalar_one_or_none():
            post = Post(**post_data)
            session.add(post)
    
    await session.commit()
    print("✅ Посты созданы")


async def init_masters(session: AsyncSession):
    """Создать мастеров"""
    masters_data = [
        {"full_name": "Иван Петров", "phone": "+79991234567", "telegram_id": None},
        {"full_name": "Петр Сидоров", "phone": "+79991234568", "telegram_id": None},
        {"full_name": "Мария Иванова", "phone": "+79991234569", "telegram_id": None},
        {"full_name": "Сергей Козлов", "phone": "+79991234570", "telegram_id": None},
        {"full_name": "Анна Смирнова", "phone": "+79991234571", "telegram_id": None},
    ]

    for master_data in masters_data:
        result = await session.execute(
            select(Master).where(Master.full_name == master_data["full_name"])
        )
        if not result.scalar_one_or_none():
            master = Master(**master_data, is_universal=True)
            session.add(master)
    
    await session.commit()
    print("✅ Мастера созданы")


async def init_settings(session: AsyncSession):
    """Создать настройки"""
    settings_data = [
        {"key": "accepting_bookings", "value": "true", "description": "Принимаются ли заявки (глобальная блокировка)"},
        {"key": "work_start_time", "value": "09:00", "description": "Время начала работы"},
        {"key": "work_end_time", "value": "18:00", "description": "Время окончания работы"},
        {"key": "slot_duration", "value": "30", "description": "Длительность слота в минутах"},
        {"key": "enable_master_specialization", "value": "false", "description": "Учитывать специализацию мастеров"},
        {"key": "reminder_day_before_time", "value": "18:00", "description": "Время напоминания за день"},
        {"key": "reminder_hour_before", "value": "true", "description": "Напоминание за час"},
        {"key": "notify_admin_delay_minutes", "value": "5", "description": "Задержка уведомления админу"},
        {"key": "work_order_time", "value": "08:00", "description": "Время отправки лист-наряда мастерам"},
    ]

    for setting_data in settings_data:
        result = await session.execute(
            select(Setting).where(Setting.key == setting_data["key"])
        )
        if not result.scalar_one_or_none():
            setting = Setting(**setting_data)
            session.add(setting)
    
    await session.commit()
    print("✅ Настройки созданы")


async def main():
    """Главная функция"""
    async with async_session_maker() as session:
        print("🚀 Инициализация начальных данных...")
        await init_services(session)
        await init_posts(session)
        await init_masters(session)
        await init_settings(session)
        print("✅ Инициализация завершена!")


if __name__ == "__main__":
    asyncio.run(main())

