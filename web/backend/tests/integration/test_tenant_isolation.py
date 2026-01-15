"""
Интеграционные тесты для изоляции данных между tenant схемами.

Проверяет:
- Данные одной компании недоступны другой
- CRUD операции работают изолированно
- search_path правильно устанавливается
"""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tenant_service import get_tenant_service


@pytest.mark.integration
@pytest.mark.tenant
class TestTenantDataIsolation:
    """Тесты изоляции данных между tenant схемами."""
    
    @pytest.mark.asyncio
    async def test_clients_isolation(self, tenant_service):
        """Тест изоляции клиентов между компаниями."""
        company_1_id = 100001
        company_2_id = 100002
        
        # Очищаем схемы перед тестом
        await tenant_service.drop_tenant_schema(company_1_id)
        await tenant_service.drop_tenant_schema(company_2_id)
        
        try:
            # Создаем и инициализируем схемы
            await tenant_service.create_tenant_schema(company_1_id)
            await tenant_service.initialize_tenant_for_company(company_1_id)
            
            await tenant_service.create_tenant_schema(company_2_id)
            await tenant_service.initialize_tenant_for_company(company_2_id)
            
            # Создаем клиента в company_1
            async for session in tenant_service.get_tenant_session(company_1_id):
                await session.execute(
                    text("""
                        INSERT INTO clients (full_name, phone, created_at, updated_at)
                        VALUES ('Клиент 1', '+79991111111', NOW(), NOW())
                    """)
                )
                await session.commit()
                break
            
            # Создаем клиента в company_2
            async for session in tenant_service.get_tenant_session(company_2_id):
                await session.execute(
                    text("""
                        INSERT INTO clients (full_name, phone, created_at, updated_at)
                        VALUES ('Клиент 2', '+79992222222', NOW(), NOW())
                    """)
                )
                await session.commit()
                break
            
            # Проверяем, что company_1 видит только своего клиента
            async for session in tenant_service.get_tenant_session(company_1_id):
                result = await session.execute(
                    text("SELECT COUNT(*) FROM clients")
                )
                count_1 = result.scalar()
                assert count_1 == 1, "company_1 должна видеть только 1 клиента"
                
                result = await session.execute(
                    text("SELECT full_name FROM clients")
                )
                name = result.scalar()
                assert name == "Клиент 1", "company_1 должна видеть только 'Клиент 1'"
                break
            
            # Проверяем, что company_2 видит только своего клиента
            async for session in tenant_service.get_tenant_session(company_2_id):
                result = await session.execute(
                    text("SELECT COUNT(*) FROM clients")
                )
                count_2 = result.scalar()
                assert count_2 == 1, "company_2 должна видеть только 1 клиента"
                
                result = await session.execute(
                    text("SELECT full_name FROM clients")
                )
                name = result.scalar()
                assert name == "Клиент 2", "company_2 должна видеть только 'Клиент 2'"
                break
        
        finally:
            # Очищаем схемы после теста
            await tenant_service.drop_tenant_schema(company_1_id)
            await tenant_service.drop_tenant_schema(company_2_id)
    
    @pytest.mark.asyncio
    async def test_bookings_isolation(self, tenant_service):
        """Тест изоляции записей между компаниями."""
        company_1_id = 100003
        company_2_id = 100004
        
        # Очищаем схемы перед тестом
        await tenant_service.drop_tenant_schema(company_1_id)
        await tenant_service.drop_tenant_schema(company_2_id)
        
        try:
            # Создаем и инициализируем схемы
            await tenant_service.create_tenant_schema(company_1_id)
            await tenant_service.initialize_tenant_for_company(company_1_id)
            
            await tenant_service.create_tenant_schema(company_2_id)
            await tenant_service.initialize_tenant_for_company(company_2_id)
            
            # Создаем клиента и запись в company_1
            async for session in tenant_service.get_tenant_session(company_1_id):
                # Создаем клиента
                await session.execute(
                    text("""
                        INSERT INTO clients (full_name, phone, created_at, updated_at)
                        VALUES ('Клиент для записи 1', '+79991111111', NOW(), NOW())
                        RETURNING id
                    """)
                )
                client_result = await session.execute(text("SELECT id FROM clients LIMIT 1"))
                client_id = client_result.scalar()
                
                # Создаем запись
                await session.execute(
                    text("""
                        INSERT INTO bookings (client_id, date, time, status, created_at, updated_at)
                        VALUES (:client_id, CURRENT_DATE, '10:00', 'new', NOW(), NOW())
                    """),
                    {"client_id": client_id}
                )
                await session.commit()
                break
            
            # Создаем клиента и запись в company_2
            async for session in tenant_service.get_tenant_session(company_2_id):
                # Создаем клиента
                await session.execute(
                    text("""
                        INSERT INTO clients (full_name, phone, created_at, updated_at)
                        VALUES ('Клиент для записи 2', '+79992222222', NOW(), NOW())
                        RETURNING id
                    """)
                )
                client_result = await session.execute(text("SELECT id FROM clients LIMIT 1"))
                client_id = client_result.scalar()
                
                # Создаем запись
                await session.execute(
                    text("""
                        INSERT INTO bookings (client_id, date, time, status, created_at, updated_at)
                        VALUES (:client_id, CURRENT_DATE, '14:00', 'new', NOW(), NOW())
                    """),
                    {"client_id": client_id}
                )
                await session.commit()
                break
            
            # Проверяем изоляцию записей
            async for session in tenant_service.get_tenant_session(company_1_id):
                result = await session.execute(
                    text("SELECT COUNT(*) FROM bookings")
                )
                count = result.scalar()
                assert count == 1, "company_1 должна видеть только 1 запись"
                
                result = await session.execute(
                    text("SELECT time FROM bookings")
                )
                time = result.scalar()
                assert time == "10:00", "company_1 должна видеть запись на 10:00"
                break
            
            async for session in tenant_service.get_tenant_session(company_2_id):
                result = await session.execute(
                    text("SELECT COUNT(*) FROM bookings")
                )
                count = result.scalar()
                assert count == 1, "company_2 должна видеть только 1 запись"
                
                result = await session.execute(
                    text("SELECT time FROM bookings")
                )
                time = result.scalar()
                assert time == "14:00", "company_2 должна видеть запись на 14:00"
                break
        
        finally:
            # Очищаем схемы после теста
            await tenant_service.drop_tenant_schema(company_1_id)
            await tenant_service.drop_tenant_schema(company_2_id)
    
    @pytest.mark.asyncio
    async def test_search_path_isolation(self, tenant_service):
        """Тест правильной установки search_path для изоляции."""
        company_id = 100005
        
        # Очищаем схему перед тестом
        await tenant_service.drop_tenant_schema(company_id)
        
        try:
            # Создаем и инициализируем схему
            await tenant_service.create_tenant_schema(company_id)
            await tenant_service.initialize_tenant_for_company(company_id)
            
            # Проверяем search_path
            async for session in tenant_service.get_tenant_session(company_id):
                result = await session.execute(text("SHOW search_path"))
                search_path = result.scalar()
                
                assert f"tenant_{company_id}" in search_path, \
                    f"search_path должен содержать tenant_{company_id}, получено: {search_path}"
                
                # Проверяем, что можем работать с таблицами tenant схемы
                result = await session.execute(
                    text("SELECT COUNT(*) FROM clients")
                )
                count = result.scalar()
                assert count is not None, "Должны иметь доступ к таблице clients"
                break
        
        finally:
            # Очищаем схему после теста
            await tenant_service.drop_tenant_schema(company_id)
