"""
Скрипт для проверки изоляции данных между tenant схемами.

Этот скрипт:
1. Создает 2 тестовые компании (company_1, company_2)
2. Создает tenant схемы (tenant_1, tenant_2)
3. Добавляет данные в tenant_1
4. Проверяет, что данные недоступны в tenant_2
5. Удаляет тестовые схемы

Использование:
    python web/backend/scripts/test_isolation.py
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

# Добавляем корневую директорию проекта в sys.path
# Предполагается, что скрипт запускается из web/backend/scripts
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Загружаем переменные окружения
load_dotenv(dotenv_path=project_root / '.env')

from app.services.tenant_service import get_tenant_service


async def test_isolation():
    """
    Тестирование изоляции данных между tenant схемами.
    
    План теста:
    1. Создать 2 tenant схемы (tenant_1, tenant_2)
    2. Добавить тестовые услуги в tenant_1
    3. Проверить, что услуги недоступны в tenant_2
    4. Проверить, что данные изолированы
    """
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ИЗОЛЯЦИИ ДАННЫХ МЕЖДУ TENANT СХЕМАМИ")
    print("=" * 70)
    print()
    
    company_1_id = 1
    company_2_id = 2
    
    tenant_service = get_tenant_service()
    
    # Шаг 1: Удаление старых тестовых схем (если есть)
    print("🗑️  Шаг 1: Удаление старых тестовых схем...")
    try:
        await tenant_service.drop_tenant_schema(company_1_id)
        print(f"  ✅ Схема tenant_{company_1_id} удалена")
    except Exception as e:
        print(f"  ℹ️  Схема tenant_{company_1_id} не существует: {e}")
    
    try:
        await tenant_service.drop_tenant_schema(company_2_id)
        print(f"  ✅ Схема tenant_{company_2_id} удалена")
    except Exception as e:
        print(f"  ℹ️  Схема tenant_{company_2_id} не существует: {e}")
    print()
    
    # Шаг 2: Создание tenant схем
    print("🏗️  Шаг 2: Создание tenant схем...")
    
    # Создаем схему для компании 1
    if not await tenant_service.tenancy_schema_exists(company_1_id):
        result = await tenant_service.create_tenant_schema(company_1_id)
        if result:
            print(f"  ✅ Схема tenant_{company_1_id} создана")
        else:
            print(f"  ❌ Ошибка при создании схемы tenant_{company_1_id}")
            return False
    else:
        print(f"  ℹ️  Схема tenant_{company_1_id} уже существует")
    print()
    
    # Создаем схему для компании 2
    if not await tenant_service.tenancy_schema_exists(company_2_id):
        result = await tenant_service.create_tenant_schema(company_2_id)
        if result:
            print(f"  ✅ Схема tenant_{company_2_id} создана")
        else:
            print(f"  ❌ Ошибка при создании схемы tenant_{company_2_id}")
            return False
    else:
        print(f"  ℹ️  Схема tenant_{company_2_id} уже существует")
    print()
    
    # Шаг 3: Создание тестовой таблицы и данных в tenant_1
    print("🔧️  Шаг 3: Создание тестовой таблицы в tenant_1...")
    async for session in tenant_service.get_tenant_session(company_1_id):
        # Создаем тестовую таблицу
        await session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS test_services (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    duration INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
        )
        
        # Вставляем тестовые данные
        await session.execute(
            text("""
                INSERT INTO test_services (name, description, price, duration, is_active)
                VALUES 
                ('Замена масла', 'Замена моторного масла', 1500.00, 30, TRUE),
                ('Диагностика', 'Диагностика двигателя', 2500.00, 60, TRUE),
                ('Мойка кузова', 'Полная мойка кузова', 3000.00, 120, TRUE)
            """)
        )
        
        await session.commit()
        print("  ✅ Таблица test_services создана в tenant_1")
        print("  ✅ Вставлены 3 тестовые услуги")
    print()
    
    # Шаг 4: Проверка данных в tenant_1
    print("🔍  Шаг 4: Проверка данных в tenant_1...")
    async for session in tenant_service.get_tenant_session(company_1_id):
        result = await session.execute(text("SELECT COUNT(*) FROM test_services"))
        count = result.scalar()
        print(f"  ✅ В tenant_1: {count} услуг")
        
        if count != 3:
            print(f"  ❌ Ошибка: ожидалось 3 услуги, найдено {count}")
            return False
    print()
    
    # Шаг 5: Проверка изоляции - данные не должны быть в tenant_2
    print("🔒  Шаг 5: Проверка изоляции (tenant_2 не должен видеть данные tenant_1)...")
    async for session in tenant_service.get_tenant_session(company_2_id):
        # Проверяем, что таблица test_services не существует в tenant_2
        result = await session.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'tenant_2' 
                AND table_name = 'test_services'
            """)
        )
        table_exists = result.scalar_one_or_none()
        
        if table_exists:
            print(f"  ❌ Ошибка: Таблица test_services существует в tenant_2!")
            print(f"  ❌ Изоляция НЕ работает!")
            return False
        else:
            print(f"  ✅ Таблица test_services НЕ существует в tenant_2")
        
        # Проверяем, что tenant_2 не видит данные из tenant_1
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM test_services"))
            count = result.scalar()
            print(f"  ❌ Ошибка: tenant_2 видит {count} услуг из tenant_1!")
            print(f"  ❌ Изоляция НЕ работает!")
            return False
        except Exception as e:
            # Ожидаем ошибку - таблица не существует
            if "test_services" in str(e) or "does not exist" in str(e):
                print(f"  ✅ tenant_2 НЕ видит данные из tenant_1 (таблица не существует)")
            else:
                print(f"  ⚠️  Непредвиденная ошибка: {e}")
                return False
    print()
    
    # Шаг 6: Проверка данных в tenant_1 (еще раз для уверенности)
    print("🔍  Шаг 6: Дополнительная проверка данных в tenant_1...")
    async for session in tenant_service.get_tenant_session(company_1_id):
        result = await session.execute(text("SELECT * FROM test_services ORDER BY name"))
        services = result.fetchall()
        
        print("  📋 Услуги в tenant_1:")
        for service in services:
            print(f"    - {service[1]}: {service[3]:.2f} руб. ({service[4]} мин.)")
    print()
    
    # Шаг 7: Проверка - tenant_2 пустой
    print("🔒  Шаг 7: Проверка, что tenant_2 пустой...")
    async for session in tenant_service.get_tenant_session(company_2_id):
        # Проверяем, что tenant_2 не содержит тестовую таблицу
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'tenant_2'
            """)
        )
        table_count = result.scalar()
        
        print(f"  ✅ В tenant_2: {table_count} таблиц")
        
        if table_count > 0:
            print(f"  ⚠️  Tenant_2 содержит {table_count} таблиц")
            print(f"  ℹ️  Это нормально, если в tenant_2 есть системные таблицы")
        else:
            print(f"  ✅ Tenant_2 пустой (как и ожидалось)")
    print()
    
    # Шаг 8: Удаление тестовых схем
    print("🗑️  Шаг 8: Удаление тестовых схем...")
    
    result_1 = await tenant_service.drop_tenant_schema(company_1_id)
    if result_1:
        print(f"  ✅ Схема tenant_{company_1_id} удалена")
    else:
        print(f"  ❌ Ошибка при удалении схемы tenant_{company_1_id}")
    
    result_2 = await tenant_service.drop_tenant_schema(company_2_id)
    if result_2:
        print(f"  ✅ Схема tenant_{company_2_id} удалена")
    else:
        print(f"  ❌ Ошибка при удалении схемы tenant_{company_2_id}")
    print()
    
    # Итог
    print("=" * 70)
    print("✅ ТЕСТ ИЗОЛЯЦИИ ДАННЫХ ПРОЙДЕН УСПЕШНО!")
    print("=" * 70)
    print()
    print("💡 Результаты:")
    print("  ✅ Tenant схемы созданы корректно")
    print("  ✅ Данные изолированы между схемами")
    print("  ✅ Tenant_1 видит свои данные")
    print("  ✅ Tenant_2 НЕ видит данные tenant_1")
    print("  ✅ Тестовые схемы удалены")
    print()
    print("🎯 Вывод: МУЛЬТИ-ТЕНАНТНОСТЬ РАБОТАЕТ КОРРЕКТНО!")
    print()
    
    return True


if __name__ == "__main__":
    print()
    print("⚠️  ВНИМАНИЕ: Этот скрипт создаст и удалит тестовые tenant схемы!")
    print("⚠️  Убедитесь, что вы на тестовой базе данных!")
    print()
    
    confirm = input("Продолжить? (yes/no): ")
    if confirm.lower() not in ["yes", "y"]:
        print("❌ Тест отменен")
        sys.exit(0)
    
    print()
    print("🚀 Запуск теста изоляции...")
    print()
    
    success = asyncio.run(test_isolation())
    
    if success:
        print()
        print("✅ Все тесты пройдены успешно!")
        sys.exit(0)
    else:
        print()
        print("❌ Тесты провалены!")
        sys.exit(1)

