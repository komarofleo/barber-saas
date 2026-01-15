"""
E2E тесты для основного потока работы с записями.

Проверяет:
- Создание записи через API
- Смена статуса записи
- Уведомления (моки)
- Полный цикл работы с записью
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import date, time, datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.bookings import (
    get_bookings,
    get_booking,
    create_booking,
    update_booking,
)
from app.schemas.booking import BookingCreateRequest, BookingUpdateRequest
from app.services.tenant_service import get_tenant_service


@pytest.mark.e2e
class TestBookingFlow:
    """E2E тесты для потока работы с записями."""
    
    @pytest.mark.asyncio
    async def test_create_booking_flow(self, tenant_session: AsyncSession, mock_user, mock_request):
        """Тест полного потока создания записи."""
        mock_request.state.company_id = 99999
        
        # Создаем необходимые данные для записи
        # 1. Создаем клиента
        await tenant_session.execute(
            text("""
                INSERT INTO clients (full_name, phone, created_at, updated_at)
                VALUES ('E2E Клиент', '+79999999999', NOW(), NOW())
                RETURNING id
            """)
        )
        client_result = await tenant_session.execute(
            text("SELECT id FROM clients WHERE full_name = 'E2E Клиент'")
        )
        client_id = client_result.scalar()
        
        # 2. Создаем услугу
        await tenant_session.execute(
            text("""
                INSERT INTO services (name, price, duration, created_at, updated_at)
                VALUES ('E2E Услуга', 1000, 60, NOW(), NOW())
                RETURNING id
            """)
        )
        service_result = await tenant_session.execute(
            text("SELECT id FROM services WHERE name = 'E2E Услуга'")
        )
        service_id = service_result.scalar()
        
        # 3. Создаем мастера
        await tenant_session.execute(
            text("""
                INSERT INTO masters (full_name, phone, is_active, created_at, updated_at)
                VALUES ('E2E Мастер', '+79998888888', true, NOW(), NOW())
                RETURNING id
            """)
        )
        master_result = await tenant_session.execute(
            text("SELECT id FROM masters WHERE full_name = 'E2E Мастер'")
        )
        master_id = master_result.scalar()
        
        await tenant_session.commit()
        
        # 4. Создаем запись
        booking_data = BookingCreateRequest(
            client_id=client_id,
            service_id=service_id,
            master_id=master_id,
            date=date.today(),
            time=time(10, 0),
            status="new",
        )
        
        # Мокаем уведомления, чтобы не отправлять реальные Telegram сообщения
        with patch('app.api.bookings.notify_admins_about_new_booking', new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = True
            
            created_booking = await create_booking(
                request=mock_request,
                booking_data=booking_data,
                tenant_session=tenant_session,
                current_user=mock_user,
            )
            
            assert created_booking.id is not None
            assert created_booking.client_id == client_id
            assert created_booking.service_id == service_id
            assert created_booking.master_id == master_id
            assert created_booking.status == "new"
            
            # Проверяем, что уведомление было вызвано
            mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_booking_status_flow(self, tenant_session: AsyncSession, mock_user, mock_request):
        """Тест потока смены статуса записи."""
        mock_request.state.company_id = 99999
        
        # Создаем необходимые данные
        # 1. Создаем клиента с user_id (для уведомлений)
        await tenant_session.execute(
            text("""
                INSERT INTO users (full_name, phone, role, telegram_id, created_at, updated_at)
                VALUES ('E2E Пользователь', '+79997777777', 'client', 123456789, NOW(), NOW())
                RETURNING id
            """)
        )
        user_result = await tenant_session.execute(
            text("SELECT id FROM users WHERE full_name = 'E2E Пользователь'")
        )
        user_id = user_result.scalar()
        
        await tenant_session.execute(
            text("""
                INSERT INTO clients (full_name, phone, user_id, created_at, updated_at)
                VALUES ('E2E Клиент с User', '+79996666666', :user_id, NOW(), NOW())
                RETURNING id
            """),
            {"user_id": user_id}
        )
        client_result = await tenant_session.execute(
            text("SELECT id FROM clients WHERE full_name = 'E2E Клиент с User'")
        )
        client_id = client_result.scalar()
        
        # 2. Создаем услугу
        await tenant_session.execute(
            text("""
                INSERT INTO services (name, price, duration, created_at, updated_at)
                VALUES ('E2E Услуга 2', 2000, 90, NOW(), NOW())
                RETURNING id
            """)
        )
        service_result = await tenant_session.execute(
            text("SELECT id FROM services WHERE name = 'E2E Услуга 2'")
        )
        service_id = service_result.scalar()
        
        # 3. Создаем мастера
        await tenant_session.execute(
            text("""
                INSERT INTO masters (full_name, phone, is_active, created_at, updated_at)
                VALUES ('E2E Мастер 2', '+79995555555', true, NOW(), NOW())
                RETURNING id
            """)
        )
        master_result = await tenant_session.execute(
            text("SELECT id FROM masters WHERE full_name = 'E2E Мастер 2'")
        )
        master_id = master_result.scalar()
        
        # 4. Создаем запись
        await tenant_session.execute(
            text("""
                INSERT INTO bookings (client_id, service_id, master_id, date, time, status, created_at, updated_at)
                VALUES (:client_id, :service_id, :master_id, CURRENT_DATE, '11:00', 'new', NOW(), NOW())
                RETURNING id
            """),
            {
                "client_id": client_id,
                "service_id": service_id,
                "master_id": master_id,
            }
        )
        booking_result = await tenant_session.execute(
            text("SELECT id FROM bookings WHERE time = '11:00'")
        )
        booking_id = booking_result.scalar()
        
        await tenant_session.commit()
        
        # 5. Обновляем статус записи
        update_data = BookingUpdateRequest(
            status="confirmed",
        )
        
        # Мокаем уведомления
        with patch('app.api.bookings.send_booking_status_notification', new_callable=AsyncMock) as mock_notify:
            mock_notify.return_value = True
            
            updated_booking = await update_booking(
                request=mock_request,
                booking_id=booking_id,
                booking_data=update_data,
                tenant_session=tenant_session,
                current_user=mock_user,
            )
            
            assert updated_booking.id == booking_id
            assert updated_booking.status == "confirmed"
            
            # Проверяем, что уведомление было вызвано
            mock_notify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_bookings_list(self, tenant_session: AsyncSession, mock_user, mock_request):
        """Тест получения списка записей."""
        mock_request.state.company_id = 99999
        
        # Создаем несколько записей
        for i in range(3):
            # Создаем клиента
            await tenant_session.execute(
                text(f"""
                    INSERT INTO clients (full_name, phone, created_at, updated_at)
                    VALUES ('Клиент {i}', '+7999{i}{i}{i}{i}{i}{i}{i}', NOW(), NOW())
                    RETURNING id
                """)
            )
            client_result = await tenant_session.execute(
                text(f"SELECT id FROM clients WHERE full_name = 'Клиент {i}'")
            )
            client_id = client_result.scalar()
            
            # Создаем услугу
            await tenant_session.execute(
                text(f"""
                    INSERT INTO services (name, price, duration, created_at, updated_at)
                    VALUES ('Услуга {i}', {1000 + i * 100}, 60, NOW(), NOW())
                    RETURNING id
                """)
            )
            service_result = await tenant_session.execute(
                text(f"SELECT id FROM services WHERE name = 'Услуга {i}'")
            )
            service_id = service_result.scalar()
            
            # Создаем мастера
            await tenant_session.execute(
                text(f"""
                    INSERT INTO masters (full_name, phone, is_active, created_at, updated_at)
                    VALUES ('Мастер {i}', '+7998{i}{i}{i}{i}{i}{i}{i}', true, NOW(), NOW())
                    RETURNING id
                """)
            )
            master_result = await tenant_session.execute(
                text(f"SELECT id FROM masters WHERE full_name = 'Мастер {i}'")
            )
            master_id = master_result.scalar()
            
            # Создаем запись
            await tenant_session.execute(
                text(f"""
                    INSERT INTO bookings (client_id, service_id, master_id, date, time, status, created_at, updated_at)
                    VALUES (:client_id, :service_id, :master_id, CURRENT_DATE, '{10 + i}:00', 'new', NOW(), NOW())
                """),
                {
                    "client_id": client_id,
                    "service_id": service_id,
                    "master_id": master_id,
                }
            )
        
        await tenant_session.commit()
        
        # Получаем список записей
        result = await get_bookings(
            request=mock_request,
            page=1,
            page_size=10,
            tenant_session=tenant_session,
            current_user=mock_user,
        )
        
        assert result.total >= 3
        assert len(result.items) >= 3
