"""
Скрипт для миграции текущего клиента в tenant схему.

Выполняет следующие действия:
1. Создает tenant схему для текущего клиента (tenant_001)
2. Копирует все таблицы из схемы по умолчанию в tenant_001
3. Копирует данные из всех таблиц
4. Создает запись компании в public схеме
5. Создает подписку для компании

Использование:
    python -m scripts.migrate_existing_client
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select, insert
from sqlalchemy.orm import Session

# Импортируем TenantService
from app.services.tenant_service import TenantService, get_tenant_service

# Импортируем модели
from app.models.public_models import Company, Plan, Subscription
from shared.database.models import Base


# Настройки подключения к БД
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "barber_db")
DB_USER = os.getenv("DB_USER", "barber_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# Список таблиц для миграции
TABLES_TO_MIGRATE = [
    "users",
    "services",
    "masters",
    "clients",
    "bookings",
    "posts",
    "slots",
    "notifications",
    "settings",
    "blocks",
    "promocodes",
    "promotions",
    "broadcasts",
]


async def migrate_to_tenant():
    """
    Мигрировать данные текущего клиента в tenant схему.
    """
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("=== Начало миграции клиента в tenant схему ===\n")
    
    try:
        async with engine.begin() as conn:
            # ===========================
            # Шаг 1: Создать tenant схему
            # ===========================
            print("📌 Шаг 1: Создание tenant схемы")
            
            company_id = 1  # ID текущего клиента (tenant_001)
            schema_name = f"tenant_{company_id}"
            
            # Проверяем, существует ли схема
            result = await conn.execute(
                text(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{schema_name}'")
            )
            existing_schema = result.scalar_one_or_none()
            
            if existing_schema:
                print(f"⚠️  Схема {schema_name} уже существует!")
                response = input("Хотите удалить и создать заново? (y/N): ")
                if response.lower() == 'y':
                    print(f"🗑️  Удаление схемы {schema_name}...")
                    await conn.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
                    await conn.commit()
                    print(f"✅ Схема {schema_name} удалена")
                else:
                    print("❌ Отмена миграции")
                    return
            
            # Создаем tenant схему
            print(f"🔧 Создание схемы {schema_name}...")
            await conn.execute(text(f"CREATE SCHEMA {schema_name}"))
            await conn.commit()
            print(f"✅ Схема {schema_name} создана\n")
            
            # ===========================
            # Шаг 2: Скопировать структуру таблиц
            # ===========================
            print("📌 Шаг 2: Копирование структуры таблиц")
            
            for table_name in TABLES_TO_MIGRATE:
                print(f"🔧 Копирование таблицы {table_name}...")
                
                # Получаем CREATE TABLE из public схемы
                result = await conn.execute(
                    text(f"""
                        SELECT pg_get_tabledef('{table_name}'::regclass)
                    """)
                )
                create_table_sql = result.scalar_one_or_none()
                
                if not create_table_sql:
                    print(f"⚠️  Таблица {table_name} не найдена в public схеме")
                    continue
                
                # Заменяем схему на tenant схему
                create_table_sql = create_table_sql.replace("public.", f"{schema_name}.")
                
                # Создаем таблицу в tenant схеме
                await conn.execute(text(create_table_sql))
                await conn.commit()
                print(f"✅ Таблица {table_name} создана в {schema_name}")
            
            print(f"\n✅ Структура таблиц скопирована\n")
            
            # ===========================
            # Шаг 3: Скопировать данные
            # ===========================
            print("📌 Шаг 3: Копирование данных")
            
            for table_name in TABLES_TO_MIGRATE:
                print(f"🔧 Копирование данных из {table_name}...")
                
                # Копируем данные
                await conn.execute(
                    text(f"INSERT INTO {schema_name}.{table_name} SELECT * FROM public.{table_name}")
                )
                await conn.commit()
                
                # Получаем количество скопированных строк
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
                )
                count = result.scalar_one_or_none()
                print(f"✅ Скопировано {count} записей в {table_name}")
            
            print(f"\n✅ Данные скопированы\n")
            
            # ===========================
            # Шаг 4: Сбросить sequence
            # ===========================
            print("📌 Шаг 4: Сброс sequence")
            
            for table_name in TABLES_TO_MIGRATE:
                # Сбрасываем sequence для каждой таблицы
                result = await conn.execute(
                    text(f"""
                        SELECT pg_get_serial_sequence('{schema_name}.{table_name}'::regclass)
                    """)
                )
                sequence_name = result.scalar_one_or_none()
                
                if sequence_name:
                    print(f"🔧 Сброс sequence для {table_name}...")
                    await conn.execute(
                        text(f"SELECT setval(pg_get_serial_sequence('{schema_name}.{table_name}'::regclass), (SELECT MAX(id) FROM {schema_name}.{table_name}))")
                    )
                    await conn.commit()
                    print(f"✅ Sequence для {table_name} сброшен")
            
            print(f"\n✅ Sequence сброшены\n")
            
            # ===========================
            # Шаг 5: Создать запись компании в public схеме
            # ===========================
            print("📌 Шаг 5: Создание записи компании в public схеме")
            
            # Получаем план Business (id=3)
            await conn.execute(
                text("""
                    INSERT INTO public.companies (
                        id, name, email, phone, telegram_bot_token,
                        plan_id, subscription_status, subscription_end_date,
                        can_create_bookings, is_active, is_blocked,
                        created_at, updated_at
                    )
                    VALUES (
                        1, 'Barber #1', 'barber1@example.com', '+79001234567',
                        'test_bot_token_for_tenant_001',
                        3, 'active', :end_date,
                        true, true, false,
                        now(), now()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        email = EXCLUDED.email,
                        updated_at = now()
                """),
                {"end_date": date.today() + timedelta(days=30)}
            )
            await conn.commit()
            print("✅ Запись компании создана\n")
            
            # ===========================
            # Шаг 6: Создать подписку для компании
            # ===========================
            print("📌 Шаг 6: Создание подписки для компании")
            
            await conn.execute(
                text("""
                    INSERT INTO public.subscriptions (
                        company_id, plan_id, start_date, end_date,
                        status, trial_used, auto_renewal,
                        created_at, updated_at
                    )
                    VALUES (
                        1, 3, :start_date, :end_date,
                        'active', true, false,
                        now(), now()
                    )
                    ON CONFLICT (company_id) DO UPDATE SET
                        end_date = EXCLUDED.end_date,
                        status = EXCLUDED.status,
                        updated_at = now()
                """),
                {
                    "start_date": date.today(),
                    "end_date": date.today() + timedelta(days=30)
                }
            )
            await conn.commit()
            print("✅ Подписка создана\n")
            
            # ===========================
            # Шаг 7: Проверка изоляции данных
            # ===========================
            print("📌 Шаг 7: Проверка изоляции данных")
            
            for table_name in TABLES_TO_MIGRATE:
                # Получаем количество записей в public схеме
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM public.{table_name}")
                )
                public_count = result.scalar_one_or_none()
                
                # Получаем количество записей в tenant схеме
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")
                )
                tenant_count = result.scalar_one_or_none()
                
                if public_count == tenant_count:
                    print(f"✅ {table_name}: {public_count} записей (изоляция OK)")
                else:
                    print(f"⚠️  {table_name}: public={public_count}, tenant={tenant_count} (проверьте!)")
            
            print("\n")
            
            # ===========================
            # Шаг 8: Бэкап данных из public схемы
            # ===========================
            print("📌 Шаг 8: Бэкап данных из public схемы")
            
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for table_name in TABLES_TO_MIGRATE:
                print(f"🔧 Бэкап таблицы {table_name}...")
                await conn.execute(
                    text(f"""
                        CREATE TABLE IF NOT EXISTS public.{table_name}_backup_{backup_suffix} AS
                        SELECT * FROM public.{table_name}
                    """)
                )
                await conn.commit()
                print(f"✅ Бэкап создан: {table_name}_backup_{backup_suffix}")
            
            print("\n")
            
            # ===========================
            # Шаг 9: Удалить данные из public схемы
            # ===========================
            print("📌 Шаг 9: Удаление данных из public схемы")
            
            response = input("Хотите удалить данные из public схемы? (y/N): ")
            if response.lower() == 'y':
                for table_name in TABLES_TO_MIGRATE:
                    print(f"🗑️  Удаление данных из {table_name}...")
                    await conn.execute(text(f"DELETE FROM public.{table_name}"))
                    await conn.commit()
                    print(f"✅ Данные из {table_name} удалены")
                print("\n✅ Данные из public схемы удалены\n")
            else:
                print("⏭️  Данные из public схемы сохранены\n")
        
        print("=== ✅ Миграция завершена успешно ===\n")
        print(f"📊 Результаты:")
        print(f"  - Tenant схема: {schema_name}")
        print(f"  - Company ID: {company_id}")
        print(f"  - Перенесено таблиц: {len(TABLES_TO_MIGRATE)}")
        print(f"  - Подписка создана до: {(date.today() + timedelta(days=30)).strftime('%d.%m.%Y')}")
        print(f"\n💡 Следующие шаги:")
        print(f"  1. Протестируйте работу с tenant схемой")
        print(f"  2. Проверьте изоляцию данных")
        print(f"  3. Удалите данные из public схемы (если нужно)")
        print(f"  4. Сделайте бэкап БД")
        
    except Exception as e:
        print(f"\n❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        await conn.rollback()
        print("\n⚠️  Транзакция откачена")
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print("=" * 60)
    print("Миграция текущего клиента в tenant схему")
    print("=" * 60)
    print()
    print("⚠️  Внимание!")
    print("  - Перед запуском убедитесь, что у вас есть бэкап БД")
    print("  - Этот скрипт создаст tenant схему tenant_001")
    print("  - Все данные будут скопированы в tenant_001")
    print("  - Будет создана запись компании в public схеме")
    print("  - Будет создана подписка на 30 дней")
    print()
    response = input("Продолжить? (y/N): ")
    
    if response.lower() == 'y':
        print()
        asyncio.run(migrate_to_tenant())
    else:
        print("❌ Отмена миграции")

