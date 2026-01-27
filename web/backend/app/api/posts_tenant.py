"""
API для работы с постами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
import logging
from datetime import datetime
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.deps.tenant import get_tenant_db
from app.schemas.post import (
    PostResponse, PostListResponse,
    PostCreateRequest, PostUpdateRequest
)
from shared.database.models import User, Post, Booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
async def get_posts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список постов.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска (по номеру, названию)
        is_active: фильтр по активности
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать посты")
    
    query = select(Post)
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Post.number.ilike(search_term),
                Post.name.ilike(search_term),
            )
        )
    
    if is_active is not None:
        query = query.where(Post.is_active == is_active)
    
    # Подсчет общего количества
    count_query = select(func.count(Post.id))
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Post.number)
    
    result = await tenant_session.execute(query)
    posts = result.scalars().all()
    
    company_id = getattr(request.state, "company_id", None)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📊 Запрос постов: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for post in posts:
        # Считаем количество записей для поста
        booking_count = await tenant_session.scalar(
            select(func.count(Booking.id)).select_from(Booking).where(Booking.post_id == post.id)
        )
        
        post_dict = {
            "id": post.id,
            "number": post.number,
            "name": post.name,
            "description": post.description,
            "is_active": post.is_active,
            "booking_count": booking_count or 0,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "company_id": company_id,
        }
        items.append(PostResponse.model_validate(post_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о посте.
    
    Аргументы:
        post_id: ID поста
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать посты")

    query = select(Post).where(Post.id == post_id)
    result = await tenant_session.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    company_id = getattr(request.state, "company_id", None)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Запрос поста: post_id={post_id}, company_id={company_id}")
    
    # Считаем количество записей для поста
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.post_id == post.id)
    )
    
    # Формируем ответ
    post_dict = {
        "id": post.id,
        "number": post.number,
        "name": post.name,
        "description": post.description,
        "is_active": post.is_active,
        "booking_count": booking_count or 0,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }
    
    return PostResponse.model_validate(post_dict)


@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать новый пост.
    
    Аргументы:
        post_data: данные поста
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать посты")
    
    # Проверяем и создаем sequence для posts, если его нет
    company_id = getattr(request.state, "company_id", None)
    if company_id:
        from sqlalchemy import text
        schema_name = f"tenant_{company_id}"
        # Проверяем существование sequence
        seq_check = await tenant_session.execute(
            text(
                f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_sequences
                    WHERE schemaname = :schema_name
                    AND sequencename = 'posts_id_seq'
                )
                """
            ),
            {"schema_name": schema_name}
        )
        if not seq_check.scalar():
            # Создаем sequence если его нет
            await tenant_session.execute(
                text(
                    f'CREATE SEQUENCE IF NOT EXISTS "{schema_name}".posts_id_seq '
                    'AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1'
                )
            )
            await tenant_session.execute(
                text(
                    f'ALTER TABLE "{schema_name}".posts '
                    f'ALTER COLUMN id SET DEFAULT nextval(\'"{schema_name}".posts_id_seq\'::regclass)'
                )
            )
            await tenant_session.commit()
    
    # Проверяем, существует ли пост с таким номером
    existing_post = await tenant_session.scalar(
        select(Post).where(Post.number == post_data.number)
    )
    
    if existing_post:
        raise HTTPException(
            status_code=400,
            detail=f"Пост с номером {post_data.number} уже существует"
        )
    
    # Создаем новый пост
    post = Post(
        number=post_data.number,
        name=post_data.name,
        description=post_data.description,
        is_active=post_data.is_active if post_data.is_active is not None else True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(post)
    await tenant_session.commit()
    await tenant_session.refresh(post)
    
    company_id = getattr(request.state, "company_id", None)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Создан пост: number={post.number}, name={post.name}, company_id={company_id}")
    
    # Отправляем уведомление
    # TODO: Создать Celery задачу для уведомления о новом посте
    
    # Формируем ответ
    post_dict = {
        "id": post.id,
        "number": post.number,
        "name": post.name,
        "description": post.description,
        "is_active": post.is_active,
        "booking_count": 0,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }
    
    return PostResponse.model_validate(post_dict)


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию о посте.
    
    Аргументы:
        post_id: ID поста
        post_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять посты")

    # Проверяем существование поста
    query = select(Post).where(Post.id == post_id)
    result = await tenant_session.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    # Проверяем, используется ли пост в записях
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.post_id == post.id)
    )
    
    # Обновляем поля
    if post_data.number is not None:
        # Проверяем, что номер не занят
        if post_data.number != post.number:
            # Сначала выполняем запрос, затем вызываем scalar_one_or_none()
            existing_result = await tenant_session.execute(
                select(Post).where(Post.number == post_data.number)
            )
            existing_post = existing_result.scalar_one_or_none()
            if existing_post:
                raise HTTPException(
                    status_code=400,
                    detail=f"Пост с номером {post_data.number} уже существует"
                )
        post.number = post_data.number
    if post_data.name is not None:
        post.name = post_data.name
    if post_data.description is not None:
        post.description = post_data.description
    if post_data.is_active is not None:
        # При дезактивации поста проверяем, нет ли активных записей
        if post_data.is_active == False and booking_count and booking_count > 0:
            active_bookings = await tenant_session.scalar(
                select(func.count(Booking.id)).select_from(Booking).where(
                    and_(
                        Booking.post_id == post.id,
                        Booking.status.in_(["new", "confirmed"])
                    )
                )
            )
            if active_bookings and active_bookings > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Невозможно деактивировать пост '{post.number}', так как с ним связаны {active_bookings} активных записей"
                )
        post.is_active = post_data.is_active
    
    post.updated_at = datetime.utcnow()
    await tenant_session.commit()
    await tenant_session.refresh(post)
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Обновлен пост: post_id={post_id}, number={post.number}, company_id={company_id}")
    
    # Формируем ответ
    post_dict = {
        "id": post.id,
        "number": post.number,
        "name": post.name,
        "description": post.description,
        "is_active": post.is_active,
        "booking_count": booking_count or 0,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }
    
    return PostResponse.model_validate(post_dict)


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить пост.
    
    Аргументы:
        post_id: ID поста
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять посты")
    # Проверяем существование поста
    query = select(Post).where(Post.id == post_id)
    result = await tenant_session.execute(query)
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    # Проверяем, используются ли записи с этим постом
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.post_id == post.id)
    )
    
    if booking_count and booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить пост '{post.number}', так как с ним связаны {booking_count} записей"
        )
    
    # Удаляем пост
    await tenant_session.execute(
        delete(Post).where(Post.id == post_id)
    )
    await tenant_session.commit()
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Удален пост: post_id={post_id}, number={post.number}, company_id={company_id}")
    
    return None

