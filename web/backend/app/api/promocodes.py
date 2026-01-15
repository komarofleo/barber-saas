from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

from app.deps.tenant import get_tenant_db
from .auth import get_current_user
from shared.database.models import User, Promocode, Service, Booking
from ..schemas.promocode import (
    PromocodeResponse, PromocodeListResponse, PromocodeCreateRequest,
    PromocodeUpdateRequest, PromocodeValidateResponse
)

router = APIRouter(prefix="/api/promocodes", tags=["promocodes"])

@router.get("", response_model=PromocodeListResponse)
async def get_promocodes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список промокодов"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать промокоды")
    
    query = select(Promocode)
    
    if is_active is not None:
        query = query.where(Promocode.is_active == is_active)
    
    query = query.order_by(Promocode.created_at.desc())
    
    result = await db.execute(query)
    all_promocodes = result.scalars().all()
    
    total = len(all_promocodes)
    start = (page - 1) * page_size
    end = start + page_size
    promocodes = all_promocodes[start:end]
    
    items = []
    for promo in promocodes:
        promo_dict = {
            "id": promo.id,
            "code": promo.code,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value,
            "service_id": promo.service_id,
            "min_amount": promo.min_amount,
            "max_uses": promo.max_uses,
            "current_uses": promo.current_uses,
            "start_date": promo.start_date,
            "end_date": promo.end_date,
            "is_active": promo.is_active,
            "description": promo.description,
            "created_at": promo.created_at,
            "service_name": None,
        }
        
        if promo.service_id:
            service_result = await db.execute(select(Service).where(Service.id == promo.service_id))
            service = service_result.scalar_one_or_none()
            if service:
                promo_dict["service_name"] = service.name
        
        items.append(PromocodeResponse.model_validate(promocode_dict))
    
    return PromocodeListResponse(items=items, total=total)

@router.post("", response_model=PromocodeResponse, status_code=201)
async def create_promocode(
    promo_data: PromocodeCreateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Создать промокод"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать промокоды")
    
    # Проверяем уникальность кода
    existing = await db.execute(select(Promocode).where(Promocode.code == promo_data.code.upper()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Промокод с таким кодом уже существует")
    
    promocode = Promocode(
        code=promo_data.code.upper(),
        discount_type=promo_data.discount_type,
        discount_value=promo_data.discount_value,
        service_id=promo_data.service_id,
        min_amount=promo_data.min_amount,
        max_uses=promo_data.max_uses,
        start_date=promo_data.start_date,
        end_date=promo_data.end_date,
        description=promo_data.description,
        is_active=True,
    )
    
    db.add(promocode)
    await db.commit()
    await db.refresh(promocode)
    
    promo_dict = {
        "id": promocode.id,
        "code": promocode.code,
        "discount_type": promocode.discount_type,
        "discount_value": promocode.discount_value,
        "service_id": promocode.service_id,
        "min_amount": promocode.min_amount,
        "max_uses": promocode.max_uses,
        "current_uses": promocode.current_uses,
        "start_date": promocode.start_date,
        "end_date": promocode.end_date,
        "is_active": promocode.is_active,
        "description": promocode.description,
        "created_at": promocode.created_at,
        "service_name": None,
    }
    
    if promocode.service_id:
        service_result = await db.execute(select(Service).where(Service.id == promocode.service_id))
        service = service_result.scalar_one_or_none()
        if service:
            promo_dict["service_name"] = service.name
    
    return PromocodeResponse.model_validate(promo_dict)

@router.get("/validate/{code}", response_model=PromocodeValidateResponse)
async def validate_promocode(
    code: str,
    service_id: Optional[int] = Query(None),
    amount: Optional[Decimal] = Query(None),
    db: AsyncSession = Depends(get_tenant_db)
):
    """Валидировать промокод"""
    result = await db.execute(select(Promocode).where(Promocode.code == code.upper()))
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        return PromocodeValidateResponse(valid=False, error="Промокод не найден")
    
    if not promocode.is_active:
        return PromocodeValidateResponse(valid=False, error="Промокод неактивен")
    
    today = date.today()
    if promocode.start_date and promocode.start_date > today:
        return PromocodeValidateResponse(valid=False, error="Промокод еще не действует")
    
    if promocode.end_date and promocode.end_date < today:
        return PromocodeValidateResponse(valid=False, error="Промокод истек")
    
    if promocode.max_uses and promocode.current_uses >= promocode.max_uses:
        return PromocodeValidateResponse(valid=False, error="Промокод исчерпан")
    
    if promocode.service_id and service_id and promocode.service_id != service_id:
        return PromocodeValidateResponse(valid=False, error="Промокод не применим к данной услуге")
    
    if amount and promocode.min_amount > amount:
        return PromocodeValidateResponse(valid=False, error=f"Минимальная сумма для промокода: {promocode.min_amount}")
    
    # Вычисляем скидку
    discount_amount = Decimal("0.00")
    if amount:
        if promocode.discount_type == "percent":
            discount_amount = amount * promocode.discount_value / Decimal("100")
        else:
            discount_amount = promocode.discount_value
        
        if discount_amount > amount:
            discount_amount = amount
    
    final_amount = (amount - discount_amount) if amount else Decimal("0.00")
    
    promo_dict = {
        "id": promocode.id,
        "code": promocode.code,
        "discount_type": promocode.discount_type,
        "discount_value": promocode.discount_value,
        "service_id": promocode.service_id,
        "min_amount": promocode.min_amount,
        "max_uses": promocode.max_uses,
        "current_uses": promocode.current_uses,
        "start_date": promocode.start_date,
        "end_date": promocode.end_date,
        "is_active": promocode.is_active,
        "description": promocode.description,
        "created_at": promocode.created_at,
        "service_name": None,
    }
    
    return PromocodeValidateResponse(
        valid=True,
        promocode=PromocodeResponse.model_validate(promo_dict),
        discount_amount=discount_amount,
        final_amount=final_amount
    )

@router.patch("/{promocode_id}", response_model=PromocodeResponse)
async def update_promocode(
    promocode_id: int,
    promo_data: PromocodeUpdateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить промокод"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять промокоды")
    
    result = await db.execute(select(Promocode).where(Promocode.id == promocode_id))
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    update_data = promo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(promocode, key, value)
    
    await db.commit()
    await db.refresh(promocode)
    
    promo_dict = {
        "id": promocode.id,
        "code": promocode.code,
        "discount_type": promocode.discount_type,
        "discount_value": promocode.discount_value,
        "service_id": promocode.service_id,
        "min_amount": promocode.min_amount,
        "max_uses": promocode.max_uses,
        "current_uses": promocode.current_uses,
        "start_date": promocode.start_date,
        "end_date": promocode.end_date,
        "is_active": promocode.is_active,
        "description": promocode.description,
        "created_at": promocode.created_at,
        "service_name": None,
    }
    
    if promocode.service_id:
        service_result = await db.execute(select(Service).where(Service.id == promocode.service_id))
        service = service_result.scalar_one_or_none()
        if service:
            promo_dict["service_name"] = service.name
    
    return PromocodeResponse.model_validate(promo_dict)

@router.delete("/{promocode_id}", status_code=204)
async def delete_promocode(
    promocode_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить промокод"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять промокоды")
    
    result = await db.execute(select(Promocode).where(Promocode.id == promocode_id))
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    await db.delete(promocode)
    await db.commit()
    
    return None

@router.get("/{promocode_id}/statistics")
async def get_promocode_statistics(
    promocode_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Статистика промокода"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать статистику")
    
    result = await db.execute(select(Promocode).where(Promocode.id == promocode_id))
    promocode = result.scalar_one_or_none()
    
    if not promocode:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    
    # Подсчитываем использование
    bookings_result = await db.execute(
        select(Booking).where(Booking.promocode_id == promocode_id)
    )
    bookings = bookings_result.scalars().all()
    
    total_uses = len(bookings_result)
    total_discount = sum(b.discount_amount or Decimal("0.00") for b in bookings)
    total_revenue = sum(b.amount or Decimal("0.00") for b in bookings if b.status == "completed")
    
    return {
        "promocode_id": promocode_id,
        "code": promocode.code,
        "total_uses": total_uses,
        "current_uses": promocode.current_uses,
        "max_uses": promocode.max_uses,
        "total_discount": float(total_discount),
        "total_revenue": float(total_revenue),
        "bookings": [
            {
                "id": b.id,
                "booking_number": b.booking_number,
                "date": b.date.isoformat() if b.date else None,
                "amount": float(b.amount or Decimal("0.00")),
                "discount_amount": float(b.discount_amount or Decimal("0.00")),
                "status": b.status
            }
            for b in bookings[:10]  # Последние 10 использований
        ]
    }

