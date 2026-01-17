"""
API для работы с клиентами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime
import logging
from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.auth import get_current_user
from app.deps.tenant import get_tenant_db
from app.schemas.client import (
    ClientResponse, ClientListResponse,
    ClientCreateRequest, ClientUpdateRequest
)
from shared.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
async def get_clients(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список клиентов.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска (по ФИО, телефону, telegram_id, email)
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать клиентов")
    
    import logging
    logger = logging.getLogger(__name__)
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"Получение клиентов: company_id={company_id}, page={page}, page_size={page_size}, user_id={current_user.id}")
    
    # Фильтры - используем text() для работы с полями, которых может не быть в модели
    search_filter = ""
    search_params = {}
    if search:
        search_term = f"%{search}%"
        search_filter = """
            WHERE c.full_name ILIKE :search
               OR c.phone ILIKE :search
               OR EXISTS (
                   SELECT 1 FROM users u 
                   WHERE u.id = c.user_id 
                   AND (u.phone ILIKE :search OR u.full_name ILIKE :search OR CAST(u.telegram_id AS TEXT) ILIKE :search)
               )
        """
        search_params["search"] = search_term
    
    # Подсчет общего количества
    count_query_str = f"SELECT COUNT(*) FROM clients c {search_filter}"
    count_query = text(count_query_str)
    count_params = search_params.copy()
    count_result = await tenant_session.execute(count_query, count_params)
    total = count_result.scalar() or 0
    
    if total == 0:
        # Если ничего не найдено, возвращаем пустой результат
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size
        }
    
    # Получаем клиентов через прямой SQL запрос, чтобы гарантировать работу с tenant схемой
    try:
        # Формируем SQL запрос с пагинацией и фильтрацией
        offset = (page - 1) * page_size
        clients_query_str = """
            SELECT c.id, 
                   c.user_id, 
                   c.full_name, 
                   c.phone, 
                   NULL as car_brand,
                   NULL as car_model,
                   NULL as car_number,
                   0 as total_visits, 
                   0 as total_amount, 
                   c.created_at, 
                   COALESCE(c.updated_at, c.created_at) as updated_at
            FROM clients c
            """ + search_filter + """
            ORDER BY c.full_name
            LIMIT :limit OFFSET :offset
        """
        
        query_params = {"limit": page_size, "offset": offset, **search_params}
        clients_query = text(clients_query_str)
        
        clients_result = await tenant_session.execute(clients_query, query_params)
        
        # Преобразуем результаты в объекты Client
        clients = []
        for row in clients_result.fetchall():
            # Создаем временный объект Client из данных строки
            client = type('Client', (), {})()
            client.id = row[0]
            client.user_id = row[1] if row[1] is not None else None  # Может быть NULL
            client.full_name = row[2]
            client.phone = row[3] if row[3] else None
            client.car_brand = row[4] if row[4] and row[4].strip() else None
            client.car_model = row[5] if row[5] and row[5].strip() else None
            client.car_number = row[6] if row[6] and row[6].strip() else None
            client.total_visits = row[7] or 0
            client.total_amount = row[8] if row[8] is not None else Decimal('0.00')
            client.created_at = row[9]
            client.updated_at = row[10] if len(row) > 10 and row[10] else row[9]  # Если updated_at нет, используем created_at
            client.user = None  # Загрузим отдельно, если нужно
            clients.append(client)
        
        logger.info(f"✅ Получено клиентов через SQL: {len(clients)}")
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении SQL запроса клиентов: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении клиентов: {str(e)}")
    
    logger.info(f"📊 Запрос клиентов: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for client in clients:
        try:
            # Считаем количество записей для клиента через прямой SQL
            booking_count_query = text('SELECT COUNT(*) FROM bookings WHERE client_id = :client_id')
            booking_count_result = await tenant_session.execute(booking_count_query, {"client_id": client.id})
            booking_count = booking_count_result.scalar() or 0
        except Exception as e:
            logger.warning(f"Ошибка при подсчете записей для клиента {client.id}: {e}")
            booking_count = 0
        
        # Проверяем обязательные поля
        if not hasattr(client, 'id') or client.id is None:
            logger.warning(f"Клиент без ID пропущен")
            continue
        
        if not hasattr(client, 'full_name') or not client.full_name:
            logger.warning(f"Клиент {client.id} без full_name пропущен")
            continue
        
        if not hasattr(client, 'created_at') or client.created_at is None:
            logger.warning(f"Клиент {client.id} без created_at, используем текущую дату")
            created_at = datetime.utcnow()
        else:
            created_at = client.created_at
        
        # Обрабатываем user_id - может быть NULL в базе
        client_user_id = getattr(client, 'user_id', None)
        if client_user_id is None:
            client_user_id = 0
        
        client_dict = {
            "id": client.id,
            "user_id": client_user_id,  # Если user_id None, используем 0
            "full_name": client.full_name,
            "phone": getattr(client, 'phone', None),
            "car_brand": getattr(client, 'car_brand', None),  # Может отсутствовать в tenant схеме
            "car_model": getattr(client, 'car_model', None),  # Может отсутствовать в tenant схеме
            "car_number": getattr(client, 'car_number', None),  # Может отсутствовать в tenant схеме
            "total_visits": booking_count or 0,
            "total_amount": getattr(client, 'total_amount', None),  # Может быть Decimal
            "created_at": created_at,
            "user_telegram_id": None,
            "user_first_name": None,
            "user_last_name": None,
        }
        
        # Преобразуем total_amount в float, если это Decimal
        if isinstance(client_dict["total_amount"], Decimal):
            client_dict["total_amount"] = float(client_dict["total_amount"])
        
        # Загружаем данные пользователя отдельно, если user_id есть и не NULL
        if client_user_id and client_user_id > 0:
            try:
                user_result = await tenant_session.execute(
                    text("SELECT telegram_id, full_name, role FROM users WHERE id = :user_id"),
                    {"user_id": client.user_id}
                )
                user_row = user_result.fetchone()
                if user_row:
                    client_dict["user_telegram_id"] = user_row[0]
                    user_full_name = user_row[1] or ''
                    name_parts = user_full_name.split(maxsplit=1) if user_full_name else ['', '']
                    client_dict["user_first_name"] = name_parts[0] if len(name_parts) > 0 else None
                    client_dict["user_last_name"] = name_parts[1] if len(name_parts) > 1 else None
            except Exception as e:
                logger.warning(f"Ошибка при получении данных пользователя для клиента {client.id}: {e}")
        
        try:
            items.append(ClientResponse.model_validate(client_dict))
        except Exception as e:
            logger.error(f"Ошибка при валидации клиента {client.id}: {e}, данные: {client_dict}", exc_info=True)
            # Пропускаем проблемного клиента, но продолжаем обработку остальных
            continue
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о клиенте.
    
    Аргументы:
        client_id: ID клиента
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать клиентов")

    client_result = await tenant_session.execute(
        text(
            """
            SELECT id, user_id, full_name, phone, created_at, COALESCE(updated_at, created_at) AS updated_at
            FROM clients
            WHERE id = :client_id
            """
        ),
        {"client_id": client_id},
    )
    row = client_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    client_id_db, user_id, full_name, phone, created_at, updated_at = row

    booking_count_result = await tenant_session.execute(
        text("SELECT COUNT(*) FROM bookings WHERE client_id = :client_id"),
        {"client_id": client_id_db},
    )
    booking_count = booking_count_result.scalar() or 0

    user_telegram_id = None
    user_first_name = None
    user_last_name = None
    if user_id:
        user_result = await tenant_session.execute(
            text("SELECT telegram_id, full_name, role FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )
        user_row = user_result.fetchone()
        if user_row:
            user_telegram_id = user_row[0]
            user_full_name = user_row[1] or ""
            parts = user_full_name.split(maxsplit=1) if user_full_name else ["", ""]
            user_first_name = parts[0] if len(parts) > 0 else None
            user_last_name = parts[1] if len(parts) > 1 else None

    company_id = getattr(request.state, "company_id", None)
    logger.info(f"🔍 Запрос клиента: client_id={client_id}, company_id={company_id}")

    return ClientResponse.model_validate(
        {
            "id": client_id_db,
            "user_id": int(user_id or 0),
            "full_name": full_name,
            "phone": phone,
            "car_brand": None,
            "car_model": None,
            "car_year": None,
            "car_number": None,
            "total_visits": int(booking_count or 0),
            "total_amount": None,
            "created_at": created_at,
            "user_telegram_id": user_telegram_id,
            "user_first_name": user_first_name,
            "user_last_name": user_last_name,
        }
    )


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    request: Request,
    client_data: ClientCreateRequest,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать нового клиента.
    
    Аргументы:
        client_data: данные клиента
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать клиентов")

    import logging
    logger = logging.getLogger(__name__)
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"Создание клиента: company_id={company_id}, user_id={current_user.id}, client_name={client_data.full_name}")

    now = datetime.utcnow()
    insert_result = await tenant_session.execute(
        text(
            """
            INSERT INTO clients (full_name, phone, created_at, updated_at)
            VALUES (:full_name, :phone, :created_at, :updated_at)
            RETURNING id
            """
        ),
        {"full_name": client_data.full_name, "phone": client_data.phone, "created_at": now, "updated_at": now},
    )
    await tenant_session.commit()
    new_id = insert_result.scalar_one()

    logger.info(f"✅ Создан клиент: id={new_id}, company_id={company_id}")

    return ClientResponse.model_validate(
        {
            "id": new_id,
            "user_id": 0,
            "full_name": client_data.full_name,
            "phone": client_data.phone,
            "car_brand": None,
            "car_model": None,
            "car_year": None,
            "car_number": None,
            "total_visits": 0,
            "total_amount": None,
            "created_at": now,
            "user_telegram_id": None,
            "user_first_name": None,
            "user_last_name": None,
        }
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    request: Request,
    client_id: int,
    client_data: ClientUpdateRequest,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию о клиенте.
    
    Аргументы:
        client_id: ID клиента
        client_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять клиентов")

    exists = await tenant_session.execute(text("SELECT 1 FROM clients WHERE id = :id"), {"id": client_id})
    if not exists.fetchone():
        raise HTTPException(status_code=404, detail="Клиент не найден")

    update_fields: dict[str, object] = {}
    if client_data.full_name is not None:
        update_fields["full_name"] = client_data.full_name
    if client_data.phone is not None:
        update_fields["phone"] = client_data.phone
    update_fields["updated_at"] = datetime.utcnow()

    set_parts = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    await tenant_session.execute(
        text(f"UPDATE clients SET {set_parts} WHERE id = :id"),
        {"id": client_id, **update_fields},
    )
    await tenant_session.commit()

    # Актуальные данные
    client_result = await tenant_session.execute(
        text(
            """
            SELECT id, user_id, full_name, phone, created_at, COALESCE(updated_at, created_at) AS updated_at
            FROM clients
            WHERE id = :client_id
            """
        ),
        {"client_id": client_id},
    )
    row = client_result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    client_id_db, user_id, full_name, phone, created_at, updated_at = row

    booking_count_result = await tenant_session.execute(
        text("SELECT COUNT(*) FROM bookings WHERE client_id = :client_id"),
        {"client_id": client_id_db},
    )
    booking_count = booking_count_result.scalar() or 0

    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Обновлен клиент: client_id={client_id}, company_id={company_id}")

    return ClientResponse.model_validate(
        {
            "id": client_id_db,
            "user_id": int(user_id or 0),
            "full_name": full_name,
            "phone": phone,
            "car_brand": None,
            "car_model": None,
            "car_year": None,
            "car_number": None,
            "total_visits": int(booking_count or 0),
            "total_amount": None,
            "created_at": created_at,
            "user_telegram_id": None,
            "user_first_name": None,
            "user_last_name": None,
        }
    )


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    request: Request,
    client_id: int,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить клиента.
    
    Аргументы:
        client_id: ID клиента
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять клиентов")

    exists = await tenant_session.execute(
        text("SELECT full_name FROM clients WHERE id = :id"),
        {"id": client_id},
    )
    row = exists.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    client_name = row[0]

    booking_count_result = await tenant_session.execute(
        text("SELECT COUNT(*) FROM bookings WHERE client_id = :client_id"),
        {"client_id": client_id},
    )
    booking_count = booking_count_result.scalar() or 0

    if booking_count and booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить клиента '{client_name}', так как с ним связаны {booking_count} записей",
        )

    await tenant_session.execute(text("DELETE FROM clients WHERE id = :id"), {"id": client_id})
    await tenant_session.commit()

    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Удален клиент: client_id={client_id}, company_id={company_id}")

    return None

