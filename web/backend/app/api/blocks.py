from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional
from datetime import date

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, BlockedSlot, Master, Post, Service
from ..schemas.blocked_slot import BlockedSlotResponse, BlockedSlotListResponse, BlockedSlotCreateRequest

router = APIRouter(prefix="/api/blocks", tags=["blocks"])

@router.get("", response_model=BlockedSlotListResponse)
async def get_blocks(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    block_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список блокировок"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать блокировки")
    
    query = select(BlockedSlot)
    
    if start_date:
        query = query.where(BlockedSlot.start_date >= start_date)
    if end_date:
        query = query.where(BlockedSlot.end_date <= end_date)
    if block_type:
        query = query.where(BlockedSlot.block_type == block_type)
    
    query = query.order_by(BlockedSlot.start_date.desc(), BlockedSlot.created_at.desc())
    
    result = await db.execute(query)
    blocks = result.scalars().all()
    
    # Загружаем связанные данные
    items = []
    for block in blocks:
        block_dict = {
            "id": block.id,
            "block_type": block.block_type,
            "master_id": block.master_id,
            "post_id": block.post_id,
            "service_id": block.service_id,
            "start_date": block.start_date,
            "end_date": block.end_date,
            "start_time": block.start_time,
            "end_time": block.end_time,
            "reason": block.reason,
            "created_at": block.created_at,
            "master_name": None,
            "post_number": None,
            "service_name": None,
        }
        
        if block.master_id:
            master_result = await db.execute(select(Master).where(Master.id == block.master_id))
            master = master_result.scalar_one_or_none()
            if master:
                block_dict["master_name"] = master.full_name
        
        if block.post_id:
            post_result = await db.execute(select(Post).where(Post.id == block.post_id))
            post = post_result.scalar_one_or_none()
            if post:
                block_dict["post_number"] = post.number
        
        if block.service_id:
            service_result = await db.execute(select(Service).where(Service.id == block.service_id))
            service = service_result.scalar_one_or_none()
            if service:
                block_dict["service_name"] = service.name
        
        items.append(BlockedSlotResponse.model_validate(block_dict))
    
    return BlockedSlotListResponse(items=items, total=len(items))

@router.post("", response_model=BlockedSlotResponse, status_code=201)
async def create_block(
    block_data: BlockedSlotCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать блокировку"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать блокировки")
    
    # Валидация типа блокировки
    if block_data.block_type == "master" and not block_data.master_id:
        raise HTTPException(status_code=400, detail="Для блокировки мастера необходимо указать master_id")
    if block_data.block_type == "post" and not block_data.post_id:
        raise HTTPException(status_code=400, detail="Для блокировки поста необходимо указать post_id")
    if block_data.block_type == "service" and not block_data.service_id:
        raise HTTPException(status_code=400, detail="Для блокировки услуги необходимо указать service_id")
    
    block = BlockedSlot(
        block_type=block_data.block_type,
        master_id=block_data.master_id,
        post_id=block_data.post_id,
        service_id=block_data.service_id,
        start_date=block_data.start_date,
        end_date=block_data.end_date,
        start_time=block_data.start_time,
        end_time=block_data.end_time,
        reason=block_data.reason,
        created_by=current_user.id,
    )
    
    db.add(block)
    await db.commit()
    await db.refresh(block)
    
    # Загружаем связанные данные для ответа
    block_dict = {
        "id": block.id,
        "block_type": block.block_type,
        "master_id": block.master_id,
        "post_id": block.post_id,
        "service_id": block.service_id,
        "start_date": block.start_date,
        "end_date": block.end_date,
        "start_time": block.start_time,
        "end_time": block.end_time,
        "reason": block.reason,
        "created_at": block.created_at,
        "master_name": None,
        "post_number": None,
        "service_name": None,
    }
    
    if block.master_id:
        master_result = await db.execute(select(Master).where(Master.id == block.master_id))
        master = master_result.scalar_one_or_none()
        if master:
            block_dict["master_name"] = master.full_name
    
    if block.post_id:
        post_result = await db.execute(select(Post).where(Post.id == block.post_id))
        post = post_result.scalar_one_or_none()
        if post:
            block_dict["post_number"] = post.number
    
    if block.service_id:
        service_result = await db.execute(select(Service).where(Service.id == block.service_id))
        service = service_result.scalar_one_or_none()
        if service:
            block_dict["service_name"] = service.name
    
    return BlockedSlotResponse.model_validate(block_dict)

@router.delete("/{block_id}", status_code=204)
async def delete_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить блокировку"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять блокировки")
    
    result = await db.execute(select(BlockedSlot).where(BlockedSlot.id == block_id))
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    
    await db.delete(block)
    await db.commit()
    
    return None

@router.patch("/toggle-accepting")
async def toggle_accepting(
    accepting: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Глобальная кнопка приема заявок"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут изменять настройки")
    
    from shared.database.models import Setting
    result = await db.execute(select(Setting).where(Setting.key == "accepting_bookings"))
    setting = result.scalar_one_or_none()
    
    if not setting:
        setting = Setting(key="accepting_bookings", value=str(accepting).lower(), description="Принимаются ли заявки (глобальная блокировка)")
        db.add(setting)
    else:
        setting.value = str(accepting).lower()
    
    await db.commit()
    
    return {
        "accepting": accepting,
        "message": "Прием заявок ВКЛЮЧЕН" if accepting else "Прием заявок ОТКЛЮЧЕН"
    }

