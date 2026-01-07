"""
API для работы с пользователями (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime, date
from typing import Optional, Annotated, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.user import UserResponse, UserCreateRequest, UserUpdateRequest
from shared.database.models import User, Client, Booking
from app.services.tenant_service import get_tenant_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список пользователей"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")
    
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
    
    query = select(User).options(
        selectinload(User.client),
    )
    
    # Фильтры
    conditions = []
    if search:
        search_term = f"%{search}%"
        query = query.join(User).where(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.phone.ilike(search_term),
                User.telegram_id.ilike(search_term),
            )
        )
    
    # Подсчет общего количества
    count_query = select(func.count(User.id))
    if search:
        count_query = count_query.join(User).where(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.phone.ilike(search_term),
                User.telegram_id.ilike(search_term),
            )
        )
    
    # Пагинация
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация и сортировка
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(User.created_at.desc())
    
    result = await tenant_session.execute(query)
    users = result.scalars().all()
    
    print(f"📊 Запрос пользователей: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for user in users:
        # Блокировка при истекшей подписке (для компаний с подпиской)
        is_blocked = False
        if company_id and not current_user.is_master:
            # TODO: Проверять статус подписки компании
            # Если подписка истекла - блокируем некоторых действий
            pass
        
        user_dict = {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_admin": user.is_admin,
            "is_master": user.is_master,
            "is_blocked": is_blocked,
            "is_client": user.is_client,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "client": None,  # Временно, без вложенного объекта
            "blocked_at": None,
        }
        
        # Добавляем информацию о клиенте, если есть
        if user.is_client:
            async for client_session in tenant_session.execute(
                select(Client).where(Client.id == user.id)
            ):
                client = await client_session.scalar_one_or_none()
                if client:
                    user_dict["client"] = {
                        "id": client.id,
                        "full_name": client.full_name,
                        "phone": client.phone,
                        "car_brand": client.car_brand,
                        "car_model": client.car_model,
                    }
        
        items.append(UserResponse.model_validate(user_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о пользователе"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")
    
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
    
    query = select(User).options(
        selectinload(User.client),
    ).where(User.id == user_id)
    
    result = await tenant_session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    print(f"🔍 Запрос пользователя: user_id={user_id}, company_id={company_id}")
    
    # Формируем ответ
    user_dict = {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_admin": user.is_admin,
        "is_master": user.is_master,
        "is_client": user.is_client,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "client": None,  # Временно, без вложенного объекта
    }
    
    # Добавляем информацию о клиенте, если есть
    if user.is_client:
        async for session in tenant_session.execute(
                select(Client).where(Client.id == user.id)
            ):
                client = await session.scalar_one_or_none()
                if client:
                    user_dict["client"] = {
                        "id": client.id,
                        "full_name": client.full_name,
                        "phone": client.phone,
                        "car_brand": client.car_brand,
                        "car_model": client.car_model,
                    }
    
    return UserResponse.model_validate(user_dict)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать нового пользователя"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать пользователей")
    
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
    
    # Проверяем, существует ли пользователь с таким telegram_id
    existing_user = await tenant_session.execute(
        select(User).where(User.telegram_id == user_data.telegram_id)
    ).scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail=f"Пользователь с telegram_id {user_data.telegram_id} уже существует")
    
    # Проверяем, существует ли пользователь с таким username
    existing_username = await tenant_session.execute(
        select(User).where(User.username == user_data.username)
    ).scalar_one_or_none()
    
    if existing_username:
        raise HTTPException(status_code=400, detail=f"Пользователь с username {user_data.username} уже существует")
    
    # Создаем нового пользователя
    user = User(
        telegram_id=user_data.telegram_id,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        is_admin=False,
        is_master=False,
        is_client=True,
        is_blocked=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(user)
    await tenant_session.commit()
    await tenant_session.refresh(user)
    
    print(f"✅ Создан пользователь: telegram_id={user_data.telegram_id}, username={user_data.username}")
    
    # Формируем ответ
    user_dict = {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_admin": user.is_admin,
        "is_master": user.is_master,
        "is_client": user.is_client,
        "is_blocked": user.is_blocked,
        "is_client": True,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
    
    return UserResponse.model_validate(user_dict)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить информацию о пользователе"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять пользователей")
    
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
    
    query = select(User).where(User.id == user_id)
    result = await tenant_session.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Обновляем поля, которые указаны в запросе
    update_data = {}
    if user_data.first_name is not None:
        update_data["first_name"] = user_data.first_name
    if user_data.last_name is not None:
        update_data["last_name"] = user_data.last_name
    if user_data.phone is not None:
        update_data["phone"] = user_data.phone
    if user_data.is_admin is not None:
        update_data["is_admin"] = user_data.is_admin
    if user_data.is_master is not None:
        update_data["is_master"] = user_data.is_master
    if user_data.is_client is not None:
        update_data["is_client"] = user_data.is_client
    
    # Обновляем timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Выполняем обновление
    result = await tenant_session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Применяем обновления
    for key, value in update_data.items():
        setattr(user, key, value)
    
    user.updated_at = update_data["updated_at"]
    
    await tenant_session.commit()
    await tenant_session.refresh(user)
    
    print(f"✅ Обновлен пользователь: user_id={user_id}, company_id={company_id}")
    
    # Формируем ответ
    user_dict = {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_admin": user.is_admin,
        "is_master": user.is_master,
        "is_client": user.is_client,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "client": None,
    }
    
    return UserResponse.model_validate(user_dict)

