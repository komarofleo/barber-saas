from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import Optional

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, Service
from ..schemas.service import (
    ServiceResponse, ServiceListResponse,
    ServiceCreateRequest, ServiceUpdateRequest
)

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("", response_model=ServiceListResponse)
async def get_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список услуг"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать услуги")
    
    query = select(Service)
    
    # Поиск по названию
    if search:
        search_term = f"%{search}%"
        query = query.where(Service.name.ilike(search_term))
    
    # Фильтр по активности
    if is_active is not None:
        query = query.where(Service.is_active == is_active)
    
    # Подсчет общего количества
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Service.name)
    
    result = await db.execute(query)
    services = result.scalars().all()
    
    return {
        "items": [ServiceResponse.model_validate(service) for service in services],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить информацию об услуге"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать услуги")
    
    query = select(Service).where(Service.id == service_id)
    result = await db.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    return ServiceResponse.model_validate(service)


@router.post("", response_model=ServiceResponse, status_code=201)
async def create_service(
    service_data: ServiceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новую услугу"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать услуги")
    
    service = Service(
        name=service_data.name,
        description=service_data.description,
        price=service_data.price,
        duration=service_data.duration,
        is_active=service_data.is_active
    )
    
    db.add(service)
    await db.commit()
    await db.refresh(service)
    
    return ServiceResponse.model_validate(service)


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить услугу"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять услуги")
    
    query = select(Service).where(Service.id == service_id)
    result = await db.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    # Обновляем только переданные поля
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
    
    await db.commit()
    await db.refresh(service)
    
    return ServiceResponse.model_validate(service)


@router.delete("/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить услугу"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять услуги")
    
    query = select(Service).where(Service.id == service_id)
    result = await db.execute(query)
    service = result.scalar_one_or_none()
    
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    
    await db.delete(service)
    await db.commit()
    
    return None









