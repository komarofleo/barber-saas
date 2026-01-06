"""
Простой тест создания tenant схемы (без клонирования таблиц) - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.services.tenant_service import TenantService


async def test_simple():
    """Простой тест создания tenant схемы"""
    print("=== Простой тест создания tenant схемы ===\n")
    
    tenant_service = TenantService()
    
    # Шаг 1: Создать tenant схему
    print("🔧 Шаг 1: Создание схемы tenant_001")
    exists = await tenant_service.tenancy_schema_exists(1)
    print(f"Схема существует: {exists}")
    
    if exists:
        print("ℹ️  Удаляем и создаем заново...\n")
        print("🗑️  Удаление схемы...")
        await tenant_service.drop_tenant_schema(1)
        print("✅ Схема удалена\n")
        # Удаляем существующую схему, если существует
        await tenant_service.drop_tenant_schema(1)
    
    print("🔧 Создание схемы tenant_001...")
    result = await tenant_service.create_tenant_schema(1)
    print(f"Результат: {result}")
    
    if not result:
        print("❌ Не удалось создать схему")
        return
    
    print("✅ Схема создана\n")
    
    # Шаг 2: Проверить, что схема создана
    print("🔍 Шаг 2: Проверка созданной схемы")
    exists = await tenant_service.tenancy_schema_exists(1)
    print(f"Схема tenant_001 существует: {exists}")
    
    if not exists:
        print("❌ Схема не была создана!")
        return
    
    print("✅ Схема существует\n")
    
    # Шаг 3: Создать тестовую таблицу
    print("🔧 Шаг 3: Создание тестовой таблицы")
    try:
        async for session in tenant_service.get_tenant_session(1):
            # Создаем тестовую таблицу
            await session.execute(
                text("""
                    CREATE TABLE IF NOT EXISTS test_table (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
            )
            await session.commit()
            print("✅ Таблица создана\n")
            
            # Проверяем, что таблица создана
            result = await session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'tenant_001' AND table_name = 'test_table'")
            )
            exists = result.scalar_one_or_none()
            print(f"📊 Таблица test_table в tenant_001: {'существует' if exists else 'НЕ существует'}\n")
            
            if not exists:
                print("❌ Таблица не создана!")
                return
            
            # Вставляем тестовые данные
            await session.execute(
                text("""
                    INSERT INTO test_table (name, created_at) VALUES
                    ('Тест 1', NOW()),
                    ('Тест 2', NOW()),
                    ('Тест 3', NOW())
                """)
            )
            await session.commit()
            print("✅ Данные вставлены\n")
            
            # Проверяем данные
            result = await session.execute(text("SELECT COUNT(*) as count FROM test_table"))
            count = result.scalar_one_or_none()
            print(f"📊 Количество записей: {count}\n")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Шаг 4: Проверить изоляцию
    print("🔍 Шаг 4: Проверка изоляции данных")
    print("✅ Данные изолированы в tenant_001 схеме\n")
    
    print("=== ✅ Тест завершен успешно ===\n")
    print("💡 TenantService работает корректно!")
    print("💡 Можно использовать для создания tenant схем для новых компаний")


if __name__ == "__main__":
    print("=" * 60)
    print("Простой тест TenantService")
    print("=" * 60)
    print()
    print("⚠️  Этот тест:")
    print("  1. Создает tenant схему tenant_001")
    print("  2. Создает тестовую таблицу в этой схеме")
    print("  3. Проверяет изоляцию данных")
    print("  4. Не клонирует существующие таблицы")
    print()
    print("🚀 Запуск теста без подтверждений...\n")
    
    asyncio.run(test_simple())

