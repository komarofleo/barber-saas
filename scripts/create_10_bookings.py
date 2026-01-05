"""Скрипт создания 10 новых заказов на разные услуги"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, func
from decimal import Decimal

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import Booking, Client, Service, Master, Post, User
import os

# Получаем параметры БД из переменных окружения
DB_HOST = os.getenv("DB_HOST", "autoservice_postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "autoservice_db")
DB_USER = os.getenv("DB_USER", "autoservice_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Формируем DATABASE_URL
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_client_for_user(session: AsyncSession, user: User, index: int):
    """Создать клиента для пользователя"""
    existing_client = await session.execute(
        select(Client).where(Client.user_id == user.id)
    )
    client = existing_client.scalar_one_or_none()
    
    if not client:
        car_brands = ["Toyota", "Honda", "BMW", "Mercedes", "Audi", "Volkswagen", "Ford", "Nissan", "Hyundai", "Kia"]
        car_models = ["Camry", "Accord", "X5", "C-Class", "A4", "Golf", "Focus", "Altima", "Elantra", "Optima"]
        
        client = Client(
            user_id=user.id,
            full_name=f"{user.first_name or ''} {user.last_name or ''}".strip() or f"Клиент {user.telegram_id}",
            phone=user.phone or f"+7999{1000000 + user.telegram_id}",
            car_brand=car_brands[index % len(car_brands)],
            car_model=car_models[index % len(car_models)],
            car_number=f"А{100 + index}БВ{777 + index}"
        )
        session.add(client)
        await session.flush()
        print(f"  ✅ Создан клиент: {client.full_name} ({client.car_brand} {client.car_model})")
    
    return client


async def create_10_bookings():
    """Создать 10 новых заказов на разные услуги"""
    async with async_session_maker() as session:
        # Получаем все активные услуги
        services_result = await session.execute(
            select(Service).where(Service.is_active == True).order_by(Service.id)
        )
        services = services_result.scalars().all()
        
        if not services:
            print("❌ Нет активных услуг в системе! Сначала создайте услуги.")
            return
        
        print(f"📋 Найдено услуг: {len(services)}")
        
        # Получаем мастеров
        masters_result = await session.execute(select(Master).limit(10))
        masters = masters_result.scalars().all()
        
        # Получаем посты
        posts_result = await session.execute(select(Post).where(Post.is_active == True).limit(10))
        posts = posts_result.scalars().all()
        
        # Получаем админа для created_by
        admin_result = await session.execute(select(User).where(User.is_admin == True).limit(1))
        admin = admin_result.scalar_one_or_none()
        if not admin:
            admin_result = await session.execute(select(User).limit(1))
            admin = admin_result.scalar_one_or_none()
        
        # Получаем существующих пользователей
        users_result = await session.execute(select(User).where(User.is_admin == False).limit(20))
        existing_users = users_result.scalars().all()
        
        # Создаем недостающих пользователей и клиентов
        users_to_use = []
        for i in range(10):
            if i < len(existing_users):
                user = existing_users[i]
            else:
                # Создаем нового пользователя
                base_telegram_id = 200000000 + i
                user = User(
                    telegram_id=base_telegram_id,
                    first_name=f"Клиент{i+1}",
                    last_name=f"Тестовый{i+1}",
                    phone=f"+7999{1000000 + i}",
                    is_admin=False,
                    is_master=False
                )
                session.add(user)
                await session.flush()
                print(f"✅ Создан пользователь: {user.first_name} {user.last_name}")
            
            # Создаем клиента для пользователя
            client = await create_client_for_user(session, user, i)
            users_to_use.append((user, client))
        
        await session.commit()
        
        # Генерируем даты - начиная с сегодня и на следующие дни
        today = date.today()
        times = [
            time(9, 0), time(10, 0), time(11, 0), time(12, 0), time(13, 0),
            time(14, 0), time(15, 0), time(16, 0), time(17, 0), time(18, 0)
        ]
        
        # Получаем последний номер записи
        last_booking = await session.execute(
            select(Booking).order_by(Booking.id.desc()).limit(1)
        )
        last = last_booking.scalar_one_or_none()
        if last and last.booking_number:
            try:
                last_num = int(last.booking_number.split('-')[-1])
                start_num = last_num + 1
            except:
                start_num = 1
        else:
            start_num = 1
        
        created_count = 0
        for i in range(10):
            user, client = users_to_use[i]
            service = services[i % len(services)]  # Циклически используем услуги
            
            # Распределяем по дням (сегодня + i дней)
            booking_date = today + timedelta(days=i % 7)  # В течение недели
            booking_time = times[i % len(times)]
            
            # Вычисляем время окончания
            start_datetime = datetime.combine(booking_date, booking_time)
            end_datetime = start_datetime + timedelta(minutes=service.duration)
            end_time = end_datetime.time()
            
            # Генерируем номер записи
            booking_number = f"BK-{booking_date.strftime('%Y%m%d')}-{start_num + i:04d}"
            
            # Проверяем, существует ли запись с таким номером
            existing = await session.execute(
                select(Booking).where(Booking.booking_number == booking_number)
            )
            if existing.scalar_one_or_none():
                print(f"⏭️  Запись {booking_number} уже существует, пропускаем")
                continue
            
            # Выбираем мастера и пост (если есть)
            master = masters[i % len(masters)] if masters else None
            post = posts[i % len(posts)] if posts else None
            
            booking = Booking(
                booking_number=booking_number,
                client_id=client.id,
                service_id=service.id,
                master_id=master.id if master else None,
                post_id=post.id if post else None,
                date=booking_date,
                time=booking_time,
                duration=service.duration,
                end_time=end_time,
                status="new" if i % 3 == 0 else ("confirmed" if i % 3 == 1 else "new"),
                amount=service.price,
                created_by=admin.id if admin else None
            )
            
            session.add(booking)
            created_count += 1
            
            master_name = master.full_name if master else "Не назначен"
            post_info = f"Пост {post.number}" if post else "Пост не указан"
            print(f"✅ Создана запись #{i+1}: {booking_number}")
            print(f"   📅 {booking_date.strftime('%d.%m.%Y')} в {booking_time.strftime('%H:%M')}")
            print(f"   🔧 Услуга: {service.name} ({service.duration} мин, {service.price} ₽)")
            print(f"   👤 Клиент: {client.full_name}")
            print(f"   👨‍🔧 Мастер: {master_name}")
            print(f"   📍 {post_info}")
            print()
        
        await session.commit()
        print(f"\n{'='*60}")
        print(f"✅ Успешно создано новых заказов: {created_count} из 10")
        print(f"{'='*60}\n")
        
        # Проверяем записи в календаре
        print("📅 Проверка записей в календаре:")
        bookings_check = await session.execute(
            select(Booking)
            .where(Booking.date >= today)
            .where(Booking.date <= today + timedelta(days=7))
            .order_by(Booking.date, Booking.time)
        )
        calendar_bookings = bookings_check.scalars().all()
        
        print(f"   Найдено записей на ближайшую неделю: {len(calendar_bookings)}")
        for booking in calendar_bookings[:10]:  # Показываем первые 10
            service_name = "Не указана"
            if booking.service:
                service_name = booking.service.name
            print(f"   • {booking.date.strftime('%d.%m.%Y')} {booking.time.strftime('%H:%M')} - {service_name} ({booking.booking_number})")


async def main():
    """Главная функция"""
    try:
        await create_10_bookings()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

