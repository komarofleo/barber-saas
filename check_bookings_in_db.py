"""
Скрипт для проверки записей в БД.

Проверяет:
1. Какие компании существуют
2. Какие записи есть в tenant схемах
3. На какие даты есть записи
"""
import asyncio
import sys
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Настройки БД
DATABASE_URL = "postgresql+asyncpg://barber_user:barber_password@localhost:5432/barber_db"


async def check_public_schema():
    """Проверить данные в public схеме"""
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("\n" + "="*80)
        print("📋 ПРОВЕРКА PUBLIC СХЕМЫ")
        print("="*80)
        
        # Проверяем компании
        companies_query = text("""
            SELECT id, name, is_active, created_at
            FROM companies
            ORDER BY id
        """)
        result = await session.execute(companies_query)
        companies = result.fetchall()
        
        print(f"\n🏢 Компании ({len(companies)}):")
        for company in companies:
            print(f"  ID: {company[0]}, Название: {company[1]}, Активна: {company[2]}")
        
        # Проверяем подписки
        subscriptions_query = text("""
            SELECT c.id as company_id, c.name as company_name,
                   s.plan_id, s.start_date, s.end_date, s.status
            FROM companies c
            LEFT JOIN subscriptions s ON c.id = s.company_id
            ORDER BY c.id
        """)
        result = await session.execute(subscriptions_query)
        subscriptions = result.fetchall()
        
        print(f"\n💳 Подписки ({len(subscriptions)}):")
        for sub in subscriptions:
            print(f"  Компания: {sub[1]} (ID: {sub[0]}), "
                  f"Тариф: {sub[2]}, "
                  f"Статус: {sub[5]}, "
                  f"Период: {sub[3]} - {sub[4]}")
    
    await engine.dispose()


async def check_tenant_schema(company_id: int, company_name: str):
    """Проверить данные в tenant схеме конкретной компании"""
    # Формируем URL для tenant схемы
    tenant_url = f"{DATABASE_URL}?options=-csearch_path%3Dtenant_{company_id}"
    engine = create_async_engine(tenant_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("\n" + "="*80)
    print(f"📊 ПРОВЕРКА TENANT СХЕМЫ ДЛЯ КОМПАНИИ: {company_name} (ID: {company_id})")
    print("="*80)
    
    try:
        async with async_session() as session:
            # Проверяем записи
            bookings_query = text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT date) as dates_count,
                    COUNT(DISTINCT master_id) as masters_count
                FROM bookings
            """)
            result = await session.execute(bookings_query)
            stats = result.fetchone()
            
            print(f"\n📋 Статистика записей:")
            print(f"  Всего записей: {stats[0]}")
            print(f"  Количество дат: {stats[1]}")
            print(f"  Количество мастеров: {stats[2]}")
            
            # Проверяем записи на ближайшие 7 дней
            today = datetime.now().date()
            dates_check = []
            for i in range(7):
                check_date = today + timedelta(days=i)
                date_query = text("""
                    SELECT COUNT(*) as count, 
                           COUNT(DISTINCT master_id) as masters
                    FROM bookings
                    WHERE date = :check_date
                """)
                result = await session.execute(date_query, {"check_date": check_date})
                row = result.fetchone()
                dates_check.append((check_date, row[0], row[1]))
            
            print(f"\n📅 Записи на ближайшие 7 дней:")
            has_bookings = False
            for date, count, masters in dates_check:
                if count > 0:
                    has_bookings = True
                    print(f"  {date}: {count} записей, {masters} мастеров")
                else:
                    print(f"  {date}: нет записей")
            
            if not has_bookings:
                print("\n⚠️  ВНИМАНИЕ: На ближайшие 7 дней записей нет!")
            
            # Если записи есть, покажем детали на сегодня
            if stats[0] > 0:
                print(f"\n📝 Записи на {today}:")
                bookings_today_query = text("""
                    SELECT b.id, b.date, b.time, b.status,
                           c.full_name as client_name,
                           s.name as service_name,
                           m.full_name as master_name
                    FROM bookings b
                    LEFT JOIN clients c ON b.client_id = c.id
                    LEFT JOIN services s ON b.service_id = s.id
                    LEFT JOIN masters m ON b.master_id = m.id
                    WHERE b.date = :check_date
                    ORDER BY b.time ASC
                """)
                result = await session.execute(bookings_today_query, {"check_date": today})
                bookings = result.fetchall()
                
                if bookings:
                    print(f"  Найдено {len(bookings)} записей:")
                    for booking in bookings:
                        print(f"    {booking[2]} - {booking[3]} | "
                              f"Клиент: {booking[4]}, "
                              f"Мастер: {booking[6]}, "
                              f"Услуга: {booking[5]}")
                else:
                    print("  Записей на сегодня нет")
    
    except Exception as e:
        print(f"\n❌ Ошибка при проверке tenant схемы: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


async def main():
    """Главная функция"""
    # Проверяем public схему
    await check_public_schema()
    
    # Получаем список компаний и проверяем их tenant схемы
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            companies_query = text("""
                SELECT id, name
                FROM companies
                WHERE is_active = true
                ORDER BY id
            """)
            result = await session.execute(companies_query)
            companies = result.fetchall()
            
            # Проверяем каждую активную компанию
            for company_id, company_name in companies:
                await check_tenant_schema(company_id, company_name)
                await asyncio.sleep(0.5)  # Пауза между запросами
    finally:
        await engine.dispose()
    
    print("\n" + "="*80)
    print("✅ Проверка завершена!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
