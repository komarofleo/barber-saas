"""
API для работы с клиентами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.client import (
    ClientResponse, ClientListResponse,
    ClientCreateRequest, ClientUpdateRequest
)
from shared.database.models import User, Client, Booking
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
async def get_clients(
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
    
    # Получаем tenant сессию для компании (если указана)
    tenant_session = None
    if company_id:
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            break
    else:
        # Для публичного API используем обычную сессию
        tenant_session = db
    
    query = select(Client).options(
        selectinload(Client.user)
    )
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.join(User).where(
            or_(
                Client.full_name.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                Client.phone.ilike(search_term),
                User.phone.ilike(search_term),
                User.telegram_id.ilike(search_term),
                Client.email.ilike(search_term),
            )
        )
    
    # Подсчет общего количества
    count_query = select(func.count(Client.id))
    if search:
        # При поиске тоже нужен join
        count_query = count_query.select_from(Client).join(User)
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Client.full_name)
    
    result = await tenant_session.execute(query)
    clients = result.scalars().all()
    
    print(f"📊 Запрос клиентов: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for client in clients:
        # Считаем количество записей для клиента
        booking_count = await tenant_session.scalar(
            select(func.count(Booking.id)).select_from(Booking).where(Booking.client_id == client.id)
        )
        
        client_dict = {
            "id": client.id,
            "full_name": client.full_name,
            "phone": client.phone,
            "email": client.email,
            "car_brand": client.car_brand,
            "car_model": client.car_model,
            "car_number": client.car_number,
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
            client_dict["telegram_id"] = client.user.telegram_id
            client_dict["first_name"] = client.user.first_name
            client_dict["last_name"] = client.user.last_name
        
        items.append(ClientResponse.model_validate(client_dict))
    
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
    
    # Получаем tenant сессию для компании (если указана)
    tenant_session = None
    if company_id:
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            break
    else:
        # Для публичного API используем обычную сессию
        tenant_session = db
    
    query = select(Client).options(
        selectinload(Client.user)
    ).where(Client.id == client_id)
    
    result = await tenant_session.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    print(f"🔍 Запрос клиента: client_id={client_id}, company_id={company_id}")
    
    # Считаем количество записей для клиента
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.client_id == client.id)
    )
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "email": client.email,
        "car_brand": client.car_brand,
        "car_model": client.car_model,
        "car_number": client.car_number,
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
        client_dict["telegram_id"] = client.user.telegram_id
        client_dict["first_name"] = client.user.first_name
        client_dict["last_name"] = client.user.last_name
    
    return ClientResponse.model_validate(client_dict)


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
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
    
    # Получаем tenant сессию для компании (если указана)
    tenant_session = None
    if company_id:
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            break
    else:
        # Для публичного API используем обычную сессию
        tenant_session = db
    
    # Создаем нового клиента
    client = Client(
        full_name=client_data.full_name,
        phone=client_data.phone,
        email=client_data.email,
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
    
    print(f"✅ Создан клиент: name={client_data.full_name}, phone={client_data.phone}")
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "email": client.email,
        "car_brand": client.car_brand,
        "car_model": client.car_model,
        "car_number": client.car_number,
        "telegram_id": None,
        "first_name": None,
        "last_name": None,
        "booking_count": 0,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
        "company_id": company_id,
    }
    
    return ClientResponse.model_validate(client_dict)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
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
    
    # Получаем tenant сессию для компании (если указана)
    tenant_session = None
    if company_id:
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            break
    else:
        # Для публичного API используем обычную сессию
        tenant_session = db
    
    # Проверяем существование клиента
    query = select(Client).where(Client.id == client_id)
    result = await tenant_session.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Обновляем поля
    update_data = {}
    if client_data.full_name is not None:
        update_data["full_name"] = client_data.full_name
    if client_data.phone is not None:
        update_data["phone"] = client_data.phone
    if client_data.email is not None:
        update_data["email"] = client_data.email
    if client_data.car_brand is not None:
        update_data["car_brand"] = client_data.car_brand
    if client_data.car_model is not None:
        update_data["car_model"] = client_data.car_model
    if client_data.car_number is not None:
        update_data["car_number"] = client_data.car_number
    
    client.updated_at = datetime.utcnow()
    update_data["updated_at"] = client.updated_at
    
    # Выполняем обновление
    await tenant_session.execute(
        select(Client).where(Client.id == client_id).values(**update_data)
    )
    await tenant_session.commit()
    await tenant_session.refresh(client)
    
    print(f"✅ Обновлен клиент: client_id={client_id}, name={client_data.full_name if client_data.full_name else client.full_name}")
    
    # Считаем количество записей
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.client_id == client.id)
    )
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "full_name": client.full_name,
        "phone": client.phone,
        "email": client.email,
        "car_brand": client.car_brand,
        "car_model": client.car_model,
        "car_number": client.car_number,
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
        client_dict["telegram_id"] = client.user.telegram_id
        client_dict["first_name"] = client.user.first_name
        client_dict["last_name"] = client.user.last_name
    
    return ClientResponse.model_validate(client_dict)


@router.delete("/{client_id}", status_code=204)
async def delete_client(
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
    
    # Получаем tenant сессию для компании (если указана)
    tenant_session = None
    if company_id:
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            break
    else:
        # Для публичного API используем обычную сессию
        tenant_session = db
    
    # Проверяем существование клиента
    query = select(Client).where(Client.id == client_id)
    result = await tenant_session.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Проверяем, используется ли клиент в записях
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.client_id == client.id)
    )
    
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

