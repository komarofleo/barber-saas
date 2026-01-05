from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import Optional

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, Client
from ..schemas.user import UserResponse, UserListResponse, UserCreateRequest

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список пользователей"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")
    
    query = select(User)
    
    # Поиск по имени или Telegram ID
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.telegram_id.cast(str).ilike(search_term)
            )
        )
    
    # Подсчет общего количества
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return {
        "items": [UserResponse.model_validate(user) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о пользователе"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")
    
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/admin", response_model=UserResponse)
async def toggle_admin(
    user_id: int,
    is_admin: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Назначить/снять администратора"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут назначать администраторов")
    
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    user.is_admin = is_admin
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать нового пользователя"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать пользователей")
    
    # Проверяем уникальность telegram_id
    existing = await db.execute(select(User).where(User.telegram_id == user_data.telegram_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пользователь с таким Telegram ID уже существует")
    
    user = User(
        telegram_id=user_data.telegram_id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        username=user_data.username,
        phone=user_data.phone,
        is_admin=user_data.is_admin or False,
        is_master=user_data.is_master or False,
        is_blocked=False  # Новые пользователи не заблокированы по умолчанию
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить данные пользователя"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять пользователей")
    
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Обновляем поля
    if "first_name" in user_data:
        user.first_name = user_data["first_name"] if user_data["first_name"] else None
    if "last_name" in user_data:
        user.last_name = user_data["last_name"] if user_data["last_name"] else None
    if "username" in user_data:
        user.username = user_data["username"] if user_data["username"] else None
    if "phone" in user_data:
        user.phone = user_data["phone"] if user_data["phone"] else None
    if "is_admin" in user_data:
        user.is_admin = user_data["is_admin"]
    if "is_master" in user_data:
        user.is_master = user_data["is_master"]
    if "is_blocked" in user_data:
        user.is_blocked = user_data["is_blocked"]
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)

