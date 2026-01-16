"""
API для работы с услугами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime
import logging
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.deps.tenant import get_tenant_db
from app.schemas.service import (
    ServiceResponse, ServiceListResponse,
    ServiceCreateRequest, ServiceUpdateRequest
)
from shared.database.models import User, Service, Booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=ServiceListResponse)
async def get_services(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список услуг.

    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска
        is_active: фильтр по активности
    """
    query = select(Service)
    
    # Фильтры
    if search:
        search_term = f"%{search}%"
        query = query.where(Service.name.ilike(search_term))
    
    if is_active is not None:
        query = query.where(Service.is_active == is_active)
    
    # Подсчет общего количества
    count_query = select(func.count(Service.id)).select_from(query)
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Service.name)
    
    result = await tenant_session.execute(query)
    services = result.scalars().all()
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"📊 Запрос услуг: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for service in services:
        service_dict = {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "price": service.price,
            "duration": service.duration,
            "is_active": service.is_active,
            "created_at": service.created_at,
        }
        items.append(ServiceResponse.model_validate(service_dict))
    
    return ServiceListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить услугу по ID.
    
    Аргументы:
        service_id: ID услуги
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать услуги")
    
    result = await tenant_session.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"🔍 Запрос услуги: service_id={service_id}, company_id={company_id}")
    
    return ServiceResponse.model_validate(service)


@router.post("", response_model=ServiceResponse, status_code=201)
async def create_service(
    service_data: ServiceCreateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
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
    
    service = Service(
        name=service_data.name,
        description=service_data.description,
        price=service_data.price,
        duration=service_data.duration,
        is_active=service_data.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(service)
    await tenant_session.commit()
    await tenant_session.refresh(service)
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Создана услуга: service_id={service.id}, company_id={company_id}")
    
    return ServiceResponse.model_validate(service)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить услугу.
    
    Аргументы:
        service_id: ID услуги
        service_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять услуги")
    
    result = await tenant_session.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    if service_data.name is not None:
        service.name = service_data.name
    if service_data.description is not None:
        service.description = service_data.description
    if service_data.price is not None:
        service.price = service_data.price
    if service_data.duration is not None:
        service.duration = service_data.duration
    if service_data.is_active is not None:
        service.is_active = service_data.is_active
    
    service.updated_at = datetime.utcnow()
    await tenant_session.commit()
    await tenant_session.refresh(service)
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Обновлена услуга: service_id={service_id}, company_id={company_id}")
    
    return ServiceResponse.model_validate(service)


@router.delete("/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
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
    
    result = await tenant_session.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    await tenant_session.delete(service)
    await tenant_session.commit()
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Удалена услуга: service_id={service_id}, company_id={company_id}")
    
    return None
