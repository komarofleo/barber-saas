from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, Master, Booking, Client, Service, Post
from ..schemas.master import (
    MasterResponse, MasterListResponse,
    MasterCreateRequest, MasterUpdateRequest
)
from ..schemas.booking import BookingResponse

router = APIRouter(prefix="/api/masters", tags=["masters"])


@router.get("", response_model=MasterListResponse)
async def get_masters(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список мастеров"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать мастеров")
    
    query = select(Master)
    
    # Поиск по имени или телефону
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Master.full_name.ilike(search_term),
                Master.phone.ilike(search_term)
            )
        )
    
    # Подсчет общего количества
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Master.full_name)
    
    result = await db.execute(query)
    masters = result.scalars().all()
    
    return {
        "items": [MasterResponse.model_validate(master) for master in masters],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{master_id}", response_model=MasterResponse)
async def get_master(
    master_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о мастере"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать мастеров")
    
    query = select(Master).where(Master.id == master_id)
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    return MasterResponse.model_validate(master)


@router.post("", response_model=MasterResponse, status_code=201)
async def create_master(
    master_data: MasterCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать нового мастера"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать мастеров")
    
    master = Master(
        user_id=master_data.user_id,
        full_name=master_data.full_name,
        phone=master_data.phone,
        telegram_id=master_data.telegram_id,
        specialization=master_data.specialization,
        is_universal=master_data.is_universal
    )
    
    db.add(master)
    await db.commit()
    await db.refresh(master)
    
    return MasterResponse.model_validate(master)


@router.patch("/{master_id}", response_model=MasterResponse)
async def update_master(
    master_id: int,
    master_data: MasterUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить мастера"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять мастеров")
    
    query = select(Master).where(Master.id == master_id)
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Обновляем только переданные поля
    update_data = master_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(master, key, value)
    
    await db.commit()
    await db.refresh(master)
    
    return MasterResponse.model_validate(master)


@router.delete("/{master_id}", status_code=204)
async def delete_master(
    master_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить мастера"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять мастеров")
    
    query = select(Master).where(Master.id == master_id)
    result = await db.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    await db.delete(master)
    await db.commit()
    
    return None


@router.get("/{master_id}/schedule")
async def get_master_schedule(
    master_id: int,
    schedule_date: date = Query(..., alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить расписание мастера на дату (лист-наряд)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать расписание")
    
    # Проверяем существование мастера
    master_query = select(Master).where(Master.id == master_id)
    master_result = await db.execute(master_query)
    master = master_result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Получаем записи мастера на дату
    bookings_query = select(Booking).where(
        and_(
            Booking.master_id == master_id,
            Booking.service_date == schedule_date,
            Booking.status.in_(["confirmed", "new"])
        )
    ).order_by(Booking.time.asc()).options(
        selectinload(Booking.client).selectinload(Client.user),
        selectinload(Booking.service),
        selectinload(Booking.post)
    )
    
    bookings_result = await db.execute(bookings_query)
    bookings = bookings_result.scalars().all()
    
    # Формируем ответ
    items = []
    for booking in bookings:
        booking_dict = {
            "id": booking.id,
            "booking_number": booking.booking_number,
            "client_id": booking.client_id,
            "service_id": booking.service_id,
            "master_id": booking.master_id,
            "post_id": booking.post_id,
            "date": booking.service_date,
            "time": booking.time,
            "duration": booking.duration,
            "end_time": booking.end_time,
            "status": booking.status,
            "amount": booking.amount,
            "is_paid": booking.is_paid or False,
            "payment_method": booking.payment_method,
            "comment": booking.comment,
            "admin_comment": booking.admin_comment,
            "created_at": booking.created_at,
            "confirmed_at": booking.confirmed_at,
            "completed_at": booking.completed_at,
            "cancelled_at": booking.cancelled_at,
            "client_name": None,
            "client_phone": None,
            "client_telegram_id": None,
            "service_name": None,
            "master_name": None,
            "post_number": None,
        }
        
        if booking.client:
            if booking.client.user:
                booking_dict["client_name"] = f"{booking.client.user.first_name or ''} {booking.client.user.last_name or ''}".strip() or booking.client.full_name
                booking_dict["client_telegram_id"] = booking.client.user.telegram_id
            else:
                booking_dict["client_name"] = booking.client.full_name
                booking_dict["client_telegram_id"] = None
            booking_dict["client_phone"] = booking.client.phone
        if booking.service:
            booking_dict["service_name"] = booking.service.name
        if booking.master:
            booking_dict["master_name"] = booking.master.full_name
        if booking.post:
            booking_dict["post_number"] = booking.post.number
        
        items.append(BookingResponse.model_validate(booking_dict))
    
    return {
        "master_id": master.id,
        "master_name": master.full_name,
        "date": schedule_date.isoformat(),
        "bookings": items
    }

