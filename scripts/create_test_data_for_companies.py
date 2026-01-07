"""
Скрипт для создания тестовых данных в tenant схемах для компаний
"""
import asyncio
import sys
import random
from pathlib import Path
from datetime import datetime, date, time, timedelta
from decimal import Decimal

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import get_db
from app.services.tenant_service import get_tenant_service


async def create_tables_in_tenant_schema(session, schema_name: str):
    """Создать таблицы в tenant схеме, если их нет"""
    tables = {
        'users': '''
            CREATE TABLE IF NOT EXISTS "{schema}".users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                phone VARCHAR(20),
                is_admin BOOLEAN DEFAULT false,
                is_master BOOLEAN DEFAULT false,
                is_blocked BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''',
        'masters': '''
            CREATE TABLE IF NOT EXISTS "{schema}".masters (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES "{schema}".users(id) ON DELETE CASCADE,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                telegram_id BIGINT,
                specialization VARCHAR(100),
                is_universal BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''',
        'clients': '''
            CREATE TABLE IF NOT EXISTS "{schema}".clients (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES "{schema}".users(id) ON DELETE CASCADE NOT NULL UNIQUE,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                car_brand VARCHAR(100),
                car_model VARCHAR(100),
                car_number VARCHAR(20),
                total_visits INTEGER DEFAULT 0,
                total_amount NUMERIC(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''',
        'services': '''
            CREATE TABLE IF NOT EXISTS "{schema}".services (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price NUMERIC(10,2) NOT NULL,
                duration INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''',
        'posts': '''
            CREATE TABLE IF NOT EXISTS "{schema}".posts (
                id SERIAL PRIMARY KEY,
                number INTEGER UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''',
        'bookings': '''
            CREATE TABLE IF NOT EXISTS "{schema}".bookings (
                id SERIAL PRIMARY KEY,
                booking_number VARCHAR(50) UNIQUE,
                client_id INTEGER REFERENCES "{schema}".clients(id) ON DELETE CASCADE,
                service_id INTEGER REFERENCES "{schema}".services(id) ON DELETE SET NULL,
                master_id INTEGER REFERENCES "{schema}".masters(id) ON DELETE SET NULL,
                post_id INTEGER REFERENCES "{schema}".posts(id) ON DELETE SET NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status VARCHAR(20) DEFAULT 'new',
                comment TEXT,
                created_by INTEGER REFERENCES "{schema}".users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        '''
    }
    
    for table_name, create_sql in tables.items():
        sql = create_sql.format(schema=schema_name)
        try:
            await session.execute(text(sql))
            await session.commit()
        except Exception as e:
            print(f"  ⚠️  Таблица {table_name} уже существует или ошибка: {e}")


async def create_test_data_for_company(company_id: int, company_name: str):
    """Создать тестовые данные для компании"""
    print(f"\n{'='*60}")
    print(f"📦 Создание тестовых данных для компании {company_id}: {company_name}")
    print(f"{'='*60}")
    
    schema_name = f"tenant_{company_id}"
    tenant_service = get_tenant_service()
    
    async for session in tenant_service.get_tenant_session(company_id):
        # Устанавливаем search_path
        await session.execute(text(f'SET search_path TO "{schema_name}", public'))
        
        # Создаем таблицы, если их нет
        print(f"\n📋 Создание таблиц в схеме {schema_name}...")
        await create_tables_in_tenant_schema(session, schema_name)
        
        # Получаем admin_telegram_id компании
        async for db in get_db():
            result = await db.execute(
                text('SELECT admin_telegram_id FROM public.companies WHERE id = :company_id'),
                {'company_id': company_id}
            )
            admin_telegram_id = result.scalar_one_or_none()
            break
        
        # 1. Создаем пользователей
        print(f"\n👥 Создание пользователей...")
        user_ids = []
        if admin_telegram_id:
            # Проверяем, есть ли уже пользователь с admin_telegram_id
            result = await session.execute(
                text('SELECT id FROM users WHERE telegram_id = :tg_id'),
                {'tg_id': admin_telegram_id}
            )
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                await session.execute(
                    text('''
                        INSERT INTO users (telegram_id, username, first_name, is_admin, is_master)
                        VALUES (:tg_id, :username, :name, true, false)
                        ON CONFLICT (telegram_id) DO NOTHING
                        RETURNING id
                    '''),
                    {'tg_id': admin_telegram_id, 'username': f'admin_{company_id}', 'name': company_name}
                )
                result = await session.execute(
                    text('SELECT id FROM users WHERE telegram_id = :tg_id'),
                    {'tg_id': admin_telegram_id}
                )
                admin_user = result.scalar_one_or_none()
            if admin_user:
                user_ids.append(admin_user[0])
        
        # Создаем дополнительных пользователей
        test_users = [
            (1000000 + company_id * 100 + 1, 'Иван', 'Петров', '+79991111111', False, False),
            (1000000 + company_id * 100 + 2, 'Мария', 'Сидорова', '+79992222222', False, True),
            (1000000 + company_id * 100 + 3, 'Алексей', 'Смирнов', '+79993333333', False, True),
            (1000000 + company_id * 100 + 4, 'Елена', 'Козлова', '+79994444444', False, False),
            (1000000 + company_id * 100 + 5, 'Дмитрий', 'Волков', '+79995555555', False, True),
        ]
        
        for tg_id, first_name, last_name, phone, is_admin, is_master in test_users:
            await session.execute(
                text('''
                    INSERT INTO users (telegram_id, username, first_name, last_name, phone, is_admin, is_master)
                    VALUES (:tg_id, :username, :first_name, :last_name, :phone, :is_admin, :is_master)
                    ON CONFLICT (telegram_id) DO NOTHING
                    RETURNING id
                '''),
                {
                    'tg_id': tg_id,
                    'username': f'{first_name.lower()}_{last_name.lower()}',
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': phone,
                    'is_admin': is_admin,
                    'is_master': is_master
                }
            )
            result = await session.execute(
                text('SELECT id FROM users WHERE telegram_id = :tg_id'),
                {'tg_id': tg_id}
            )
            user = result.scalar_one_or_none()
            if user:
                user_ids.append(user[0])
        
        await session.commit()
        print(f"  ✅ Создано пользователей: {len(user_ids)}")
        
        # 2. Создаем мастеров
        print(f"\n👨‍🔧 Создание мастеров...")
        master_ids = []
        specializations = ['Ремонт двигателя', 'Кузовной ремонт', 'Диагностика', 'Шиномонтаж', 'Замена масла']
        
        master_users = [uid for i, uid in enumerate(user_ids) if i > 0 and i <= 3]  # Берем пользователей 2-4 как мастеров
        
        for i, user_id in enumerate(master_users[:3]):
            await session.execute(
                text('''
                    INSERT INTO masters (user_id, full_name, phone, specialization, is_universal)
                    SELECT :user_id, first_name || ' ' || COALESCE(last_name, ''), phone, :spec, true
                    FROM users WHERE id = :user_id
                    ON CONFLICT (user_id) DO NOTHING
                    RETURNING id
                '''),
                {'user_id': user_id, 'spec': specializations[i % len(specializations)]}
            )
            result = await session.execute(
                text('SELECT id FROM masters WHERE user_id = :user_id'),
                {'user_id': user_id}
            )
            master = result.scalar_one_or_none()
            if master:
                master_ids.append(master[0])
        
        await session.commit()
        print(f"  ✅ Создано мастеров: {len(master_ids)}")
        
        # 3. Создаем клиентов
        print(f"\n👤 Создание клиентов...")
        client_ids = []
        client_users = [uid for uid in user_ids if uid not in master_users]
        
        car_brands = ['Toyota', 'Honda', 'BMW', 'Mercedes', 'Audi']
        car_models = ['Camry', 'Accord', 'X5', 'C-Class', 'A4']
        
        for i, user_id in enumerate(client_users[:5]):
            await session.execute(
                text('''
                    INSERT INTO clients (user_id, full_name, phone, car_brand, car_model, car_number)
                    SELECT :user_id, first_name || ' ' || COALESCE(last_name, ''), phone, :brand, :model, :number
                    FROM users WHERE id = :user_id
                    ON CONFLICT (user_id) DO NOTHING
                    RETURNING id
                '''),
                {
                    'user_id': user_id,
                    'brand': car_brands[i % len(car_brands)],
                    'model': car_models[i % len(car_models)],
                    'number': f'А{100 + i}БВ{777 + company_id}'
                }
            )
            result = await session.execute(
                text('SELECT id FROM clients WHERE user_id = :user_id'),
                {'user_id': user_id}
            )
            client = result.scalar_one_or_none()
            if client:
                client_ids.append(client[0])
        
        await session.commit()
        print(f"  ✅ Создано клиентов: {len(client_ids)}")
        
        # 4. Создаем услуги
        print(f"\n🔧 Создание услуг...")
        service_ids = []
        services_data = [
            ('Диагностика', 'Полная диагностика автомобиля', 2000, 60),
            ('Замена масла', 'Замена моторного масла и фильтра', 1500, 30),
            ('Шиномонтаж', 'Монтаж/демонтаж шин', 1000, 45),
            ('Ремонт двигателя', 'Ремонт двигателя', 10000, 240),
            ('Кузовной ремонт', 'Восстановление кузова', 15000, 480),
        ]
        
        for name, desc, price, duration in services_data:
            await session.execute(
                text('''
                    INSERT INTO services (name, description, price, duration, is_active)
                    VALUES (:name, :desc, :price, :duration, true)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                '''),
                {'name': name, 'desc': desc, 'price': price, 'duration': duration}
            )
            result = await session.execute(
                text('SELECT id FROM services WHERE name = :name'),
                {'name': name}
            )
            service = result.scalar_one_or_none()
            if service:
                service_ids.append(service[0])
        
        await session.commit()
        print(f"  ✅ Создано услуг: {len(service_ids)}")
        
        # 5. Создаем посты
        print(f"\n🛠️  Создание постов...")
        post_ids = []
        posts_data = [
            (1, 'Пост 1', 'Основной пост для диагностики'),
            (2, 'Пост 2', 'Пост для шиномонтажа'),
            (3, 'Пост 3', 'Пост для кузовного ремонта'),
            (4, 'Пост 4', 'Пост для замены масла'),
        ]
        
        for number, name, desc in posts_data:
            await session.execute(
                text('''
                    INSERT INTO posts (number, name, description, is_active)
                    VALUES (:number, :name, :desc, true)
                    ON CONFLICT (number) DO NOTHING
                    RETURNING id
                '''),
                {'number': number, 'name': name, 'desc': desc}
            )
            result = await session.execute(
                text('SELECT id FROM posts WHERE number = :number'),
                {'number': number}
            )
            post = result.scalar_one_or_none()
            if post:
                post_ids.append(post[0])
        
        await session.commit()
        print(f"  ✅ Создано постов: {len(post_ids)}")
        
        # 6. Создаем записи
        print(f"\n📅 Создание записей...")
        booking_count = 0
        today = date.today()
        
        for day_offset in range(-7, 30):  # Записи на прошлую неделю и следующий месяц
            booking_date = today + timedelta(days=day_offset)
            
            # Создаем 2-3 записи в день
            for _ in range(random.randint(2, 3)):
                if not client_ids or not service_ids:
                    continue
                
                client_id = random.choice(client_ids)
                service_id = random.choice(service_ids)
                master_id = random.choice(master_ids) if master_ids else None
                post_id = random.choice(post_ids) if post_ids else None
                
                # Получаем длительность услуги
                result = await session.execute(
                    text('SELECT duration FROM services WHERE id = :service_id'),
                    {'service_id': service_id}
                )
                duration = result.scalar_one_or_none()
                duration_minutes = duration[0] if duration else 60
                
                # Генерируем время (9:00 - 18:00)
                hour = random.randint(9, 17)
                minute = random.choice([0, 30])
                booking_time = time(hour, minute)
                
                booking_number = f"BK{company_id}{booking_date.strftime('%Y%m%d')}{booking_count:03d}"
                status = random.choice(['new', 'confirmed', 'completed', 'cancelled'])
                
                await session.execute(
                    text('''
                        INSERT INTO bookings (booking_number, client_id, service_id, master_id, post_id, 
                                             date, time, status, created_by)
                        VALUES (:number, :client_id, :service_id, :master_id, :post_id, 
                                :date, :time, :status, :created_by)
                        ON CONFLICT (booking_number) DO NOTHING
                    '''),
                    {
                        'number': booking_number,
                        'client_id': client_id,
                        'service_id': service_id,
                        'master_id': master_id,
                        'post_id': post_id,
                        'date': booking_date,
                        'time': booking_time,
                        'status': status,
                        'created_by': user_ids[0] if user_ids else None
                    }
                )
                booking_count += 1
        
        await session.commit()
        print(f"  ✅ Создано записей: {booking_count}")
        
        print(f"\n✅ Тестовые данные для компании {company_id} ({company_name}) успешно созданы!")
        break


async def main():
    """Главная функция"""
    companies = [
        (2, 'Тестовая компания проверка'),
        (3, 'Шинка'),
    ]
    
    for company_id, company_name in companies:
        try:
            await create_test_data_for_company(company_id, company_name)
        except Exception as e:
            print(f"\n❌ Ошибка при создании данных для компании {company_id}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("✅ Готово! Все тестовые данные созданы.")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    asyncio.run(main())

