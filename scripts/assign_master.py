"""Скрипт назначения мастера пользователю"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import User, Master
from bot.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def assign_master(telegram_id: int, master_id: int = None):
    """Назначить пользователя мастером"""
    async with async_session_maker() as session:
        # Получаем пользователя
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            print(f"❌ Пользователь с Telegram ID {telegram_id} не найден")
            return

        # Если указан master_id, связываем с существующим мастером
        if master_id:
            result = await session.execute(
                select(Master).where(Master.id == master_id)
            )
            master = result.scalar_one_or_none()
            if not master:
                print(f"❌ Мастер с ID {master_id} не найден")
                return
            
            master.user_id = user.id
            master.telegram_id = telegram_id
            user.is_master = True
            print(f"✅ Пользователь {telegram_id} назначен мастером {master.full_name}")
        else:
            # Создаем нового мастера
            master = Master(
                user_id=user.id,
                telegram_id=telegram_id,
                full_name=user.first_name or f"Мастер {telegram_id}",
                is_universal=True,
            )
            session.add(master)
            user.is_master = True
            print(f"✅ Создан новый мастер для пользователя {telegram_id}")

        await session.commit()


async def list_masters():
    """Список всех мастеров"""
    async with async_session_maker() as session:
        result = await session.execute(select(Master))
        masters = result.scalars().all()
        
        if not masters:
            print("❌ Мастеров не найдено")
            return
        
        print("\n📋 Список мастеров:")
        for master in masters:
            user_info = f"User ID: {master.user_id}" if master.user_id else "Не привязан"
            print(f"  {master.id}. {master.full_name} - {user_info}")


async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python assign_master.py --telegram-id <TELEGRAM_ID> [--master-id <MASTER_ID>]")
        print("  python assign_master.py --list")
        print("\nПримеры:")
        print("  python assign_master.py --telegram-id 123456789")
        print("  python assign_master.py --telegram-id 123456789 --master-id 1")
        print("  python assign_master.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        await list_masters()
    elif sys.argv[1] == "--telegram-id":
        if len(sys.argv) < 3:
            print("❌ Укажите Telegram ID")
            sys.exit(1)
        
        telegram_id = int(sys.argv[2])
        master_id = None
        
        if len(sys.argv) > 4 and sys.argv[3] == "--master-id":
            master_id = int(sys.argv[4])
        
        await assign_master(telegram_id, master_id)
    else:
        print("❌ Неизвестная команда")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

