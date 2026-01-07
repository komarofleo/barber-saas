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
from sqlalchemy import select, and_, or_, func, text
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
    # Используем обычную сессию db, но устанавливаем search_path для tenant схемы
    tenant_session = db
    if company_id:
        # Устанавливаем search_path для tenant схемы
        await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    
    query = select(Service)
    
    # Фильтры
    conditions = []
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
    
    print(f"📊 Запрос услуг: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for service in services:
        # Считаем количество записей для услуги
        booking_count = await tenant_session.scalar(
            select(func.count(Booking.id)).select_from(Booking).where(Booking.service_id == service.id)
        )
        
        service_dict = {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "price": float(service.price) if service.price else 0.0,
            "duration": service.duration,
            "is_active": service.is_active,
            "booking_count": booking_count,
            "created_at": service.created_at,
            "updated_at": service.updated_at,
            "company_id": company_id,
        }
        items.append(ServiceResponse.model_validate(service_dict))
    
    return ServiceListResponse(items=items, total=total, page=page, page_size=page_size)
