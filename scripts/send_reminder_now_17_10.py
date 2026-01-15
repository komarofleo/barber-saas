"""Отправить напоминание для записи на 17.10 в 10:00 прямо сейчас"""
import asyncio
import sys
from pathlib import Path
from datetime import date

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.backend.app.tasks.notifications import send_single_reminder_day_before, send_single_reminder_3_hours_before
from web.backend.app.database import get_async_session_maker
from sqlalchemy import text

async_session_maker = get_async_session_maker()


async def send_reminder_for_booking_17_10():
    """Найти запись на 17.10 в 10:00 и отправить напоминание"""
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
        
        # Ищем запись на 17.10 в 10:00
        target_date = date(2024, 10, 17)  # 17.10.2024
        target_time = "10:00"
        
        await session.execute(text(f'SET search_path TO "{schema_name}", public'))
        
        booking_result = await session.execute(
            text('''
                SELECT b.id, b.booking_number, b.date, b.time, b.status,
                       c.user_id, c.full_name,
                       u.telegram_id
                FROM bookings b
                LEFT JOIN clients c ON b.client_id = c.id
                LEFT JOIN users u ON c.user_id = u.id
                WHERE b.date = :target_date
                  AND b.time::text = :target_time
                  AND b.status = 'confirmed'
                ORDER BY b.id DESC
                LIMIT 1
            '''),
            {
                "target_date": target_date,
                "target_time": target_time
            }
        )
        booking_row = booking_result.fetchone()
        
        if not booking_row:
            print(f"❌ Запись на {target_date} в {target_time} не найдена или не подтверждена")
            print("   Проверьте, что запись существует и имеет статус 'confirmed'")
            return
        
        booking_id = booking_row[0]
        booking_number = booking_row[1]
        booking_date = booking_row[2]
        booking_time = booking_row[3]
        booking_status = booking_row[4]
        user_id = booking_row[5]
        client_name = booking_row[6]
        telegram_id = booking_row[7]
        
        print(f"✅ Найдена запись:")
        print(f"   ID: {booking_id}")
        print(f"   Номер: {booking_number}")
        print(f"   Клиент: {client_name}")
        print(f"   Дата: {booking_date}")
        print(f"   Время: {booking_time}")
        print(f"   Статус: {booking_status}")
        print(f"   Telegram ID: {telegram_id}")
        
        if not telegram_id:
            print("❌ У клиента нет telegram_id. Нельзя отправить напоминание.")
            return
        
        # Отправляем напоминание за день (можно также отправить за 3 часа)
        print(f"\n📤 Отправляем напоминание за день...")
        try:
            await send_single_reminder_day_before(company_id, booking_id)
            print(f"✅ Напоминание за день отправлено!")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания за день: {e}")
            import traceback
            traceback.print_exc()
        
        # Также можно отправить напоминание за 3 часа
        print(f"\n📤 Отправляем напоминание за 3 часа...")
        try:
            await send_single_reminder_3_hours_before(company_id, booking_id)
            print(f"✅ Напоминание за 3 часа отправлено!")
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания за 3 часа: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """Главная функция"""
    try:
        await send_reminder_for_booking_17_10()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🔔 Отправка напоминания для записи на 17.10 в 10:00")
    print("=" * 60)
    asyncio.run(main())
