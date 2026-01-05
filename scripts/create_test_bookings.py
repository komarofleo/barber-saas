"""Скрипт создания тестовых записей"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import Booking, Client, Service, Master, Post, User
from bot.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_test_bookings():
    """Создать тестовые записи"""
    async with async_session_maker() as session:
        # Получаем существующих клиентов
        clients_result = await session.execute(select(Client).limit(5))
        clients = clients_result.scalars().all()
        
        # Если клиентов нет, создаем их из пользователей
        if not clients:
            users_result = await session.execute(select(User).limit(5))
            users = users_result.scalars().all()
            
            for i, user in enumerate(users):
                client = Client(
                    user_id=user.id,
                    full_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or f"Клиент {user.telegram_id}",
                    phone=user.phone or f"+7999{1000000 + user.telegram_id}",
                    car_brand="Toyota",
                    car_model="Camry",
                    car_number=f"А{100 + i}БВ777"
                )
                session.add(client)
            await session.commit()
            await session.refresh(client)
            
            clients_result = await session.execute(select(Client).limit(5))
            clients = clients_result.scalars().all()
        
        # Получаем услуги
        services_result = await session.execute(select(Service).limit(5))
        services = services_result.scalars().all()
        
        # Получаем мастеров
        masters_result = await session.execute(select(Master).limit(5))
        masters = masters_result.scalars().all()
        
        # Получаем посты
        posts_result = await session.execute(select(Post).limit(5))
        posts = posts_result.scalars().all()
        
        # Получаем админа для created_by
        admin_result = await session.execute(select(User).where(User.is_admin == True).limit(1))
        admin = admin_result.scalar_one_or_none()
        if not admin:
            admin_result = await session.execute(select(User).limit(1))
            admin = admin_result.scalar_one_or_none()
        
        if not clients or not services:
            print("❌ Недостаточно данных: нужны клиенты и услуги")
            return
        
        # Создаем тестовые записи
        today = date.today()
        test_bookings = [
            {
                "booking_number": f"BK-{today.strftime('%Y%m%d')}-0001",
                "client_id": clients[0].id if len(clients) > 0 else None,
                "service_id": services[0].id if len(services) > 0 else None,
                "master_id": masters[0].id if len(masters) > 0 else None,
                "post_id": posts[0].id if len(posts) > 0 else None,
                "date": today,
                "time": time(10, 0),
                "duration": services[0].duration if len(services) > 0 else 30,
                "end_time": time(10, 30),
                "status": "new",
                "created_by": admin.id if admin else None
            },
            {
                "booking_number": f"BK-{today.strftime('%Y%m%d')}-0002",
                "client_id": clients[1].id if len(clients) > 1 else clients[0].id,
                "service_id": services[1].id if len(services) > 1 else services[0].id,
                "master_id": masters[1].id if len(masters) > 1 else (masters[0].id if len(masters) > 0 else None),
                "post_id": posts[1].id if len(posts) > 1 else (posts[0].id if len(posts) > 0 else None),
                "date": today + timedelta(days=1),
                "time": time(14, 0),
                "duration": services[1].duration if len(services) > 1 else 30,
                "end_time": time(14, 30),
                "status": "confirmed",
                "created_by": admin.id if admin else None
            },
            {
                "booking_number": f"BK-{today.strftime('%Y%m%d')}-0003",
                "client_id": clients[2].id if len(clients) > 2 else clients[0].id,
                "service_id": services[2].id if len(services) > 2 else services[0].id,
                "master_id": masters[2].id if len(masters) > 2 else (masters[0].id if len(masters) > 0 else None),
                "post_id": posts[2].id if len(posts) > 2 else (posts[0].id if len(posts) > 0 else None),
                "date": today + timedelta(days=2),
                "time": time(11, 30),
                "duration": services[2].duration if len(services) > 2 else 30,
                "end_time": time(12, 0),
                "status": "completed",
                "created_by": admin.id if admin else None
            },
            {
                "booking_number": f"BK-{today.strftime('%Y%m%d')}-0004",
                "client_id": clients[3].id if len(clients) > 3 else clients[0].id,
                "service_id": services[3].id if len(services) > 3 else services[0].id,
                "master_id": masters[3].id if len(masters) > 3 else (masters[0].id if len(masters) > 0 else None),
                "post_id": posts[3].id if len(posts) > 3 else (posts[0].id if len(posts) > 0 else None),
                "date": today - timedelta(days=1),
                "time": time(15, 0),
                "duration": services[3].duration if len(services) > 3 else 30,
                "end_time": time(15, 30),
                "status": "new",
                "created_by": admin.id if admin else None
            },
            {
                "booking_number": f"BK-{today.strftime('%Y%m%d')}-0005",
                "client_id": clients[4].id if len(clients) > 4 else clients[0].id,
                "service_id": services[4].id if len(services) > 4 else services[0].id,
                "master_id": masters[4].id if len(masters) > 4 else (masters[0].id if len(masters) > 0 else None),
                "post_id": posts[4].id if len(posts) > 4 else (posts[0].id if len(posts) > 0 else None),
                "date": today + timedelta(days=3),
                "time": time(16, 0),
                "duration": services[4].duration if len(services) > 4 else 30,
                "end_time": time(16, 30),
                "status": "confirmed",
                "created_by": admin.id if admin else None
            },
        ]
        
        created_count = 0
        for booking_data in test_bookings:
            # Проверяем, существует ли запись с таким номером
            existing = await session.execute(
                select(Booking).where(Booking.booking_number == booking_data["booking_number"])
            )
            if existing.scalar_one_or_none():
                print(f"⏭️  Запись {booking_data['booking_number']} уже существует")
                continue
            
            # Вычисляем end_time на основе времени и длительности
            start_datetime = datetime.combine(booking_data["date"], booking_data["time"])
            end_datetime = start_datetime + timedelta(minutes=booking_data["duration"])
            booking_data["end_time"] = end_datetime.time()
            
            booking = Booking(**booking_data)
            session.add(booking)
            created_count += 1
            print(f"✅ Создана запись: {booking_data['booking_number']} ({booking_data['date']} {booking_data['time']}, статус: {booking_data['status']})")
        
        await session.commit()
        print(f"\n✅ Всего создано новых записей: {created_count}")


async def main():
    """Главная функция"""
    try:
        await create_test_bookings()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())









