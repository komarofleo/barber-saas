"""
API для работы с пользователями (tenant-схема).

Схема users соответствует shared.database.models.User:
telegram_id, username, first_name, last_name, phone,
is_admin, is_master, is_blocked, created_at, updated_at.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.deps.tenant import get_tenant_db
from app.schemas.user import UserCreateRequest, UserListResponse, UserResponse
from shared.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_response(user: User) -> UserResponse:
    """Собрать UserResponse из ORM-модели."""
    return UserResponse.model_validate(
        {
            "id": user.id,
            "telegram_id": user.telegram_id or 0,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_admin": bool(user.is_admin),
            "is_master": bool(user.is_master),
            "is_blocked": bool(user.is_blocked),
            "created_at": user.created_at,
            "updated_at": user.updated_at or user.created_at,
        }
    )


@router.get("", response_model=UserListResponse)
async def get_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список пользователей."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")

    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                User.username.ilike(term),
                User.phone.ilike(term),
                User.first_name.ilike(term),
                User.last_name.ilike(term),
                func.cast(User.telegram_id, String).ilike(term),
            )
        )

    count_query = select(func.count()).select_from(User)
    list_query = select(User).order_by(User.created_at.desc())
    if filters:
        count_query = count_query.where(*filters)
        list_query = list_query.where(*filters)

    total = (await tenant_session.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await tenant_session.execute(list_query.offset(offset).limit(page_size))
    users = result.scalars().all()

    company_id = getattr(request.state, "company_id", None)
    logger.info(
        "Запрос пользователей: total=%s, page=%s, page_size=%s, company_id=%s",
        total,
        page,
        page_size,
        company_id,
    )

    return {
        "items": [_to_response(user) for user in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о пользователе."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")

    result = await tenant_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    company_id = getattr(request.state, "company_id", None)
    logger.info("Запрос пользователя: user_id=%s, company_id=%s", user_id, company_id)
    return _to_response(user)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Создать нового пользователя."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать пользователей")

    existing_tg = await tenant_session.execute(
        select(User.id).where(User.telegram_id == user_data.telegram_id).limit(1)
    )
    if existing_tg.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Пользователь с telegram_id {user_data.telegram_id} уже существует",
        )

    if user_data.username:
        existing_username = await tenant_session.execute(
            select(User.id).where(User.username == user_data.username).limit(1)
        )
        if existing_username.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Пользователь с username {user_data.username} уже существует",
            )

    now = datetime.utcnow()
    user = User(
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        is_admin=bool(user_data.is_admin),
        is_master=bool(user_data.is_master),
        is_blocked=bool(user_data.is_blocked),
        created_at=now,
        updated_at=now,
    )
    tenant_session.add(user)
    await tenant_session.commit()
    await tenant_session.refresh(user)

    company_id = getattr(request.state, "company_id", None)
    logger.info(
        "Создан пользователь: id=%s, telegram_id=%s, company_id=%s",
        user.id,
        user.telegram_id,
        company_id,
    )
    return _to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    user_data: dict = Body(...),
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить информацию о пользователе."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять пользователей")

    result = await tenant_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if "username" in user_data and user_data["username"] is not None:
        user.username = user_data["username"]
    if "phone" in user_data and user_data["phone"] is not None:
        user.phone = user_data["phone"]
    if "first_name" in user_data:
        user.first_name = user_data.get("first_name")
    if "last_name" in user_data:
        user.last_name = user_data.get("last_name")
    if "is_admin" in user_data and user_data["is_admin"] is not None:
        user.is_admin = bool(user_data["is_admin"])
    if "is_master" in user_data and user_data["is_master"] is not None:
        user.is_master = bool(user_data["is_master"])
    if "is_blocked" in user_data and user_data["is_blocked"] is not None:
        user.is_blocked = bool(user_data["is_blocked"])

    user.updated_at = datetime.utcnow()
    await tenant_session.commit()
    await tenant_session.refresh(user)

    company_id = getattr(request.state, "company_id", None)
    logger.info("Обновлен пользователь: user_id=%s, company_id=%s", user_id, company_id)
    return _to_response(user)


@router.patch("/{user_id}/admin", response_model=UserResponse)
async def toggle_admin(
    user_id: int,
    request: Request,
    is_admin: bool = Query(..., description="Назначить пользователя администратором"),
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Назначить/снять права администратора."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут менять права пользователей")

    result = await tenant_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_admin = bool(is_admin)
    user.updated_at = datetime.utcnow()
    await tenant_session.commit()
    await tenant_session.refresh(user)

    company_id = getattr(request.state, "company_id", None)
    logger.info(
        "Обновлены права пользователя: user_id=%s, company_id=%s, is_admin=%s",
        user_id,
        company_id,
        user.is_admin,
    )
    return _to_response(user)
