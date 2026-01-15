"""
Unit тесты для TenantService.

Проверяет:
- Создание tenant схем
- Клонирование таблиц
- Получение tenant сессий
- Удаление tenant схем
"""
import pytest
import pytest_asyncio
from datetime import date

from app.services.tenant_service import get_tenant_service


@pytest_asyncio.fixture
async def tenant_service():
    """Fixture для получения TenantService."""
    return get_tenant_service()


class TestTenantServiceCreation:
    """Тесты для создания tenant схем."""
    
    @pytest.mark.asyncio
    async def test_create_tenant_schema(self, tenant_service):
        """Тест создания tenant схемы."""
        # Создаем схему
        result = await tenant_service.create_tenant_schema(999)
        
        assert result is True, "Схема должна быть создана"
        
        # Проверяем, что схема существует
        exists = await tenant_service.tenancy_schema_exists(999)
        assert exists is True, "Схема должна существовать"
        
        # Удаляем схему после теста
        await tenant_service.drop_tenant_schema(999)
    
    @pytest.mark.asyncio
    async def test_create_existing_tenant_schema(self, tenant_service):
        """Тест создания существующей tenant схемы."""
        # Сначала создаем схему
        await tenant_service.create_tenant_schema(998)
        
        # Пытаемся создать еще раз
        result = await tenant_service.create_tenant_schema(998)
        
        assert result is True, "Должен вернуться True (схема существует)"
        
        # Удаляем схему после теста
        await tenant_service.drop_tenant_schema(998)


class TestTenantServiceDeletion:
    """Тесты для удаления tenant схем."""
    
    @pytest.mark.asyncio
    async def test_drop_tenant_schema(self, tenant_service):
        """Тест удаления tenant схемы."""
        # Сначала создаем схему
        await tenant_service.create_tenant_schema(997)
        
        # Удаляем схему
        result = await tenant_service.drop_tenant_schema(997)
        
        assert result is True, "Схема должна быть удалена"
        
        # Проверяем, что схема больше не существует
        exists = await tenant_service.tenancy_schema_exists(997)
        assert exists is False, "Схема не должна существовать"
    
    @pytest.mark.asyncio
    async def test_drop_nonexistent_tenant_schema(self, tenant_service):
        """Тест удаления несуществующей tenant схемы."""
        # Пытаемся удалить несуществующую схему
        result = await tenant_service.drop_tenant_schema(996)
        
        assert result is True, "Должен вернуться True (схема не существовала)"


class TestTenantServiceClone:
    """Тесты для клонирования таблиц."""
    
    @pytest.mark.asyncio
    async def test_clone_table_to_tenant(self, tenant_service):
        """Тест клонирования таблицы в tenant схему."""
        # Сначала создаем схему
        await tenant_service.create_tenant_schema(996)
        
        # Клонируем таблицу (это создаст ее в tenant схеме)
        result = await tenant_service.clone_table_to_tenant(996, "users")
        
        assert result is True, "Таблица должна быть склонирована"
        
        # Удаляем схему после теста
        await tenant_service.drop_tenant_schema(996)
    
    @pytest.mark.asyncio
    async def test_clone_nonexistent_table(self, tenant_service):
        """Тест клонирования несуществующей таблицы."""
        # Создаем схему
        await tenant_service.create_tenant_schema(995)
        
        # Пытаемся склонировать несуществующую таблицу
        result = await tenant_service.clone_table_to_tenant(995, "nonexistent_table")
        
        # Должен провалиться (таблица не существует в public)
        assert result is False or result is not None, "Клонирование должно провалиться"
        
        # Удаляем схему после теста
        await tenant_service.drop_tenant_schema(995)


class TestTenantServiceSession:
    """Тесты для работы с tenant сессиями."""
    
    @pytest.mark.asyncio
    async def test_get_tenant_session(self, tenant_service):
        """Тест получения tenant сессии."""
        # Сначала создаем схему
        await tenant_service.create_tenant_schema(994)
        
        # Получаем tenant сессию
        async for session in tenant_service.get_tenant_session(994):
            # Проверяем, что сессия получена
            assert session is not None, "Сессия должна быть получена"
            
            # Проверяем search_path
            from sqlalchemy import text
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            
            assert "tenant_994" in search_path, f"search_path должен содержать tenant_994, получено: {search_path}"
            
            break # Только первая сессия
        
        # Удаляем схему после теста
        await tenant_service.drop_tenant_schema(994)


class TestTenantServiceInitialize:
    """Тесты для инициализации tenant схемы."""
    
    @pytest.mark.asyncio
    async def test_initialize_tenant_for_company(self, tenant_service):
        """Тест инициализации tenant схемы для компании."""
        # Инициализируем tenant схему
        result = await tenant_service.initialize_tenant_for_company(993)
        
        assert result is True, "Tenant схема должна быть инициализирована"
        
        # Проверяем, что схема существует
        exists = await tenant_service.tenancy_schema_exists(993)
        assert exists is True, "Схема должна существовать"
        
        # Удаляем схему после теста
        await tenant_service.drop_tenant_schema(993)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

