"""
API для работы с блокировками (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime, time
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.block import (
    BlockResponse, BlockListResponse,
    BlockCreateRequest, BlockUpdateRequest
)
from shared.database.models import User, Block, Post
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


@router.get("", response_model=BlockListResponse)
async def get_blocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    post_id: Optional[int] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список блокировок.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска (по названию)
        post_id: фильтр по посту
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать блокировки")
    
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
    
    query = select(Block).options(
        selectinload(Block.post)
    )
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.where(Block.name.ilike(search_term))
    
    if post_id is not None:
        query = query.where(Block.post_id == post_id)
    
    # Подсчет общего количества
    count_query = select(func.count(Block.id))
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Block.date, Block.start_time)
    
    result = await tenant_session.execute(query)
    blocks = result.scalars().all()
    
    print(f"📊 Запрос блокировок: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for block in blocks:
        block_dict = {
            "id": block.id,
            "post_id": block.post_id,
            "post_number": None,
            "date": block.date,
            "start_time": block.start_time,
            "end_time": block.end_time,
            "name": block.name,
            "reason": block.reason,
            "created_at": block.created_at,
            "updated_at": block.updated_at,
            "company_id": company_id,
        }
        
        # Добавляем номер поста, если есть
        if block.post:
            block_dict["post_number"] = block.post.number
        
        items.append(BlockResponse.model_validate(block_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{block_id}", response_model=BlockResponse)
async def get_block(
    block_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о блокировке.
    
    Аргументы:
        block_id: ID блокировки
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать блокировки")
    
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
    
    query = select(Block).options(
        selectinload(Block.post)
    ).where(Block.id == block_id)
    
    result = await tenant_session.execute(query)
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    
    print(f"🔍 Запрос блокировки: block_id={block_id}, company_id={company_id}")
    
    # Формируем ответ
    block_dict = {
        "id": block.id,
        "post_id": block.post_id,
        "post_number": None,
        "date": block.date,
        "start_time": block.start_time,
        "end_time": block.end_time,
        "name": block.name,
        "reason": block.reason,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
        "company_id": company_id,
    }
    
    # Добавляем номер поста, если есть
    if block.post:
        block_dict["post_number"] = block.post.number
    
    return BlockResponse.model_validate(block_dict)


@router.post("", response_model=BlockResponse, status_code=201)
async def create_block(
    block_data: BlockCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать новую блокировку.
    
    Аргументы:
        block_data: данные блокировки
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать блокировки")
    
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
    
    # Проверяем существование поста
    post = await tenant_session.execute(
        select(Post).where(Post.id == block_data.post_id)
    ).scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    
    if not post.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Пост '{post.number}' неактивен, нельзя создавать блокировку"
        )
    
    # Валидация времени: start_time должен быть меньше end_time
    if block_data.start_time >= block_data.end_time:
        raise HTTPException(
            status_code=400,
            detail="Время начала блокировки должно быть меньше времени окончания"
        )
    
    # Проверяем пересечение с существующими блокировками для этого поста и даты
    existing_blocks = await tenant_session.execute(
        select(Block).where(
            and_(
                Block.post_id == block_data.post_id,
                Block.date == block_data.date
            )
        )
    ).scalars().all()
    
    for existing_block in existing_blocks:
        # Проверяем пересечение по времени
        if not (block_data.end_time <= existing_block.start_time or block_data.start_time >= existing_block.end_time):
            raise HTTPException(
                status_code=400,
                detail=f"Блокировка пересекается с существующей: '{existing_block.name}' ({existing_block.start_time.strftime('%H:%M')} - {existing_block.end_time.strftime('%H:%M')})"
            )
    
    # Создаем новую блокировку
    block = Block(
        post_id=block_data.post_id,
        date=block_data.date,
        start_time=block_data.start_time,
        end_time=block_data.end_time,
        name=block_data.name,
        reason=block_data.reason,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(block)
    await tenant_session.commit()
    await tenant_session.refresh(block)
    
    print(f"✅ Создана блокировка: name={block_data.name}, date={block_data.date}, time={block_data.start_time} - {block_data.end_time}")
    
    # Отправляем уведомление
    # TODO: Создать Celery задачу для уведомления о новой блокировке
    
    # Формируем ответ
    block_dict = {
        "id": block.id,
        "post_id": block.post_id,
        "post_number": post.number,
        "date": block.date,
        "start_time": block.start_time,
        "end_time": block.end_time,
        "name": block.name,
        "reason": block.reason,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
        "company_id": company_id,
    }
    
    return BlockResponse.model_validate(block_dict)


@router.patch("/{block_id}", response_model=BlockResponse)
async def update_block(
    block_id: int,
    block_data: BlockUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию о блокировке.
    
    Аргументы:
        block_id: ID блокировки
        block_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять блокировки")
    
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
    
    # Проверяем существование блокировки
    query = select(Block).options(
        selectinload(Block.post)
    ).where(Block.id == block_id)
    
    result = await tenant_session.execute(query)
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    
    # Обновляем поля
    update_data = {}
    new_start_time = None
    new_end_time = None
    
    if block_data.post_id is not None:
        # Проверяем существование поста
        new_post = await tenant_session.execute(
            select(Post).where(Post.id == block_data.post_id)
        ).scalar_one_or_none()
        
        if not new_post:
            raise HTTPException(status_code=404, detail="Пост не найден")
        
        if not new_post.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Пост '{new_post.number}' неактивен, нельзя менять блокировку"
            )
        
        block.post_id = block_data.post_id
    
    if block_data.date is not None:
        block.date = block_data.date
        update_data["date"] = block.date
    
    if block_data.start_time is not None:
        new_start_time = block_data.start_time
        block.start_time = block_data.start_time
        update_data["start_time"] = block.start_time
    
    if block_data.end_time is not None:
        new_end_time = block_data.end_time
        block.end_time = block_data.end_time
        update_data["end_time"] = block.end_time
    
    if block_data.name is not None:
        block.name = block_data.name
        update_data["name"] = block.name
    
    if block_data.reason is not None:
        block.reason = block_data.reason
        update_data["reason"] = block.reason
    
    # Валидация времени
    if new_start_time and new_end_time:
        if new_start_time >= new_end_time:
            raise HTTPException(
                status_code=400,
                detail="Время начала блокировки должно быть меньше времени окончания"
            )
    elif new_start_time:
        if new_start_time >= block.end_time:
            raise HTTPException(
                status_code=400,
                detail="Время начала блокировки должно быть меньше времени окончания"
            )
    elif new_end_time:
        if block.start_time >= new_end_time:
            raise HTTPException(
                status_code=400,
                detail="Время начала блокировки должно быть меньше времени окончания"
            )
    
    # Проверяем пересечение с существующими блокировками для этого поста и даты
    # (исключая текущую блокировку)
    existing_blocks = await tenant_session.execute(
        select(Block).where(
            and_(
                Block.post_id == block.post_id,
                Block.date == block.date,
                Block.id != block_id
            )
        )
    ).scalars().all()
    
    for existing_block in existing_blocks:
        # Проверяем пересечение по времени
        if not (block.end_time <= existing_block.start_time or block.start_time >= existing_block.end_time):
            raise HTTPException(
                status_code=400,
                detail=f"Блокировка пересекается с существующей: '{existing_block.name}' ({existing_block.start_time.strftime('%H:%M')} - {existing_block.end_time.strftime('%H:%M')})"
            )
    
    block.updated_at = datetime.utcnow()
    update_data["updated_at"] = block.updated_at
    
    # Выполняем обновление
    await tenant_session.execute(
        select(Block).where(Block.id == block_id).values(**update_data)
    )
    await tenant_session.commit()
    await tenant_session.refresh(block)
    
    print(f"✅ Обновлена блокировка: block_id={block_id}, name={block_data.name if block_data.name else block.name}")
    
    # Формируем ответ
    block_dict = {
        "id": block.id,
        "post_id": block.post_id,
        "post_number": None,
        "date": block.date,
        "start_time": block.start_time,
        "end_time": block.end_time,
        "name": block.name,
        "reason": block.reason,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
        "company_id": company_id,
    }
    
    # Добавляем номер поста, если есть
    if block.post:
        block_dict["post_number"] = block.post.number
    
    return BlockResponse.model_validate(block_dict)


@router.delete("/{block_id}", status_code=204)
async def delete_block(
    block_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить блокировку.
    
    Аргументы:
        block_id: ID блокировки
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять блокировки")
    
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
    
    # Проверяем существование блокировки
    query = select(Block).where(Block.id == block_id)
    result = await tenant_session.execute(query)
    block = result.scalar_one_or_none()
    
    if not block:
        raise HTTPException(status_code=404, detail="Блокировка не найдена")
    
    # Удаляем блокировку
    await tenant_session.execute(
        delete(Block).where(Block.id == block_id)
    )
    await tenant_session.commit()
    
    print(f"✅ Удалена блокировка: block_id={block_id}, name={block.name}")
    
    return None

