"""Тестовый скрипт для проверки напоминаний - Иван Петров на завтра 10:00"""
import asyncio
import sys
from pathlib import Path
from datetime import date, time, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, text

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database.models import Booking, Client, Service, Master, Post, User
from bot.config import DATABASE_URL
from bot.database.crud import create_booking, update_booking_status, get_booking_by_id

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def test_reminder_ivan_petrov():
    """Создать тестовую запись для Ивана Петрова на завтра в 10:00"""
    async with async_session_maker() as session:
        # Определяем company_id (берем первую активную компанию)
        await session.execute(text('SET search_path TO public'))
        company_result = await session.execute(
            text('SELECT id FROM companies WHERE is_active = true LIMIT 1')
        )
        company_row = company_result.fetchone()
        
        if not company_row:
            print("❌ Не найдена активная компания")
            return
        
        company_id = company_row[0]
        schema_name = f"tenant_{company_id}"
        print(f"✅ Используем компанию ID={company_id}, схема={schema_name}")
        
        # Устанавливаем search_path для tenant схемы
        await session.execute(text(f'SET search_path TO "{schema_name}", public'))
        
        # Ищем клиента "Иван Петров"
        client_result = await session.execute(
            text('SELECT id, user_id, full_name, phone FROM clients WHERE full_name LIKE :name'),
            {"name": "%Иван%Петров%"}
        )
        client_row = client_result.fetchone()
        
        if not client_row:
            print("⚠️ Клиент 'Иван Петров' не найден, создаем...")
            
            # Создаем пользователя
            user_result = await session.execute(
                text('''
                    INSERT INTO users (telegram_id, first_name, last_name, phone, is_admin, is_master, created_at, updated_at)
                    VALUES (:telegram_id, :first_name, :last_name, :phone, false, false, NOW(), NOW())
                    RETURNING id
                '''),
                {
                    "telegram_id": 999999999,  # Тестовый telegram_id
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "phone": "+79991234567"
                }
            )
            user_id = user_result.scalar_one()
            await session.commit()
            print(f"✅ Создан пользователь ID={user_id}")
            
            # Создаем клиента
            client_result = await session.execute(
                text('''
                    INSERT INTO clients (user_id, full_name, phone, created_at, updated_at)
                    VALUES (:user_id, :full_name, :phone, NOW(), NOW())
                    RETURNING id, user_id, full_name, phone
                '''),
                {
                    "user_id": user_id,
                    "full_name": "Иван Петров",
                    "phone": "+79991234567"
                }
            )
            client_row = client_result.fetchone()
            await session.commit()
            print(f"✅ Создан клиент ID={client_row[0]}")
        else:
            print(f"✅ Найден клиент: ID={client_row[0]}, ФИО={client_row[2]}")
        
        client_id = client_row[0]
        user_id = client_row[1]
        
        # Получаем услугу (первую активную)
        service_result = await session.execute(
            text('SELECT id, name, duration, price FROM services WHERE is_active = true LIMIT 1')
        )
        service_row = service_result.fetchone()
        
        if not service_row:
            print("❌ Не найдена активная услуга")
            return
        
        service_id = service_row[0]
        service_duration = service_row[2]
        print(f"✅ Используем услугу: {service_row[1]}, длительность={service_duration} мин")
        
        # Дата завтра в 10:00
        tomorrow = date.today() + timedelta(days=1)
        booking_time = time(10, 0)
        end_time = time(10, 0 + service_duration // 60, service_duration % 60)
        
        # Проверяем, есть ли уже запись на это время
        existing_result = await session.execute(
            text('''
                SELECT id, booking_number, status FROM bookings 
                WHERE client_id = :client_id 
                  AND date = :date 
                  AND time = :time
            '''),
            {
                "client_id": client_id,
                "date": tomorrow,
                "time": booking_time
            }
        )
        existing_booking = existing_result.fetchone()
        
        if existing_booking:
            booking_id = existing_booking[0]
            booking_status = existing_booking[2]
            print(f"✅ Найдена существующая запись ID={booking_id}, статус={booking_status}")
            
            # Если запись не подтверждена - подтверждаем
            if booking_status != "confirmed":
                print(f"🔄 Подтверждаем запись...")
                booking = await update_booking_status(
                    session=session,
                    booking_id=booking_id,
                    status="confirmed",
                    company_id=company_id
                )
                print(f"✅ Запись подтверждена! Напоминания должны быть запланированы.")
            else:
                print(f"✅ Запись уже подтверждена. Напоминания должны быть уже запланированы.")
        else:
            # Создаем новую запись
            print(f"📅 Создаем новую запись на {tomorrow} в {booking_time}...")
            
            booking = await create_booking(
                session=session,
                client_id=client_id,
                service_id=service_id,
                booking_date=tomorrow,
                booking_time=booking_time,
                duration=service_duration,
                end_time=end_time,
                comment="Тестовая запись для проверки напоминаний",
                created_by=user_id,
                company_id=company_id
            )
            
            print(f"✅ Запись создана: ID={booking.id}, номер={booking.booking_number}")
            
            # Подтверждаем запись (это вызовет планирование напоминаний)
            print(f"🔄 Подтверждаем запись...")
            booking = await update_booking_status(
                session=session,
                booking_id=booking.id,
                status="confirmed",
                company_id=company_id
            )
            
            print(f"✅ Запись подтверждена! Напоминания должны быть запланированы.")
            print(f"\n📋 Информация о записи:")
            print(f"   ID: {booking.id}")
            print(f"   Номер: {booking.booking_number}")
            print(f"   Клиент: Иван Петров")
            print(f"   Дата: {tomorrow}")
            print(f"   Время: {booking_time}")
            print(f"   Статус: confirmed")
            print(f"\n⏰ Ожидаемые напоминания:")
            print(f"   1. За день: {tomorrow - timedelta(days=1)} в 18:00")
            print(f"   2. За 3 часа: {tomorrow} в 07:00 (за 3 часа до 10:00)")


async def main():
    """Главная функция"""
    try:
        await test_reminder_ivan_petrov()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
