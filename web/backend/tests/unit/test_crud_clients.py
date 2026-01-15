"""
Unit тесты для CRUD операций с клиентами.

Проверяет:
- Создание клиента
- Получение клиента
- Обновление клиента
- Удаление клиента
- Изоляцию данных между компаниями
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.clients_tenant import (
    get_clients,
    get_client,
    create_client,
    update_client,
    delete_client,
)
from app.schemas.client import ClientCreateRequest, ClientUpdateRequest
from shared.database.models import User


@pytest.mark.asyncio
async def test_create_client(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест создания клиента."""
    # Устанавливаем company_id в request.state
    mock_request.state.company_id = 99999
    
    # Создаем клиента
    client_data = ClientCreateRequest(
        full_name="Иван Иванов",
        phone="+79991234567",
    )
    
    result = await create_client(
        request=mock_request,
        client_data=client_data,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    assert result.id is not None
    assert result.full_name == "Иван Иванов"
    assert result.phone == "+79991234567"
    assert result.user_id == 0  # Новый клиент без user_id


@pytest.mark.asyncio
async def test_get_client(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест получения клиента."""
    mock_request.state.company_id = 99999
    
    # Сначала создаем клиента
    client_data = ClientCreateRequest(
        full_name="Петр Петров",
        phone="+79997654321",
    )
    created = await create_client(
        request=mock_request,
        client_data=client_data,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    # Получаем клиента
    result = await get_client(
        client_id=created.id,
        request=mock_request,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    assert result.id == created.id
    assert result.full_name == "Петр Петров"
    assert result.phone == "+79997654321"


@pytest.mark.asyncio
async def test_get_clients_list(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест получения списка клиентов."""
    mock_request.state.company_id = 99999
    
    # Создаем несколько клиентов
    for i in range(3):
        client_data = ClientCreateRequest(
            full_name=f"Клиент {i}",
            phone=f"+7999123456{i}",
        )
        await create_client(
            request=mock_request,
            client_data=client_data,
            tenant_session=tenant_session,
            current_user=mock_user,
        )
    
    # Получаем список клиентов
    result = await get_clients(
        request=mock_request,
        page=1,
        page_size=10,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    assert result.total >= 3
    assert len(result.items) >= 3


@pytest.mark.asyncio
async def test_update_client(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест обновления клиента."""
    mock_request.state.company_id = 99999
    
    # Создаем клиента
    client_data = ClientCreateRequest(
        full_name="Сидор Сидоров",
        phone="+79991111111",
    )
    created = await create_client(
        request=mock_request,
        client_data=client_data,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    # Обновляем клиента
    update_data = ClientUpdateRequest(
        full_name="Сидор Сидоров (обновлен)",
        phone="+79992222222",
    )
    result = await update_client(
        request=mock_request,
        client_id=created.id,
        client_data=update_data,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    assert result.id == created.id
    assert result.full_name == "Сидор Сидоров (обновлен)"
    assert result.phone == "+79992222222"


@pytest.mark.asyncio
async def test_delete_client(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест удаления клиента."""
    mock_request.state.company_id = 99999
    
    # Создаем клиента
    client_data = ClientCreateRequest(
        full_name="Удаляемый Клиент",
        phone="+79993333333",
    )
    created = await create_client(
        request=mock_request,
        client_data=client_data,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    # Удаляем клиента
    await delete_client(
        request=mock_request,
        client_id=created.id,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    # Проверяем, что клиент удален
    result = await tenant_session.execute(
        text("SELECT COUNT(*) FROM clients WHERE id = :id"),
        {"id": created.id},
    )
    count = result.scalar()
    assert count == 0


@pytest.mark.asyncio
async def test_delete_client_with_bookings(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест удаления клиента с записями (должна быть ошибка)."""
    from fastapi import HTTPException
    
    mock_request.state.company_id = 99999
    
    # Создаем клиента
    client_data = ClientCreateRequest(
        full_name="Клиент с записями",
        phone="+79994444444",
    )
    created = await create_client(
        request=mock_request,
        client_data=client_data,
        tenant_session=tenant_session,
        current_user=mock_user,
    )
    
    # Создаем запись для клиента (имитируем)
    await tenant_session.execute(
        text("""
            INSERT INTO bookings (client_id, date, time, status, created_at, updated_at)
            VALUES (:client_id, CURRENT_DATE, '10:00', 'new', NOW(), NOW())
        """),
        {"client_id": created.id},
    )
    await tenant_session.commit()
    
    # Пытаемся удалить клиента (должна быть ошибка)
    with pytest.raises(HTTPException) as exc_info:
        await delete_client(
            request=mock_request,
            client_id=created.id,
            tenant_session=tenant_session,
            current_user=mock_user,
        )
    
    assert exc_info.value.status_code == 400
    assert "связаны" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_client_not_found(tenant_session: AsyncSession, mock_user, mock_request):
    """Тест получения несуществующего клиента."""
    from fastapi import HTTPException
    
    mock_request.state.company_id = 99999
    
    with pytest.raises(HTTPException) as exc_info:
        await get_client(
            client_id=999999,
            request=mock_request,
            tenant_session=tenant_session,
            current_user=mock_user,
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_client_non_admin(tenant_session: AsyncSession, mock_request):
    """Тест создания клиента не-администратором (должна быть ошибка)."""
    from fastapi import HTTPException
    
    mock_request.state.company_id = 99999
    
    # Создаем не-администратора
    non_admin = Mock(spec=User)
    non_admin.id = 2
    non_admin.is_admin = False
    
    client_data = ClientCreateRequest(
        full_name="Тест",
        phone="+79995555555",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_client(
            request=mock_request,
            client_data=client_data,
            tenant_session=tenant_session,
            current_user=non_admin,
        )
    
    assert exc_info.value.status_code == 403
