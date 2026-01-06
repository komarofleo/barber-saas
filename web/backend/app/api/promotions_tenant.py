"""
API для работы с акциями (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime, date
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.promotion import (
    PromotionResponse, PromotionListResponse,
    PromotionCreateRequest, PromotionUpdateRequest
)
from shared.database.models import User, Promotion
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/promotions", tags=["promotions"])


@router.get("", response_model=PromotionListResponse)
async def get_promotions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список акций.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска (по названию)
        is_active: фильтр по активности
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать акции")
    
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
    
    query = select(Promotion)
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.where(Promotion.name.ilike(search_term))
    
    if is_active is not None:
        query = query.where(Promotion.is_active == is_active)
    
    # Подсчет общего количества
    count_query = select(func.count(Promotion.id))
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Promotion.created_at.desc())
    
    result = await tenant_session.execute(query)
    promotions = result.scalars().all()
    
    print(f"📊 Запрос акций: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for promotion in promotions:
        # Проверяем актуальность акции (по датам)
        is_expired = False
        if promotion.end_date and promotion.end_date < date.today():
            is_expired = True
        
        promotion_dict = {
            "id": promotion.id,
            "name": promotion.name,
            "description": promotion.description,
            "discount_percent": float(promotion.discount_percent),
            "start_date": promotion.start_date,
            "end_date": promotion.end_date,
            "is_active": promotion.is_active,
            "is_expired": is_expired,
            "created_at": promotion.created_at,
            "updated_at": promotion.updated_at,
            "company_id": company_id,
        }
        items.append(PromotionResponse.model_validate(promotion_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{promotion_id}", response_model=PromotionResponse)
async def get_promotion(
    promotion_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию об акции.
    
    Аргументы:
        promotion_id: ID акции
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать акции")
    
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
    
    query = select(Promotion).where(Promotion.id == promotion_id)
    result = await tenant_session.execute(query)
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    print(f"🔍 Запрос акции: promotion_id={promotion_id}, company_id={company_id}")
    
    # Проверяем актуальность акции (по датам)
    is_expired = False
    if promotion.end_date and promotion.end_date < date.today():
        is_expired = True
    
    # Формируем ответ
    promotion_dict = {
        "id": promotion.id,
        "name": promotion.name,
        "description": promotion.description,
        "discount_percent": float(promotion.discount_percent),
        "start_date": promotion.start_date,
        "end_date": promotion.end_date,
        "is_active": promotion.is_active,
        "is_expired": is_expired,
        "created_at": promotion.created_at,
        "updated_at": promotion.updated_at,
        "company_id": company_id,
    }
    
    return PromotionResponse.model_validate(promotion_dict)


@router.post("", response_model=PromotionResponse, status_code=201)
async def create_promotion(
    promotion_data: PromotionCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать новую акцию.
    
    Аргументы:
        promotion_data: данные акции
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать акции")
    
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
    
    # Валидация дат: start_date должен быть не больше end_date
    if promotion_data.start_date and promotion_data.end_date:
        if promotion_data.start_date > promotion_data.end_date:
            raise HTTPException(
                status_code=400,
                detail="Дата начала должна быть не больше даты окончания"
            )
    
    # Валидация скидки: от 0 до 100
    if promotion_data.discount_percent < 0 or promotion_data.discount_percent > 100:
        raise HTTPException(
            status_code=400,
            detail="Скидка должна быть от 0% до 100%"
        )
    
    # Создаем новую акцию
    promotion = Promotion(
        name=promotion_data.name,
        description=promotion_data.description,
        discount_percent=float(promotion_data.discount_percent),
        start_date=promotion_data.start_date,
        end_date=promotion_data.end_date,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(promotion)
    await tenant_session.commit()
    await tenant_session.refresh(promotion)
    
    print(f"✅ Создана акция: name={promotion_data.name}, discount={promotion_data.discount_percent}%")
    
    # Отправляем уведомление
    # TODO: Создать Celery задачу для уведомления о новой акции
    
    # Формируем ответ
    promotion_dict = {
        "id": promotion.id,
        "name": promotion.name,
        "description": promotion.description,
        "discount_percent": float(promotion.discount_percent),
        "start_date": promotion.start_date,
        "end_date": promotion.end_date,
        "is_active": promotion.is_active,
        "is_expired": False,
        "created_at": promotion.created_at,
        "updated_at": promotion.updated_at,
        "company_id": company_id,
    }
    
    return PromotionResponse.model_validate(promotion_dict)


@router.patch("/{promotion_id}", response_model=PromotionResponse)
async def update_promotion(
    promotion_id: int,
    promotion_data: PromotionUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию об акции.
    
    Аргументы:
        promotion_id: ID акции
        promotion_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять акции")
    
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
    
    # Проверяем существование акции
    query = select(Promotion).where(Promotion.id == promotion_id)
    result = await tenant_session.execute(query)
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    # Обновляем поля
    update_data = {}
    if promotion_data.name is not None:
        promotion.name = promotion_data.name
        update_data["name"] = promotion.name
    
    if promotion_data.description is not None:
        promotion.description = promotion_data.description
        update_data["description"] = promotion.description
    
    if promotion_data.discount_percent is not None:
        # Валидация скидки: от 0 до 100
        if promotion_data.discount_percent < 0 or promotion_data.discount_percent > 100:
            raise HTTPException(
                status_code=400,
                detail="Скидка должна быть от 0% до 100%"
            )
        promotion.discount_percent = float(promotion_data.discount_percent)
        update_data["discount_percent"] = promotion.discount_percent
    
    if promotion_data.start_date is not None:
        promotion.start_date = promotion_data.start_date
        update_data["start_date"] = promotion.start_date
    
    if promotion_data.end_date is not None:
        promotion.end_date = promotion_data.end_date
        update_data["end_date"] = promotion.end_date
    
    if promotion_data.is_active is not None:
        promotion.is_active = promotion_data.is_active
        update_data["is_active"] = promotion.is_active
    
    # Валидация дат: start_date должен быть не больше end_date
    if promotion.start_date and promotion.end_date:
        if promotion.start_date > promotion.end_date:
            raise HTTPException(
                status_code=400,
                detail="Дата начала должна быть не больше даты окончания"
            )
    
    promotion.updated_at = datetime.utcnow()
    update_data["updated_at"] = promotion.updated_at
    
    # Выполняем обновление
    await tenant_session.execute(
        select(Promotion).where(Promotion.id == promotion_id).values(**update_data)
    )
    await tenant_session.commit()
    await tenant_session.refresh(promotion)
    
    print(f"✅ Обновлена акция: promotion_id={promotion_id}, name={promotion_data.name if promotion_data.name else promotion.name}")
    
    # Проверяем актуальность акции (по датам)
    is_expired = False
    if promotion.end_date and promotion.end_date < date.today():
        is_expired = True
    
    # Формируем ответ
    promotion_dict = {
        "id": promotion.id,
        "name": promotion.name,
        "description": promotion.description,
        "discount_percent": float(promotion.discount_percent),
        "start_date": promotion.start_date,
        "end_date": promotion.end_date,
        "is_active": promotion.is_active,
        "is_expired": is_expired,
        "created_at": promotion.created_at,
        "updated_at": promotion.updated_at,
        "company_id": company_id,
    }
    
    return PromotionResponse.model_validate(promotion_dict)


@router.delete("/{promotion_id}", status_code=204)
async def delete_promotion(
    promotion_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить акцию.
    
    Аргументы:
        promotion_id: ID акции
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять акции")
    
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
    
    # Проверяем существование акции
    query = select(Promotion).where(Promotion.id == promotion_id)
    result = await tenant_session.execute(query)
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    # Удаляем акцию
    await tenant_session.execute(
        delete(Promotion).where(Promotion.id == promotion_id)
    )
    await tenant_session.commit()
    
    print(f"✅ Удалена акция: promotion_id={promotion_id}, name={promotion.name}")
    
    return None

