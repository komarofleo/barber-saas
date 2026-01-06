"""
Тест создания tenant схемы через TenantService
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.tenant_service import TenantService


async def test_tenant():
    """Тест создания tenant схемы"""
    print("=== Тест создания tenant схемы ===\n")
    
    tenant_service = TenantService()
    
    # Проверяем, существует ли схема
    print("🔍 Проверка существования схемы tenant_001...")
    exists = await tenant_service.tenancy_schema_exists(1)
    print(f"Схема tenant_001 существует: {exists}\n")
    
    if not exists:
        print("🔧 Создание схемы tenant_001...")
        await tenant_service.create_tenant_schema(1)
        print("✅ Схема tenant_001 создана!\n")
    else:
        print("⚠️  Схема уже существует\n")
    
    # Проверяем создание таблиц
    print("🔧 Создание таблиц в tenant_001...")
    await tenant_service.initialize_tenant_for_company(1)
    print("✅ Таблицы созданы в tenant_001!\n")
    
    # Проверяем, что таблицы существуют
    print("🔍 Проверка созданных таблиц...")
    async with tenant_service.get_tenant_session(1) as session:
        result = await session.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'tenant_001';"
        )
        tables = [row[0] for row in result]
        print(f"Таблицы в tenant_001 ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")
    
    print("\n=== ✅ Тест завершен успешно ===")


if __name__ == "__main__":
    asyncio.run(test_tenant())

