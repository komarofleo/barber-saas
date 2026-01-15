from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import date

from app.deps.tenant import get_tenant_db
from .auth import get_current_user
from shared.database.models import User, Promotion, Service
from ..schemas.promotion import (
    PromotionResponse, PromotionListResponse, PromotionCreateRequest, PromotionUpdateRequest
)

router = APIRouter(prefix="/api/promotions", tags=["promotions"])

@router.get("", response_model=PromotionListResponse)
async def get_promotions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    service_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список акций"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать акции")
    
    query = select(Promotion)
    
    if is_active is not None:
        query = query.where(Promotion.is_active == is_active)
    if service_id is not None:
        query = query.where(Promotion.service_id == service_id)
    
    query = query.order_by(Promotion.created_at.desc())
    
    result = await db.execute(query)
    all_promotions = result.scalars().all()
    
    total = len(all_promotions)
    start = (page - 1) * page_size
    end = start + page_size
    promotions = all_promotions[start:end]
    
    items = []
    for promo in promotions:
        promo_dict = {
            "id": promo.id,
            "name": promo.name,
            "description": promo.description,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "service_id": promo.service_id,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
            "is_active": promo.is_active,
            "created_at": promo.created_at,
            "service_name": None,
        }
        
        if promo.service_id:
            service_result = await db.execute(select(Service).where(Service.id == promo.service_id))
            service = service_result.scalar_one_or_none()
            if service:
                promo_dict["service_name"] = service.name
        
        items.append(PromotionResponse.model_validate(promotion_dict))
    
    return PromotionListResponse(items=items, total=total)

@router.get("/active", response_model=PromotionListResponse)
async def get_active_promotions(
    service_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Получить активные акции (публичный endpoint)"""
    today = date.today()
    query = select(Promotion).where(
        Promotion.is_active == True
    ).where(
        (Promotion.start_date.is_(None)) | (Promotion.start_date <= today)
    ).where(
        (Promotion.end_date.is_(None)) | (Promotion.end_date >= today)
    )
    
    if service_id is not None:
        query = query.where(
            (Promotion.service_id.is_(None)) | (Promotion.service_id == service_id)
        )
    
    query = query.order_by(Promotion.created_at.desc())
    
    result = await db.execute(query)
    promotions = result.scalars().all()
    
    items = []
    for promo in promotions:
        promo_dict = {
            "id": promo.id,
            "name": promo.name,
            "description": promo.description,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "service_id": promo.service_id,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
            "is_active": promo.is_active,
            "created_at": promo.created_at,
            "service_name": None,
        }
        
        if promo.service_id:
            service_result = await db.execute(select(Service).where(Service.id == promo.service_id))
            service = service_result.scalar_one_or_none()
            if service:
                promo_dict["service_name"] = service.name
        
        items.append(PromotionResponse.model_validate(promotion_dict))
    
    return PromotionListResponse(items=items, total=len(items))

@router.post("", response_model=PromotionResponse, status_code=201)
async def create_promotion(
    promo_data: PromotionCreateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Создать акцию"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать акции")
    
    promotion = Promotion(
        name=promo_data.name,
        description=promo_data.description,
        discount_type=promo_data.discount_type,
        discount_value=promo_data.discount_value,
        service_id=promo_data.service_id,
        start_date=promo_data.start_date,
        end_date=promo_data.end_date,
        is_active=True,
    )
    
    db.add(promotion)
    await db.commit()
    await db.refresh(promotion)
    
    promo_dict = {
        "id": promotion.id,
        "name": promotion.name,
        "description": promotion.description,
        "discount_type": promotion.discount_type,
        "discount_value": promotion.discount_value,
        "service_id": promotion.service_id,
        "start_date": promotion.start_date,
        "end_date": promotion.end_date,
        "is_active": promotion.is_active,
        "created_at": promotion.created_at,
        "service_name": None,
    }
    
    if promotion.service_id:
        service_result = await db.execute(select(Service).where(Service.id == promotion.service_id))
        service = service_result.scalar_one_or_none()
        if service:
            promo_dict["service_name"] = service.name
    
    return PromotionResponse.model_validate(promo_dict)

@router.patch("/{promotion_id}", response_model=PromotionResponse)
async def update_promotion(
    promotion_id: int,
    promo_data: PromotionUpdateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить акцию"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять акции")
    
    result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    update_data = promo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(promotion, key, value)
    
    await db.commit()
    await db.refresh(promotion)
    
    promo_dict = {
        "id": promotion.id,
        "name": promotion.name,
        "description": promotion.description,
        "discount_type": promotion.discount_type,
        "discount_value": promotion.discount_value,
        "service_id": promotion.service_id,
        "start_date": promotion.start_date,
        "end_date": promotion.end_date,
        "is_active": promotion.is_active,
        "created_at": promotion.created_at,
        "service_name": None,
    }
    
    if promotion.service_id:
        service_result = await db.execute(select(Service).where(Service.id == promotion.service_id))
        service = service_result.scalar_one_or_none()
        if service:
            promo_dict["service_name"] = service.name
    
    return PromotionResponse.model_validate(promo_dict)

@router.delete("/{promotion_id}", status_code=204)
async def delete_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить акцию"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять акции")
    
    result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
    promotion = result.scalar_one_or_none()
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Акция не найдена")
    
    await db.delete(promotion)
    await db.commit()
    
    return None









