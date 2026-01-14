"""
API для работы с клиентами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime
from typing import Optional, Annotated
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, delete
from sqlalchemy.orm import selectinload
from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.client import (
    ClientResponse, ClientListResponse,
    ClientCreateRequest, ClientUpdateRequest
)
from shared.database.models import User, Client, Booking
from app.services.tenant_service import get_tenant_service
from app.config import settings

router = APIRouter(prefix="/api/clients", tags=["clients"])
security = HTTPBearer()


async def get_company_id_from_token(request: Request) -> Optional[int]:
    """Получить company_id из JWT токена"""
    try:
        # Извлекаем токен напрямую из заголовков
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return None
        
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        company_id = payload.get("company_id")
        if company_id:
            return int(company_id)
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Не удалось получить company_id из токена: {e}")
        return None


@router.get("", response_model=ClientListResponse)
async def get_clients(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
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
    
    # Получаем company_id из токена, если не передан в query параметрах
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Получение клиентов: company_id={company_id}, page={page}, page_size={page_size}, user_id={current_user.id}")
    
    if not company_id:
        logger.error("company_id не найден в токене и не передан в query параметрах")
        raise HTTPException(status_code=400, detail="company_id не найден. Необходимо указать company_id в query параметрах или войти как пользователь компании.")
    
    # Устанавливаем search_path для tenant схемы
    schema_name = f"tenant_{company_id}"
    
    # Проверяем существование схемы ПЕРЕД установкой search_path
    try:
        schema_check = await db.execute(
            text(f'SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema_name)'),
            {"schema_name": schema_name}
        )
        schema_exists = schema_check.scalar()
        if not schema_exists:
            logger.error(f"Схема {schema_name} не существует")
            raise HTTPException(status_code=404, detail=f"Схема для компании {company_id} не найдена")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при проверке схемы {schema_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке схемы: {str(e)}")
    
    # Устанавливаем search_path для tenant схемы
    try:
        await db.execute(text(f'SET search_path TO "{schema_name}", public'))
        logger.info(f"✅ Установлен search_path для {schema_name}")
    except Exception as e:
        logger.error(f"Ошибка при установке search_path для {schema_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при установке search_path: {str(e)}")
    
    tenant_session = db
    
    # Фильтры - используем text() для работы с полями, которых может не быть в модели
    search_filter = ""
    search_params = {}
    if search:
        search_term = f"%{search}%"
        search_filter = f"""
            WHERE c.full_name ILIKE :search
               OR c.phone ILIKE :search
               OR EXISTS (
                   SELECT 1 FROM "{schema_name}".users u 
                   WHERE u.id = c.user_id 
                   AND (u.phone ILIKE :search OR u.full_name ILIKE :search OR CAST(u.telegram_id AS TEXT) ILIKE :search)
               )
        """
        search_params["search"] = search_term
    
    # Подсчет общего количества
    count_query_str = f'SELECT COUNT(*) FROM "{schema_name}".clients c {search_filter}'
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
        clients_query_str = f"""
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
            FROM "{schema_name}".clients c
            {search_filter}
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
    
    print(f"📊 Запрос клиентов: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for client in clients:
        try:
            # Считаем количество записей для клиента через прямой SQL
            booking_count_query = text(f'SELECT COUNT(*) FROM "{schema_name}".bookings WHERE client_id = :client_id')
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
            "user_is_admin": None,
        }
        
        # Преобразуем total_amount в float, если это Decimal
        if isinstance(client_dict["total_amount"], Decimal):
            client_dict["total_amount"] = float(client_dict["total_amount"])
        
        # Загружаем данные пользователя отдельно, если user_id есть и не NULL
        if client_user_id and client_user_id > 0:
            try:
                user_result = await tenant_session.execute(
                    text(f'SELECT telegram_id, full_name, role, is_admin FROM "{schema_name}".users WHERE id = :user_id'),
                    {"user_id": client.user_id}
                )
                user_row = user_result.fetchone()
                if user_row:
                    client_dict["user_telegram_id"] = user_row[0]
                    user_full_name = user_row[1] or ''
                    name_parts = user_full_name.split(maxsplit=1) if user_full_name else ['', '']
                    client_dict["user_first_name"] = name_parts[0] if len(name_parts) > 0 else None
                    client_dict["user_last_name"] = name_parts[1] if len(name_parts) > 1 else None
                    client_dict["user_is_admin"] = (user_row[3] if user_row[3] is not None else False) or (user_row[2] == 'admin' if user_row[2] else False)
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
    request: Request,
    client_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
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
    
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    schema_name = f"tenant_{company_id}"
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "{schema_name}", public'))
    tenant_session = db
    
    query = select(Client).where(Client.id == client_id)
    
    result = await tenant_session.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    print(f"🔍 Запрос клиента: client_id={client_id}, company_id={company_id}")
    
    # Считаем количество записей для клиента
    booking_count_result = await tenant_session.execute(
        text(f'SELECT COUNT(*) FROM "{schema_name}".bookings WHERE client_id = :client_id'),
        {"client_id": client.id}
    )
    booking_count = booking_count_result.scalar() or 0
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "email": getattr(client, 'email', None),  # Может отсутствовать в tenant схеме
        "car_brand": getattr(client, 'car_brand', None),  # Может отсутствовать в tenant схеме
        "car_model": getattr(client, 'car_model', None),  # Может отсутствовать в tenant схеме
        "car_number": getattr(client, 'car_number', None),  # Может отсутствовать в tenant схеме
        "telegram_id": None,
        "first_name": None,
        "last_name": None,
        "booking_count": booking_count or 0,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
        "company_id": company_id,
    }
    
    # Добавляем данные пользователя, если есть
    if client.user:
        client_dict["telegram_id"] = getattr(client.user, 'telegram_id', None)
        # Получаем full_name из user и разбиваем на first_name и last_name
        user_full_name = getattr(client.user, 'full_name', None) or ''
        name_parts = user_full_name.split(maxsplit=1) if user_full_name else ['', '']
        client_dict["first_name"] = name_parts[0] if len(name_parts) > 0 else None
        client_dict["last_name"] = name_parts[1] if len(name_parts) > 1 else None
    
    return ClientResponse.model_validate(client_dict)


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    request: Request,
    client_data: ClientCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
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
    
    # Получаем company_id из токена, если не передан в query параметрах
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клиента: company_id={company_id}, user_id={current_user.id}, client_name={client_data.full_name}")
    
    if not company_id:
        logger.error("company_id не найден в токене и не передан в query параметрах")
        raise HTTPException(status_code=400, detail="company_id не найден. Необходимо указать company_id в query параметрах или войти как пользователь компании.")
    
    # Устанавливаем search_path для tenant схемы
    schema_name = f"tenant_{company_id}"
    await db.execute(text(f'SET search_path TO "{schema_name}", public'))
    # Устанавливаем search_path для текущей транзакции
    await db.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    tenant_session = db
    
    # Создаем нового клиента
    client = Client(
        full_name=client_data.full_name,
        phone=client_data.phone,
        car_brand=client_data.car_brand,
        car_model=client_data.car_model,
        car_number=client_data.car_number,
        user_id=None,  # Будет заполнен позже при регистрации через бота
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(client)
    await tenant_session.commit()
    await tenant_session.refresh(client)
    
    print(f"✅ Создан клиент: name={client_data.full_name}, phone={client_data.phone}, company_id={company_id}")
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "user_id": client.user_id or 0,  # Если user_id None, используем 0
        "full_name": client.full_name,
        "phone": client.phone,
        "car_brand": getattr(client, 'car_brand', None),  # Может отсутствовать в tenant схеме
        "car_model": getattr(client, 'car_model', None),  # Может отсутствовать в tenant схеме
        "car_number": getattr(client, 'car_number', None),  # Может отсутствовать в tenant схеме
        "total_visits": 0,
        "total_amount": None,
        "created_at": client.created_at,
        "user_telegram_id": None,
        "user_first_name": None,
        "user_last_name": None,
        "user_is_admin": None,
    }
    
    return ClientResponse.model_validate(client_dict)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    request: Request,
    client_id: int,
    client_data: ClientUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
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
    
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    schema_name = f"tenant_{company_id}"
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "{schema_name}", public'))
    tenant_session = db
    
    # Проверяем существование клиента
    query = select(Client).where(Client.id == client_id)
    result = await tenant_session.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Обновляем поля
    if client_data.full_name is not None:
        client.full_name = client_data.full_name
    if client_data.phone is not None:
        client.phone = client_data.phone
    if hasattr(client_data, 'email') and client_data.email is not None:
        setattr(client, 'email', client_data.email)
    if client_data.car_brand is not None:
        setattr(client, 'car_brand', client_data.car_brand)
    if client_data.car_model is not None:
        setattr(client, 'car_model', client_data.car_model)
    if client_data.car_number is not None:
        setattr(client, 'car_number', client_data.car_number)
    
    client.updated_at = datetime.utcnow()
    
    await tenant_session.commit()
    await tenant_session.refresh(client)
    
    print(f"✅ Обновлен клиент: client_id={client_id}, name={client_data.full_name if client_data.full_name else client.full_name}")
    
    # Считаем количество записей
    booking_count_result = await tenant_session.execute(
        text(f'SELECT COUNT(*) FROM "{schema_name}".bookings WHERE client_id = :client_id'),
        {"client_id": client.id}
    )
    booking_count = booking_count_result.scalar() or 0
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "email": getattr(client, 'email', None),  # Может отсутствовать в tenant схеме
        "car_brand": getattr(client, 'car_brand', None),  # Может отсутствовать в tenant схеме
        "car_model": getattr(client, 'car_model', None),  # Может отсутствовать в tenant схеме
        "car_number": getattr(client, 'car_number', None),  # Может отсутствовать в tenant схеме
        "telegram_id": None,
        "first_name": None,
        "last_name": None,
        "booking_count": booking_count or 0,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
        "company_id": company_id,
    }
    
    # Добавляем данные пользователя, если есть
    if client.user:
        client_dict["telegram_id"] = getattr(client.user, 'telegram_id', None)
        # Получаем full_name из user и разбиваем на first_name и last_name
        user_full_name = getattr(client.user, 'full_name', None) or ''
        name_parts = user_full_name.split(maxsplit=1) if user_full_name else ['', '']
        client_dict["first_name"] = name_parts[0] if len(name_parts) > 0 else None
        client_dict["last_name"] = name_parts[1] if len(name_parts) > 1 else None
    
    return ClientResponse.model_validate(client_dict)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    request: Request,
    client_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
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
    
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    schema_name = f"tenant_{company_id}"
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "{schema_name}", public'))
    tenant_session = db
    
    # Проверяем существование клиента
    query = select(Client).where(Client.id == client_id)
    result = await tenant_session.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Проверяем, используется ли клиент в записях
    booking_count_result = await tenant_session.execute(
        text(f'SELECT COUNT(*) FROM "{schema_name}".bookings WHERE client_id = :client_id'),
        {"client_id": client.id}
    )
    booking_count = booking_count_result.scalar() or 0
    
    if booking_count and booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить клиента '{client.full_name}', так как с ним связаны {booking_count} записей"
        )
    
    # Удаляем клиента
    await tenant_session.execute(
        delete(Client).where(Client.id == client_id)
    )
    await tenant_session.commit()
    
    print(f"✅ Удален клиент: client_id={client_id}, name={client.full_name}")
    
    return None

