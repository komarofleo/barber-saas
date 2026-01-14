"""
Скрипт для создания тестовой компании и тестовых данных.

Создает:
- Компанию (салон красоты) с логином test/test
- Tenant схему для компании
- Тестовых мастеров
- Рабочие места
- Услуги
- Записи на этот месяц
"""

import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext
from app.config import settings
from app.services.tenant_service import get_tenant_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_test_company():
    """Создать тестовую компанию и все необходимые данные."""
    
    print("🚀 Создание тестовой компании...")
    
    # Подключение к БД для public схемы
    database_url = (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session_maker() as session:
            # Проверяем, существует ли уже тестовая компания
            result = await session.execute(
                text("SELECT id, name FROM companies WHERE name = 'Тестовый салон красоты'")
            )
            existing_company = result.fetchone()
            
            if existing_company:
                company_id = existing_company[0]
                print(f"⚠️  Тестовая компания уже существует (ID: {company_id})")
                print("   Удаляем старую компанию...")
                
                # Удаляем tenant схему
                tenant_service = get_tenant_service()
                await tenant_service.drop_tenant_schema(company_id)
                
                # Удаляем компанию
                await session.execute(
                    text("DELETE FROM companies WHERE id = :id"),
                    {"id": company_id}
                )
                await session.commit()
                print("   ✅ Старая компания удалена")
            
            # Создаем новую компанию
            print("📝 Создание компании...")
            
            # Получаем ID тарифного плана (Starter)
            plan_result = await session.execute(
                text("SELECT id FROM plans WHERE name = 'Starter' LIMIT 1")
            )
            plan_id = plan_result.scalar_one_or_none()
            
            if not plan_id:
                print("❌ Тарифный план Starter не найден!")
                return
            
            # Создаем компанию
            company_result = await session.execute(
                text("""
                    INSERT INTO companies (
                        name, email, phone, telegram_bot_token,
                        admin_telegram_id, plan_id, subscription_status,
                        can_create_bookings, is_active, created_at
                    ) VALUES (
                        :name, :email, :phone, :telegram_bot_token,
                        :admin_telegram_id, :plan_id, :subscription_status,
                        :can_create_bookings, :is_active, :created_at
                    ) RETURNING id
                """),
                {
                    "name": "Тестовый салон красоты",
                    "email": "test@barber-saas.com",
                    "phone": "+79991234567",
                    "telegram_bot_token": "1234567890:TEST_TOKEN_FOR_TESTING",
                    "admin_telegram_id": 123456789,
                    "plan_id": plan_id,
                    "subscription_status": "active",
                    "can_create_bookings": True,
                    "is_active": True,
                    "created_at": datetime.now()
                }
            )
            company_id = company_result.scalar_one()
            await session.commit()
            
            print(f"✅ Компания создана (ID: {company_id})")
            
            # Создаем подписку
            print("📋 Создание подписки...")
            await session.execute(
                text("""
                    INSERT INTO subscriptions (
                        company_id, plan_id, start_date, end_date, status, created_at
                    ) VALUES (
                        :company_id, :plan_id, :start_date, :end_date, :status, :created_at
                    )
                """),
                {
                    "company_id": company_id,
                    "plan_id": plan_id,
                    "start_date": date.today(),
                    "end_date": date.today() + timedelta(days=30),
                    "status": "active",
                    "created_at": datetime.now()
                }
            )
            await session.commit()
            print("✅ Подписка создана")
            
            # Пользователь будет создан в tenant схеме
            print("✅ Компания готова для создания пользователя в tenant схеме")
        
        # Создаем tenant схему и клонируем таблицы
        print("🏗️  Создание tenant схемы...")
        tenant_service = get_tenant_service()
        
        if not await tenant_service.create_tenant_schema(company_id):
            print("❌ Ошибка создания tenant схемы!")
            return
        
        if not await tenant_service.initialize_tenant_for_company(company_id):
            print("❌ Ошибка инициализации tenant схемы!")
            return
        
        print("✅ Tenant схема создана и инициализирована")
        
        # Создаем таблицы в tenant схеме
        print("📋 Создание таблиц в tenant схеме...")
        await create_tenant_tables(company_id)
        
        # Создаем тестовые данные в tenant схеме
        print("📊 Создание тестовых данных...")
        await create_tenant_test_data(company_id)
        
        print("\n✅ ✅ ✅ Тестовая компания успешно создана! ✅ ✅ ✅")
        print(f"\n📝 Данные для входа:")
        print(f"   Company ID: {company_id}")
        print(f"   Username: test")
        print(f"   Password: test")
        print(f"\n📍 URL: http://localhost:3000/company/{company_id:03d}/login")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()


async def create_tenant_tables(company_id: int):
    """Создать таблицы в tenant схеме."""
    
    schema_name = f"tenant_{company_id}"
    tenant_service = get_tenant_service()
    
    async for session in tenant_service.get_tenant_session(company_id):
        try:
            # Устанавливаем схему явно
            await session.execute(text(f'SET search_path TO "{schema_name}", public'))
            
            # Создаем таблицы напрямую через SQL с указанием схемы
            tables_sql = f"""
            -- Таблица users
            CREATE TABLE IF NOT EXISTS "{schema_name}".users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                phone VARCHAR(20),
                role VARCHAR(50) DEFAULT 'client',
                telegram_id BIGINT,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Таблица clients
            CREATE TABLE IF NOT EXISTS "{schema_name}".clients (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES "{schema_name}".users(id) ON DELETE CASCADE,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255),
                telegram_id BIGINT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Таблица masters
            CREATE TABLE IF NOT EXISTS "{schema_name}".masters (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES "{schema_name}".users(id) ON DELETE CASCADE UNIQUE,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                telegram_id BIGINT,
                specialization VARCHAR(100),
                is_universal BOOLEAN DEFAULT true NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Таблица services
            CREATE TABLE IF NOT EXISTS "{schema_name}".services (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                duration INTEGER NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                is_active BOOLEAN DEFAULT true NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Таблица posts
            CREATE TABLE IF NOT EXISTS "{schema_name}".posts (
                id SERIAL PRIMARY KEY,
                number INTEGER NOT NULL UNIQUE,
                name VARCHAR(255),
                description TEXT,
                is_active BOOLEAN DEFAULT true NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Таблица bookings
            CREATE TABLE IF NOT EXISTS "{schema_name}".bookings (
                id SERIAL PRIMARY KEY,
                booking_number VARCHAR(50) UNIQUE NOT NULL,
                client_id INTEGER REFERENCES "{schema_name}".clients(id) ON DELETE CASCADE NOT NULL,
                service_id INTEGER REFERENCES "{schema_name}".services(id) ON DELETE SET NULL,
                master_id INTEGER REFERENCES "{schema_name}".masters(id) ON DELETE SET NULL,
                post_id INTEGER REFERENCES "{schema_name}".posts(id) ON DELETE SET NULL,
                created_by INTEGER REFERENCES "{schema_name}".users(id) ON DELETE SET NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                duration INTEGER NOT NULL,
                end_time TIME NOT NULL,
                status VARCHAR(50) DEFAULT 'new' NOT NULL,
                amount NUMERIC(10, 2),
                is_paid BOOLEAN DEFAULT false NOT NULL,
                payment_method VARCHAR(50),
                promocode_id INTEGER,
                discount_amount NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
                comment TEXT,
                admin_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                completed_at TIMESTAMP,
                cancelled_at TIMESTAMP
            );
            
            -- Индексы
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_users_username ON "{schema_name}".users(username);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_users_email ON "{schema_name}".users(email);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_clients_user_id ON "{schema_name}".clients(user_id);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_masters_user_id ON "{schema_name}".masters(user_id);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_services_is_active ON "{schema_name}".services(is_active);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_bookings_date ON "{schema_name}".bookings(date);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_bookings_status ON "{schema_name}".bookings(status);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_bookings_client_id ON "{schema_name}".bookings(client_id);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_bookings_master_id ON "{schema_name}".bookings(master_id);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_bookings_post_id ON "{schema_name}".bookings(post_id);
            CREATE INDEX IF NOT EXISTS "{schema_name}".idx_bookings_date_time ON "{schema_name}".bookings(date, time);
            """
            
            # Выполняем SQL по частям
            statements = [s.strip() for s in tables_sql.split(';') if s.strip() and not s.strip().startswith('--')]
            
            for statement in statements:
                if statement:
                    try:
                        await session.execute(text(statement))
                    except Exception as e:
                        # Игнорируем ошибки "already exists"
                        if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                            print(f"  ⚠️  Предупреждение: {str(e)[:100]}")
            
            await session.commit()
            
            print(f"  ✅ Таблицы созданы в схеме {schema_name}")
            
        except Exception as e:
            print(f"  ❌ Ошибка при создании таблиц: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


async def create_tenant_test_data(company_id: int):
    """Создать тестовые данные в tenant схеме."""
    
    schema_name = f"tenant_{company_id}"
    tenant_service = get_tenant_service()
    
    async for session in tenant_service.get_tenant_session(company_id):
        # Устанавливаем search_path для этой сессии
        await session.execute(text(f'SET search_path TO "{schema_name}", public'))
        try:
            # 1. Создаем услуги
            print("  📋 Создание услуг...")
            services_data = [
                {
                    "name": "Стрижка мужская",
                    "description": "Классическая мужская стрижка",
                    "price": Decimal("800.00"),
                    "duration": 30,
                    "is_active": True
                },
                {
                    "name": "Стрижка женская",
                    "description": "Женская стрижка любой сложности",
                    "price": Decimal("1500.00"),
                    "duration": 60,
                    "is_active": True
                },
                {
                    "name": "Окрашивание",
                    "description": "Окрашивание волос",
                    "price": Decimal("2500.00"),
                    "duration": 120,
                    "is_active": True
                },
                {
                    "name": "Укладка",
                    "description": "Укладка волос",
                    "price": Decimal("1000.00"),
                    "duration": 45,
                    "is_active": True
                },
                {
                    "name": "Мелирование",
                    "description": "Мелирование волос",
                    "price": Decimal("3000.00"),
                    "duration": 150,
                    "is_active": True
                }
            ]
            
            service_ids = []
            for service_data in services_data:
                result = await session.execute(
                    text(f"""
                        INSERT INTO "{schema_name}".services (
                            name, description, price, duration, is_active, created_at, updated_at
                        ) VALUES (
                            :name, :description, :price, :duration, :is_active, :created_at, :updated_at
                        ) RETURNING id
                    """),
                    {**service_data, "created_at": datetime.now(), "updated_at": datetime.now()}
                )
                service_id = result.scalar_one()
                service_ids.append(service_id)
            
            await session.commit()
            print(f"  ✅ Создано {len(service_ids)} услуг")
            
            # 2. Создаем пользователя для входа (admin)
            print("  👤 Создание пользователя для входа...")
            password_hash = pwd_context.hash("test")
            
            user_result = await session.execute(
                    text(f"""
                        INSERT INTO "{schema_name}".users (
                            username, email, password_hash,
                            full_name, phone, role, is_active, created_at
                        ) VALUES (
                            :username, :email, :password_hash,
                            :full_name, :phone, :role, :is_active, :created_at
                        ) RETURNING id
                    """),
                {
                    "username": "test",
                    "email": "test@barber-saas.com",
                    "password_hash": password_hash,
                    "full_name": "Тестовый администратор",
                    "phone": "+79991234567",
                    "role": "admin",
                    "is_active": True,
                    "created_at": datetime.now()
                }
            )
            user_id = user_result.scalar_one()
            await session.commit()
            print(f"  ✅ Пользователь создан (ID: {user_id}, username: test, password: test)")
            
            # 3. Создаем мастеров
            print("  👨‍💼 Создание мастеров...")
            masters_data = [
                {
                    "full_name": "Иван Петров",
                    "phone": "+79991111111",
                    "specialization": "Барбер",
                    "is_universal": False
                },
                {
                    "full_name": "Мария Сидорова",
                    "phone": "+79992222222",
                    "specialization": "Парикмахер, Колорист",
                    "is_universal": False
                },
                {
                    "full_name": "Алексей Смирнов",
                    "phone": "+79993333333",
                    "specialization": "Барбер",
                    "is_universal": False
                },
                {
                    "full_name": "Елена Козлова",
                    "phone": "+79994444444",
                    "specialization": "Колорист, Стилист",
                    "is_universal": False
                },
                {
                    "full_name": "Анна Волкова",
                    "phone": "+79995555555",
                    "specialization": "Визажист",
                    "is_universal": False
                },
                {
                    "full_name": "Ольга Новикова",
                    "phone": "+79996666666",
                    "specialization": "Ногтевой мастер",
                    "is_universal": False
                }
            ]
            
            master_ids = []
            for master_data in masters_data:
                result = await session.execute(
                    text(f"""
                        INSERT INTO "{schema_name}".masters (
                            full_name, phone, specialization, is_universal, created_at, updated_at
                        ) VALUES (
                            :full_name, :phone, :specialization, :is_universal, :created_at, :updated_at
                        ) RETURNING id
                    """),
                    {**master_data, "created_at": datetime.now(), "updated_at": datetime.now()}
                )
                master_id = result.scalar_one()
                master_ids.append(master_id)
            
            await session.commit()
            print(f"  ✅ Создано {len(master_ids)} мастеров")
            
            # 4. Создаем рабочие места
            print("  🏢 Создание рабочих мест...")
            posts_data = [
                {"number": 1, "name": "Рабочее место 1", "description": "Основное рабочее место"},
                {"number": 2, "name": "Рабочее место 2", "description": "Дополнительное рабочее место"},
                {"number": 3, "name": "Рабочее место 3", "description": "VIP рабочее место"},
                {"number": 4, "name": "Рабочее место 4", "description": "Рабочее место для окрашивания"}
            ]
            
            post_ids = []
            for post_data in posts_data:
                result = await session.execute(
                    text(f"""
                        INSERT INTO "{schema_name}".posts (
                            number, name, description, is_active, created_at, updated_at
                        ) VALUES (
                            :number, :name, :description, :is_active, :created_at, :updated_at
                        ) RETURNING id
                    """),
                    {**post_data, "is_active": True, "created_at": datetime.now(), "updated_at": datetime.now()}
                )
                post_id = result.scalar_one()
                post_ids.append(post_id)
            
            await session.commit()
            print(f"  ✅ Создано {len(post_ids)} рабочих мест")
            
            # 5. Создаем клиентов
            print("  👥 Создание клиентов...")
            clients_data = [
                {
                    "full_name": "Петр Иванов",
                    "phone": "+79995555555",
                    "email": "petr@example.com"
                },
                {
                    "full_name": "Анна Смирнова",
                    "phone": "+79996666666",
                    "email": "anna@example.com"
                },
                {
                    "full_name": "Дмитрий Козлов",
                    "phone": "+79997777777",
                    "email": "dmitry@example.com"
                },
                {
                    "full_name": "Ольга Новикова",
                    "phone": "+79998888888",
                    "email": "olga@example.com"
                },
                {
                    "full_name": "Сергей Волков",
                    "phone": "+79999999999",
                    "email": "sergey@example.com"
                }
            ]
            
            client_ids = []
            for client_data in clients_data:
                result = await session.execute(
                    text(f"""
                        INSERT INTO "{schema_name}".clients (
                            full_name, phone, email, created_at
                        ) VALUES (
                            :full_name, :phone, :email, :created_at
                        ) RETURNING id
                    """),
                    {**client_data, "created_at": datetime.now()}
                )
                client_id = result.scalar_one()
                client_ids.append(client_id)
            
            await session.commit()
            print(f"  ✅ Создано {len(client_ids)} клиентов")
            
            # 6. Создаем записи на этот месяц
            print("  📅 Создание записей на этот месяц...")
            
            today = date.today()
            start_of_month = date(today.year, today.month, 1)
            
            # Создаем записи на каждый день месяца (кроме выходных)
            booking_count = 0
            current_date = start_of_month
            
            while current_date <= today:
                # Пропускаем воскресенья (день недели 6)
                if current_date.weekday() != 6:
                    # Создаем 3-5 записей в день
                    num_bookings = 4 if current_date.weekday() < 5 else 2  # Меньше в субботу
                    
                    for i in range(num_bookings):
                        # Выбираем случайные данные
                        import random
                        service_id = random.choice(service_ids)
                        master_id = random.choice(master_ids)
                        post_id = random.choice(post_ids)
                        client_id = random.choice(client_ids)
                        
                        # Время: 9:00, 10:30, 12:00, 13:30, 15:00, 16:30
                        time_slots = ["09:00", "10:30", "12:00", "13:30", "15:00", "16:30"]
                        time_slot = time_slots[i % len(time_slots)]
                        
                        # Статусы: new, confirmed, completed
                        statuses = ["new", "confirmed", "completed"]
                        # Больше подтвержденных и завершенных для прошлых дат
                        if current_date < today:
                            status = random.choice(["confirmed", "completed", "completed"])
                        else:
                            status = random.choice(["new", "confirmed"])
                        
                        # Получаем длительность услуги
                        service_duration_result = await session.execute(
                            text(f'SELECT duration FROM "{schema_name}".services WHERE id = :service_id'),
                            {"service_id": service_id}
                        )
                        duration_minutes = service_duration_result.scalar_one_or_none() or 30
                        
                        # Вычисляем время окончания
                        from datetime import time as dt_time
                        time_parts = time_slot.split(":")
                        start_hour = int(time_parts[0])
                        start_minute = int(time_parts[1])
                        start_time = dt_time(start_hour, start_minute)
                        
                        # Вычисляем end_time
                        total_minutes = start_hour * 60 + start_minute + duration_minutes
                        end_hour = total_minutes // 60
                        end_minute = total_minutes % 60
                        end_time = dt_time(end_hour, end_minute)
                        
                        # Генерируем номер записи
                        booking_number = f"BK{company_id:03d}{current_date.strftime('%Y%m%d')}{i+1:03d}"
                        
                        await session.execute(
                            text(f"""
                                INSERT INTO "{schema_name}".bookings (
                                    booking_number, client_id, service_id, master_id, post_id,
                                    date, time, duration, end_time, status,
                                    comment, created_at, updated_at
                                ) VALUES (
                                    :booking_number, :client_id, :service_id, :master_id, :post_id,
                                    :date, :time, :duration, :end_time, :status,
                                    :comment, :created_at, :updated_at
                                )
                            """),
                            {
                                "booking_number": booking_number,
                                "client_id": client_id,
                                "service_id": service_id,
                                "master_id": master_id,
                                "post_id": post_id,
                                "date": current_date,
                                "time": start_time,
                                "duration": duration_minutes,
                                "end_time": end_time,
                                "status": status,
                                "comment": f"Тестовая запись {i+1}",
                                "created_at": datetime.now(),
                                "updated_at": datetime.now()
                            }
                        )
                        booking_count += 1
                
                current_date += timedelta(days=1)
            
            await session.commit()
            print(f"  ✅ Создано {booking_count} записей на этот месяц")
            
            print("\n✅ Все тестовые данные успешно созданы!")
            
        except Exception as e:
            print(f"❌ Ошибка при создании тестовых данных: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(create_test_company())
