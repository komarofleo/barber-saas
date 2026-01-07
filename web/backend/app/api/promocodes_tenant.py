"""
API для работы с промокодами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime, date
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.promocode import (
    PromocodeResponse, PromocodeListResponse,
    PromocodeCreateRequest, PromocodeUpdateRequest
)
from shared.database.models import User, Promocode, Client
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/promocodes", tags=["promocodes"])


@router.get("", response_model=PromocodeListResponse)
async def get_promocodes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список промокодов.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска (по коду, названию)
        is_active: фильтр по активности
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать промокоды")
    
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
    
    query = select(Promocode)
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Promocode.code.ilike(search_term),
                Promocode.name.ilike(search_term),
            )
        )
    
    if is_active is not None:
        query = query.where(Promocode.is_active == is_active)
    
    # Подсчет общего количества
    count_query = select(func.count(Promocode.id))
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Promocode.created_at.desc())
    
    result = await tenant_session.execute(query)
    promocodes = result.scalars().all()
    
    print(f"📊 Запрос промокодов: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for promocode in promocodes:
        # Проверяем актуальность промокода (по дате)
        is_expired = False
        if promocode.end_date and promocode.end_date < date.today():
            is_expired = True
        
        # Считаем количество использований
        usage_count = await tenant_session.scalar(
            select(func.count(Client.id)).select_from(Client).where(Client.promocode_id == promocode.id)
        )
        
        promocode_dict = {
            "id": promocode.id,
            "code": promocode.code,
            "name": promocode.name,
            "description": promocode.description,
            "discount_percent": float(promocode.discount_percent),
            "max_uses": promocode.max_uses,
            "start_date": promocode.start_date,
            "end_date": promocode.end_date,
            "is_active": promocode.is_active,
            "is_expired": is_expired,
            "usage_count": usage_count or 0,
            "remaining_uses": (promocode.max_uses - (usage_count or 0)) if promocode.max_uses else None,
            "created_at": promocode.created_at,
            "updated_at": promocode.updated_at,
            "company_id": company_id,
        }
        items.append(PromocodeResponse.model_validate(promocode_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{promocode_id}", response_model=PromocodeResponse)
async def get_promocode(
    promocode_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о промокоде.
    
    Аргументы:
        promocode_id: ID промокода
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать промокоды")
    
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
    
    query = select(Promocode).where(Promocode.id == promocode_id)
    result = await tenant_session.execute(query)
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    print(f"🔍 Запрос промокода: promocode_id={promocode_id}, company_id={company_id}")
    
    # Проверяем актуальность промокода (по дате)
    is_expired = False
    if promocode.end_date and promocode.end_date < date.today():
        is_expired = True
    
    # Считаем количество использований
    usage_count = await tenant_session.scalar(
        select(func.count(Client.id)).select_from(Client).where(Client.promocode_id == promocode.id)
    )
    
    # Формируем ответ
    promocode_dict = {
        "id": promocode.id,
        "code": promocode.code,
        "name": promocode.name,
        "description": promocode.description,
        "discount_percent": float(promocode.discount_percent),
        "max_uses": promocode.max_uses,
        "start_date": promocode.start_date,
        "end_date": promocode.end_date,
        "is_active": promocode.is_active,
        "is_expired": is_expired,
        "usage_count": usage_count or 0,
        "remaining_uses": (promocode.max_uses - (usage_count or 0)) if promocode.max_uses else None,
        "created_at": promocode.created_at,
        "updated_at": promocode.updated_at,
        "company_id": company_id,
    }
    
    return PromocodeResponse.model_validate(promocode_dict)


@router.post("", response_model=PromocodeResponse, status_code=201)
async def create_promocode(
    promocode_data: PromocodeCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать новый промокод.
    
    Аргументы:
        promocode_data: данные промокода
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать промокоды")
    
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
    
    # Проверяем, существует ли промокод с таким кодом
    existing_promocode = await tenant_session.execute(
        select(Promocode).where(Promocode.code == promocode_data.code.upper())
    ).scalar_one_or_none()
    
    if existing_promocode:
        raise HTTPException(
            status_code=400,
            detail=f"Промокод с кодом '{promocode_data.code.upper()}' уже существует"
        )
    
    # Валидация дат: start_date должен быть не больше end_date
    if promocode_data.start_date and promocode_data.end_date:
        if promocode_data.start_date > promocode_data.end_date:
            raise HTTPException(
                status_code=400,
                detail="Дата начала должна быть не больше даты окончания"
            )
    
    # Валидация скидки: от 0 до 100
    if promocode_data.discount_percent < 0 or promocode_data.discount_percent > 100:
        raise HTTPException(
            status_code=400,
            detail="Скидка должна быть от 0% до 100%"
        )
    
    # Валидация максимального использования: должно быть > 0
    if promocode_data.max_uses is not None and promocode_data.max_uses <= 0:
        raise HTTPException(
            status_code=400,
            detail="Максимальное количество использований должно быть больше 0"
        )
    
    # Создаем новый промокод
    promocode = Promocode(
        code=promocode_data.code.upper(),
        name=promocode_data.name,
        description=promocode_data.description,
        discount_percent=float(promocode_data.discount_percent),
        max_uses=promocode_data.max_uses,
        start_date=promocode_data.start_date,
        end_date=promocode_data.end_date,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(promocode)
    await tenant_session.commit()
    await tenant_session.refresh(promocode)
    
    print(f"✅ Создан промокод: code={promocode.code}, name={promocode.name}, discount={promocode_data.discount_percent}%")
    
    # Формируем ответ
    promocode_dict = {
        "id": promocode.id,
        "code": promocode.code,
        "name": promocode.name,
        "description": promocode.description,
        "discount_percent": float(promocode.discount_percent),
        "max_uses": promocode.max_uses,
        "start_date": promocode.start_date,
        "end_date": promocode.end_date,
        "is_active": promocode.is_active,
        "is_expired": False,
        "usage_count": 0,
        "remaining_uses": promocode.max_uses,
        "created_at": promocode.created_at,
        "updated_at": promocode.updated_at,
        "company_id": company_id,
    }
    
    return PromocodeResponse.model_validate(promocode_dict)


@router.patch("/{promocode_id}", response_model=PromocodeResponse)
async def update_promocode(
    promocode_id: int,
    promocode_data: PromocodeUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию о промокоде.
    
    Аргументы:
        promocode_id: ID промокода
        promocode_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять промокоды")
    
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
    
    # Проверяем существование промокода
    query = select(Promocode).where(Promocode.id == promocode_id)
    result = await tenant_session.execute(query)
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    # Обновляем поля
    update_data = {}
    if promocode_data.code is not None:
        # Проверяем, что код не занят
        if promocode_data.code.upper() != promocode.code:
            existing_promocode = await tenant_session.execute(
                select(Promocode).where(Promocode.code == promocode_data.code.upper())
            ).scalar_one_or_none()
            if existing_promocode:
                raise HTTPException(
                    status_code=400,
                    detail=f"Промокод с кодом '{promocode_data.code.upper()}' уже существует"
                )
        promocode.code = promocode_data.code.upper()
        update_data["code"] = promocode.code
    
    if promocode_data.name is not None:
        promocode.name = promocode_data.name
        update_data["name"] = promocode.name
    
    if promocode_data.description is not None:
        promocode.description = promocode_data.description
        update_data["description"] = promocode.description
    
    if promocode_data.discount_percent is not None:
        # Валидация скидки: от 0 до 100
        if promocode_data.discount_percent < 0 or promocode_data.discount_percent > 100:
            raise HTTPException(
                status_code=400,
                detail="Скидка должна быть от 0% до 100%"
            )
        promocode.discount_percent = float(promocode_data.discount_percent)
        update_data["discount_percent"] = promocode.discount_percent
    
    if promocode_data.max_uses is not None:
        # Валидация: должно быть > 0
        if promocode_data.max_uses <= 0:
            raise HTTPException(
                status_code=400,
                detail="Максимальное количество использований должно быть больше 0"
            )
        promocode.max_uses = promocode_data.max_uses
        update_data["max_uses"] = promocode.max_uses
    
    if promocode_data.start_date is not None:
        promocode.start_date = promocode_data.start_date
        update_data["start_date"] = promocode.start_date
    
    if promocode_data.end_date is not None:
        promocode.end_date = promocode_data.end_date
        update_data["end_date"] = promocode.end_date
    
    if promocode_data.is_active is not None:
        promocode.is_active = promocode_data.is_active
        update_data["is_active"] = promocode.is_active
    
    # Валидация дат: start_date должен быть не больше end_date
    if promocode.start_date and promocode.end_date:
        if promocode.start_date > promocode.end_date:
            raise HTTPException(
                status_code=400,
                detail="Дата начала должна быть не больше даты окончания"
            )
    
    promocode.updated_at = datetime.utcnow()
    update_data["updated_at"] = promocode.updated_at
    
    # Выполняем обновление
    await tenant_session.execute(
        select(Promocode).where(Promocode.id == promocode_id).values(**update_data)
    )
    await tenant_session.commit()
    await tenant_session.refresh(promocode)
    
    print(f"✅ Обновлен промокод: promocode_id={promocode_id}, code={promocode.code}")
    
    # Проверяем актуальность промокода (по дате)
    is_expired = False
    if promocode.end_date and promocode.end_date < date.today():
        is_expired = True
    
    # Считаем количество использований
    usage_count = await tenant_session.scalar(
        select(func.count(Client.id)).select_from(Client).where(Client.promocode_id == promocode.id)
    )
    
    # Формируем ответ
    promocode_dict = {
        "id": promocode.id,
        "code": promocode.code,
        "name": promocode.name,
        "description": promocode.description,
        "discount_percent": float(promocode.discount_percent),
        "max_uses": promocode.max_uses,
        "start_date": promocode.start_date,
        "end_date": promocode.end_date,
        "is_active": promocode.is_active,
        "is_expired": is_expired,
        "usage_count": usage_count or 0,
        "remaining_uses": (promocode.max_uses - (usage_count or 0)) if promocode.max_uses else None,
        "created_at": promocode.created_at,
        "updated_at": promocode.updated_at,
        "company_id": company_id,
    }
    
    return PromocodeResponse.model_validate(promocode_dict)


@router.delete("/{promocode_id}", status_code=204)
async def delete_promocode(
    promocode_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить промокод.
    
    Аргументы:
        promocode_id: ID промокода
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять промокоды")
    
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
    
    # Проверяем существование промокода
    query = select(Promocode).where(Promocode.id == promocode_id)
    result = await tenant_session.execute(query)
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    # Проверяем, используется ли промокод
    usage_count = await tenant_session.scalar(
        select(func.count(Client.id)).select_from(Client).where(Client.promocode_id == promocode_id)
    )
    
    if usage_count and usage_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить промокод '{promocode.code}', так как он уже использовался {usage_count} раз"
        )
    
    # Удаляем промокод
    await tenant_session.execute(
        delete(Promocode).where(Promocode.id == promocode_id)
    )
    await tenant_session.commit()
    
    print(f"✅ Удален промокод: promocode_id={promocode_id}, code={promocode.code}")
    
    return None

