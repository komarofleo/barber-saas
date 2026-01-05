from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, Setting
from ..schemas.setting import SettingResponse, SettingUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("", response_model=list[SettingResponse])
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить все настройки"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать настройки")
    
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings = result.scalars().all()
    return [SettingResponse.model_validate(setting) for setting in settings]

@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить настройку по ключу"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать настройки")
    
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    
    return SettingResponse.model_validate(setting)

@router.patch("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_data: SettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить настройку"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут изменять настройки")
    
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    
    setting.value = setting_data.value
    await db.commit()
    await db.refresh(setting)
    
    return SettingResponse.model_validate(setting)









