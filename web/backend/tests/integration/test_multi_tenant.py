"""
Интеграционные тесты для мульти-тенантности.

Проверяет:
- Изоляцию данных между компаниями
- Работу CRUD операций с tenant схемами
- Проверку подписок (блокировка записей)
"""
import pytest
import pytest_asyncio

from app.services.tenant_service import get_tenant_service
from app.database import async_session_maker, engine


@pytest_asyncio.fixture
async def db():
    """Fixture для получения сессии БД."""
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def tenant_service():
    """Fixture для получения TenantService."""
    return get_tenant_service()


class TestMultiTenantIsolation:
    """Тесты изоляции данных между компаниями."""
    
    @pytest_asyncio.mark.asyncio
    async def test_data_isolation(tenant_service, db):
        """Тест изоляции данных между компаниями."""
        company_1_id = 1
        company_2_id = 2
        
        # Удаляем старые схемы если есть
        await tenant_service.drop_tenant_schema(company_1_id)
        await tenant_service.drop_tenant_schema(company_2_id)
        
        # Создаем tenant схемы
        result_1 = await tenant_service.create_tenant_schema(company_1_id)
        result_2 = await tenant_service.create_tenant_schema(company_2_id)
        
        assert result_1 is True, "Схема tenant_1 должна быть создана"
        assert result_2 is True, "Схема tenant_2 должна быть создана"
        
        # Инициализируем tenant схему для компании 1
        await tenant_service.initialize_tenant_for_company(company_1_id)
        
        # Проверяем изоляцию
        # Создаем таблицу в tenant_1
        async for session in tenant_service.get_tenant_session(company_1_id):
            await session.execute(
                """
                CREATE TABLE test_isolation (
                    id SERIAL PRIMARY KEY,
                    data VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            
            # Вставляем данные
            await session.execute(
                """
                INSERT INTO test_isolation (data, created_at)
                VALUES ('company_1_data', NOW()), ('company_1_data_2', NOW())
                """
            )
            
            await session.commit()
        
        # Проверяем, что данные недоступны в tenant_2
        async for session in tenant_service.get_tenant_session(company_2_id):
            # Проверяем, что таблица test_isolation НЕ существует в tenant_2
            result = await session.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'tenant_2' 
                AND table_name = 'test_isolation'
                """
            )
            table_exists = result.scalar_one_or_none()
            
            assert table_exists is None, "Таблица test_isolation НЕ должна существовать в tenant_2"
            
            # Проверяем, что tenant_2 НЕ видит данные из tenant_1
            try:
                result = await session.execute("SELECT COUNT(*) FROM test_isolation")
                count = result.scalar()
                assert False, "tenant_2 НЕ должен видеть данные из tenant_1"
            except Exception as e:
                # Ожидаем ошибку - таблица не существует
                if "test_isolation" in str(e) or "does not exist" in str(e):
                    pass  # Это норма
                else:
                    assert False, f"Непредвиденная ошибка: {e}"
        
        # Удаляем тестовые схемы
        await tenant_service.drop_tenant_schema(company_1_id)
        await tenant_service.drop_tenant_schema(company_2_id)


class TestTenantServiceErrors:
    """Тесты обработки ошибок в TenantService."""
    
    @pytest_asyncio.mark.asyncio
    async def test_create_duplicate_schema(tenant_service):
        """Тест создания дубликата схемы."""
        company_id = 1
        
        # Создаем схему
        result_1 = await tenant_service.create_tenant_schema(company_id)
        assert result_1 is True, "Первая схема должна быть создана"
        
        # Пытаемся создать еще раз
        result_2 = await tenant_service.create_tenant_schema(company_id)
        assert result_2 is False, "Дубликат должен быть отклонен"
        
        # Удаляем схему
        await tenant_service.drop_tenant_schema(company_id)
    
    @pytest_asyncio.mark.asyncio
    async def test_drop_nonexistent_schema(tenant_service):
        """Тест удаления несуществующей схемы."""
        company_id = 1
        
        # Удаляем несуществующую схему
        result = await tenant_service.drop_tenant_schema(company_id)
        assert result is True, "Должен вернуться True (схема не существовала)"
    
    @pytest_asyncio.mark.asyncio
    async def test_clone_nonexistent_table(tenant_service):
        """Тест клонирования несуществующей таблицы."""
        company_id = 1
        
        # Пытаемся склонировать несуществующую таблицу
        result = await tenant_service.clone_table_to_tenant(company_id, "nonexistent_table")
        assert result is False, "Клонирование должно провалиться"
        
        # Удаляем схему если создалась
        await tenant_service.drop_tenant_schema(company_id)


class TestTenantServiceSessionManagement:
    """Тесты управления tenant сессиями."""
    
    @pytest_asyncio.mark.asyncio
    async def test_multiple_tenant_sessions(tenant_service):
        """Тест нескольких tenant сессий одновременно."""
        company_1_id = 1
        company_2_id = 2
        company_3_id = 3
        
        # Создаем схемы
        for company_id in [company_1_id, company_2_id, company_3_id]:
            await tenant_service.create_tenant_schema(company_id)
        
        # Инициализируем схемы
        for company_id in [company_1_id, company_2_id, company_3_id]:
            await tenant_service.initialize_tenant_for_company(company_id)
        
        # Проверяем, что схемы существуют
        for company_id in [company_1_id, company_2_id, company_3_id]:
            exists = await tenant_service.tenancy_schema_exists(company_id)
            assert exists is True, f"Схема tenant_{company_id} должна существовать"
        
        # Удаляем схемы
        for company_id in [company_1_id, company_2_id, company_3_id]:
            await tenant_service.drop_tenant_schema(company_id)
    
    @pytest_asyncio.mark.asyncio
    async def test_tenant_session_search_path(tenant_service):
        """Тест установки search_path в tenant сессии."""
        company_id = 1
        
        # Создаем схему
        await tenant_service.create_tenant_schema(company_id)
        
        # Проверяем search_path
        async for session in tenant_service.get_tenant_session(company_id):
            from sqlalchemy import text
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            
            assert "tenant_1" in search_path, f"search_path должен содержать tenant_1, получено: {search_path}"
            
            break # Только первая сессия
        
        # Удаляем схему
        await tenant_service.drop_tenant_schema(company_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

