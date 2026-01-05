from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import Optional

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, Post
from ..schemas.post import (
    PostResponse, PostListResponse,
    PostCreateRequest, PostUpdateRequest
)

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
async def get_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список постов"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать посты")
    
    query = select(Post)
    
    # Поиск по номеру или названию
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Post.name.ilike(search_term),
                Post.number.cast(str).ilike(search_term)
            )
        )
    
    # Фильтр по активности
    if is_active is not None:
        query = query.where(Post.is_active == is_active)
    
    # Подсчет общего количества
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Post.number)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return {
        "items": [PostResponse.model_validate(post) for post in posts],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о посте"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать посты")
    
    query = select(Post).where(Post.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    return PostResponse.model_validate(post)


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новый пост"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать посты")
    
    # Проверяем уникальность номера
    existing = await db.execute(select(Post).where(Post.number == post_data.number))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Пост с таким номером уже существует")
    
    post = Post(
        number=post_data.number,
        name=post_data.name,
        description=post_data.description,
        is_active=post_data.is_active
    )
    
    db.add(post)
    await db.commit()
    await db.refresh(post)
    
    return PostResponse.model_validate(post)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить пост"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять посты")
    
    query = select(Post).where(Post.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    # Проверяем уникальность номера, если он изменяется
    if post_data.number is not None and post_data.number != post.number:
        existing = await db.execute(select(Post).where(Post.number == post_data.number))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Пост с таким номером уже существует")
    
    # Обновляем только переданные поля
    if post_data.number is not None:
        post.number = post_data.number
    if post_data.name is not None:
        post.name = post_data.name
    if post_data.description is not None:
        post.description = post_data.description
    if post_data.is_active is not None:
        post.is_active = post_data.is_active
    
    await db.commit()
    await db.refresh(post)
    
    return PostResponse.model_validate(post)


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить пост"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять посты")
    
    query = select(Post).where(Post.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    await db.delete(post)
    await db.commit()
    
    return None









