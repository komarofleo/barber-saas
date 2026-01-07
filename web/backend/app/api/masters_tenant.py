"""
API для работы с мастерами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

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
from app.schemas.master import (
    MasterResponse, MasterListResponse,
    MasterCreateRequest, MasterUpdateRequest
)
from shared.database.models import User, Master, Booking
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/masters", tags=["masters"])


@router.get("", response_model=MasterListResponse)
async def get_masters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список мастеров.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска
        is_active: фильтр по активности
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать мастеров")
    
    # Используем обычную сессию db, но устанавливаем search_path для tenant схемы
    tenant_session = db
    if company_id:
        # Устанавливаем search_path для tenant схемы
        await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    
    query = select(Master)
    
    # Фильтры
    if search:
        search_term = f"%{search}%"
        query = query.where(Master.full_name.ilike(search_term))
    
    # Подсчет общего количества
    count_query = select(func.count(Master.id))
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Master.full_name)
    
    result = await tenant_session.execute(query)
    masters = result.scalars().all()
    
    print(f"📊 Запрос мастеров: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for master in masters:
        # Считаем количество записей для мастера
        booking_count = await tenant_session.scalar(
            select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master.id)
        )
        
        master_dict = {
            "id": master.id,
            "user_id": master.user_id,
            "full_name": master.full_name,
            "phone": master.phone,
            "telegram_id": master.telegram_id,
            "specialization": master.specialization,
            "is_universal": master.is_universal,
            "booking_count": booking_count or 0,
            "created_at": master.created_at,
            "updated_at": master.updated_at,
        }
        items.append(MasterResponse.model_validate(master_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{master_id}", response_model=MasterResponse)
async def get_master(
    master_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о мастере.
    
    Аргументы:
        master_id: ID мастера
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать мастеров")
    
    # Используем обычную сессию db, но устанавливаем search_path для tenant схемы
    tenant_session = db
    if company_id:
        # Устанавливаем search_path для tenant схемы
        await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    
    query = select(Master).where(Master.id == master_id)
    result = await tenant_session.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    print(f"🔍 Запрос мастера: master_id={master_id}, company_id={company_id}")
    
    # Считаем количество записей для мастера
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master.id)
    )
    
    # Формируем ответ
    master_dict = {
        "id": master.id,
        "full_name": master.full_name,
        "phone": master.phone,
        "specialization": master.specialization,
        "is_active": master.is_active,
        "booking_count": booking_count or 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
        "company_id": company_id,
    }
    
    return MasterResponse.model_validate(master_dict)


@router.post("", response_model=MasterResponse, status_code=201)
async def create_master(
    master_data: MasterCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать нового мастера.
    
    Аргументы:
        master_data: данные мастера
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать мастеров")
    
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
    
    # Проверяем, существует ли мастер с таким именем
    existing_master = await tenant_session.execute(
        select(Master).where(Master.full_name == master_data.full_name)
    ).scalar_one_or_none()
    
    if existing_master:
        raise HTTPException(
            status_code=400,
            detail=f"Мастер с именем '{master_data.full_name}' уже существует"
        )
    
    # Создаем нового мастера
    master = Master(
        full_name=master_data.full_name,
        phone=master_data.phone,
        specialization=master_data.specialization,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(master)
    await tenant_session.commit()
    await tenant_session.refresh(master)
    
    print(f"✅ Создан мастер: name={master.full_name}, phone={master.phone}")
    
    # Отправляем уведомление
    # TODO: Создать Celery задачу для уведомления о новом мастере
    
    # Формируем ответ
    master_dict = {
        "id": master.id,
        "full_name": master.full_name,
        "phone": master.phone,
        "specialization": master.specialization,
        "is_active": master.is_active,
        "booking_count": 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
        "company_id": company_id,
    }
    
    return MasterResponse.model_validate(master_dict)


@router.patch("/{master_id}", response_model=MasterResponse)
async def update_master(
    master_id: int,
    master_data: MasterUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию о мастере.
    
    Аргументы:
        master_id: ID мастера
        master_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять мастеров")
    
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
    
    # Проверяем существование мастера
    query = select(Master).where(Master.id == master_id)
    result = await tenant_session.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Обновляем поля
    update_data = {}
    if master_data.full_name is not None:
        update_data["full_name"] = master_data.full_name
    if master_data.phone is not None:
        update_data["phone"] = master_data.phone
    if master_data.specialization is not None:
        update_data["specialization"] = master_data.specialization
    if master_data.is_active is not None:
        update_data["is_active"] = master_data.is_active
    
    master.updated_at = datetime.utcnow()
    update_data["updated_at"] = master.updated_at
    
    # Выполняем обновление
    await tenant_session.execute(
        select(Master).where(Master.id == master_id).values(**update_data)
    )
    await tenant_session.commit()
    await tenant_session.refresh(master)
    
    print(f"✅ Обновлен мастер: master_id={master_id}, name={master_data.full_name if master_data.full_name else master.full_name}")
    
    # Формируем ответ
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master.id)
    )
    
    master_dict = {
        "id": master.id,
        "full_name": master.full_name,
        "phone": master.phone,
        "specialization": master.specialization,
        "is_active": master.is_active,
        "booking_count": booking_count or 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
        "company_id": company_id,
    }
    
    return MasterResponse.model_validate(master_dict)


@router.delete("/{master_id}", status_code=204)
async def delete_master(
    master_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить мастера.
    
    Аргументы:
        master_id: ID мастера
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять мастеров")
    
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
    
    # Проверяем существование мастера
    query = select(Master).where(Master.id == master_id)
    result = await tenant_session.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Проверяем, используются ли записи с этим мастером
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master_id)
    )
    
    if booking_count and booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить мастера '{master.full_name}', так как с ним связаны {booking_count} записей"
        )
    
    # Удаляем мастера
    await tenant_session.execute(
        delete(Master).where(Master.id == master_id)
    )
    await tenant_session.commit()
    
    print(f"✅ Удален мастер: master_id={master_id}, name={master.full_name}")
    
    return None

