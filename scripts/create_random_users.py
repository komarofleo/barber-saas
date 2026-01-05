"""Скрипт создания случайных пользователей"""
import asyncio
import sys
import random
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import User
from bot.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Списки для генерации случайных данных
FIRST_NAMES = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Артем", "Илья", "Кирилл", "Михаил",
               "Анна", "Мария", "Елена", "Ольга", "Татьяна", "Наталья", "Ирина", "Светлана", "Екатерина", "Юлия"]
LAST_NAMES = ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев", "Козлов", "Новиков",
              "Иванова", "Петрова", "Сидорова", "Смирнова", "Кузнецова", "Попова", "Соколова", "Лебедева", "Козлова", "Новикова"]
PHONE_PREFIXES = ["+7999", "+7998", "+7997", "+7996", "+7995"]


async def create_random_users():
    """Создать случайных пользователей"""
    async with async_session_maker() as session:
        # Получаем максимальный telegram_id
        result = await session.execute(select(User.telegram_id).order_by(User.telegram_id.desc()).limit(1))
        max_id = result.scalar_one_or_none()
        start_id = (max_id or 100000000) + 1
        
        created_count = 0
        for i in range(5):
            telegram_id = start_id + i
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            username = f"{first_name.lower()}_{last_name.lower()}_{telegram_id % 10000}"
            phone = f"{random.choice(PHONE_PREFIXES)}{random.randint(1000000, 9999999)}"
            
            # Случайно определяем роли (большинство - заказчики)
            roles = random.choices(
                ["customer", "admin", "master"],
                weights=[70, 15, 15]
            )[0]
            
            is_admin = roles == "admin"
            is_master = roles == "master"
            
            # Проверяем, существует ли пользователь
            existing = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            if existing.scalar_one_or_none():
                print(f"⏭️  Пользователь с TG ID {telegram_id} уже существует")
                continue
            
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                phone=phone,
                is_admin=is_admin,
                is_master=is_master
            )
            session.add(user)
            created_count += 1
            
            role_name = "Админ" if is_admin else ("Мастер" if is_master else "Заказчик")
            print(f"✅ Создан пользователь: {first_name} {last_name} (TG: {telegram_id}, роль: {role_name})")
        
        await session.commit()
        print(f"\n✅ Всего создано новых пользователей: {created_count}")


async def main():
    """Главная функция"""
    try:
        await create_random_users()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())









