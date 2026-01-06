"""
API для работы с услугами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

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
from app.schemas.service import (
    ServiceResponse, ServiceListResponse,
    ServiceCreateRequest, ServiceUpdateRequest
)
from shared.database.models import User, Service, Booking
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=ServiceListResponse)
async def get_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список услуг.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска
        is_active: фильтр по активности
        company_id: ID компании для мульти-тенантности
    """
    # Получаем tenant сессию для компании (если указана)
    tenant_session = None
    if company_id:
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            break
    else:
        # Для публичного API используем обычную сессию
        # Для публичных API company_id может быть None
        # В будущем здесь будет проверка JWT токена
        tenant_session = db
    
    query = select(Service)
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.where(Service.name.ilike(search_term))
    
    if is_active is not None:
        query = query.where(Service.is_active == is_active)
    
    # Подсчет общего количества (с учетом фильтров)
    count_query = select(func.count(Service.id)).select_from(query)
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Service.name)
    
    result = await tenant_session.execute(query)
    services = result.scalars().all()
    
    # Формируем ответы
    items = []
    for service in services:
        items.append(ServiceResponse.model_validate(service))
    
    print(f"📊 Запрос услуг: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию об услуге.
    
    Аргументы:
        service_id: ID услуги
        company_id: ID компании для мульти-тенантности
    """
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
    
    query = select(Service).where(Service.id == service_id)
    result = await tenant_session.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    # Формируем ответ
    service_dict = {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "price": float(service.price),
        "duration": service.duration,
        "is_active": service.is_active,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        "company_id": company_id,
    }
    
    # Проверяем, связаны ли услуги с записями
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.service_id == service_id)
    )
    service_dict["booking_count"] = booking_count or 0
    
    return ServiceResponse.model_validate(service_dict)


@router.post("", response_model=ServiceResponse, status_code=201)
async def create_service(
    service_data: ServiceCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать новую услугу.
    
    Аргументы:
        service_data: данные услуги
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать услуги")
    
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
    
    # Проверяем, существует ли услуга с таким названием
    existing_service = await tenant_session.execute(
        select(Service).where(Service.name == service_data.name)
    ).scalar_one_or_none()
    
    if existing_service:
        raise HTTPException(
            status_code=400,
            detail=f"Услуга с названием '{service_data.name}' уже существует"
        )
    
    # Создаем новую услугу
    service = Service(
        name=service_data.name,
        description=service_data.description,
        price=float(service_data.price),
        duration=service_data.duration,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(service)
    await tenant_session.commit()
    await tenant_session.refresh(service)
    
    print(f"✅ Создана услуга: name={service_data.name}, price={service_data.price}, duration={service_data.duration}")
    
    # Отправляем уведомление
    # TODO: Создать Celery задачу для уведомления о новой услуге
    
    # Формируем ответ
    service_dict = {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "price": float(service.price),
        "duration": service.duration,
        "is_active": service.is_active,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        "company_id": company_id,
    }
    
    return ServiceResponse.model_validate(service_dict)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию об услуге.
    
    Аргументы:
        service_id: ID услуги
        service_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять услуги")
    
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
    
    # Проверяем существование услуги
    query = select(Service).where(Service.id == service_id)
    result = await tenant_session.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    # Проверяем, используется ли услуга в записях
    # TODO: Добавить проверку на Bookings перед обновлением
    
    # Обновляем поля
    update_data = {}
    if service_data.name is not None:
        update_data["name"] = service_data.name
    if service_data.description is not None:
        update_data["description"] = service_data.description
    if service_data.price is not None:
        update_data["price"] = float(service_data.price)
    if service_data.duration is not None:
        update_data["duration"] = service_data.duration
    if service_data.is_active is not None:
        update_data["is_active"] = service_data.is_active
    
    service.updated_at = datetime.utcnow()
    update_data["updated_at"] = service.updated_at
    
    # Выполняем обновление
    await tenant_session.execute(
        select(Service).where(Service.id == service_id).values(**update_data)
    )
    await tenant_session.commit()
    await tenant_session.refresh(service)
    
    print(f"✅ Обновлена услуга: service_id={service_id}, name={service_data.name if service_data.name else service.name}")
    
    # Формируем ответ
    service_dict = {
        "id": service.id,
        "name": service.name,
        "description": service.description,
        "price": float(service.price),
        "duration": service.duration,
        "is_active": service.is_active,
        "created_at": service.created_at,
        "updated_at": service.updated_at,
        "company_id": company_id,
    }
    
    return ServiceResponse.model_validate(service_dict)


@router.delete("/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить услугу.
    
    Аргументы:
        service_id: ID услуги
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять услуги")
    
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
    
    # Проверяем существование услуги
    query = select(Service).where(Service.id == service_id)
    result = await tenant_session.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    # Проверяем, используется ли услуга в записях
    # TODO: Добавить проверку на Bookings перед удалением
    
    # Если есть записи, не даем удалить
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.service_id == service_id)
    )
    
    if booking_count and booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить услугу '{service.name}', так как с ней связаны {booking_count} записей"
        )
    
    # Удаляем услугу
    await tenant_session.execute(
        delete(Service).where(Service.id == service_id)
    )
    await tenant_session.commit()
    
    print(f"✅ Удалена услуга: service_id={service_id}, name={service.name}")
    
    return None

