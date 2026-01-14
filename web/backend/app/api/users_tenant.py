"""
API для работы с пользователями (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime, date
from typing import Optional, Annotated, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from jose import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.user import UserResponse, UserListResponse, UserCreateRequest
from shared.database.models import User, Client, Booking
from app.services.tenant_service import get_tenant_service
from app.config import settings

router = APIRouter(prefix="/api/users", tags=["users"])
security = HTTPBearer()


async def get_company_id_from_token(request: Request) -> Optional[int]:
    """Получить company_id из JWT токена"""
    try:
        authorization: HTTPAuthorizationCredentials = await security(request)
        token = authorization.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("company_id")
    except:
        return None


@router.get("", response_model=UserListResponse)
async def get_users(
    request: Request,
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
    
    # Получаем company_id из токена, если не передан в query параметрах
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден. Необходимо указать company_id в query параметрах или войти как пользователь компании.")
    
    # Устанавливаем search_path для tenant схемы
    schema_name = f"tenant_{company_id}"
    await db.execute(text(f'SET search_path TO "{schema_name}", public'))
    # Устанавливаем search_path для текущей сессии
    await db.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    tenant_session = db
    
    # Используем text() для прямых SQL запросов, так как структура таблицы отличается от модели
    # В tenant схеме users имеет: id, username, email, password_hash, full_name, phone, role, telegram_id, is_active, created_at, updated_at
    
    # Подсчет общего количества
    if search:
        search_term = f"%{search}%"
        count_query = text(f"""
            SELECT COUNT(*) FROM "{schema_name}".users
            WHERE username ILIKE :search
               OR phone ILIKE :search
               OR CAST(telegram_id AS TEXT) ILIKE :search
               OR full_name ILIKE :search
        """)
        count_result = await tenant_session.execute(count_query, {"search": search_term})
        total = count_result.scalar() or 0
    else:
        count_result = await tenant_session.execute(text(f'SELECT COUNT(*) FROM "{schema_name}".users'))
        total = count_result.scalar() or 0
    
    # Получаем пользователей с пагинацией
    offset = (page - 1) * page_size
    if search:
        search_term = f"%{search}%"
        users_query = text(f"""
            SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            FROM "{schema_name}".users
            WHERE username ILIKE :search
               OR phone ILIKE :search
               OR CAST(telegram_id AS TEXT) ILIKE :search
               OR full_name ILIKE :search
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await tenant_session.execute(
            users_query,
            {"search": search_term, "limit": page_size, "offset": offset}
        )
    else:
        users_query = text(f"""
            SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            FROM "{schema_name}".users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await tenant_session.execute(
            users_query,
            {"limit": page_size, "offset": offset}
        )
    
    users_rows = result.fetchall()
    
    print(f"📊 Запрос пользователей: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for row in users_rows:
        user_id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at = row
        
        # Разбиваем full_name на first_name и last_name
        name_parts = (full_name or '').split(maxsplit=1) if full_name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else None
        last_name = name_parts[1] if len(name_parts) > 1 else None
        
        # Определяем is_admin и is_master из role
        is_admin = role == 'admin'
        is_master = role == 'master'
        
        user_dict = {
            "id": user_id,
            "telegram_id": telegram_id or 0,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "is_admin": is_admin,
            "is_master": is_master,
            "is_blocked": not is_active,
            "created_at": created_at,
            "updated_at": updated_at or created_at,
        }
        
        items.append(UserResponse.model_validate(user_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
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
    # Объединяем first_name и last_name в full_name
    full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip()
    
    user = User(
        telegram_id=user_data.telegram_id,
        username=user_data.username or '',
        full_name=full_name or None,
        phone=user_data.phone,
        role='client',
        is_active=True,
    )
    
    tenant_session.add(user)
    await tenant_session.commit()
    await tenant_session.refresh(user)
    
    print(f"✅ Создан пользователь: telegram_id={user_data.telegram_id}, username={user_data.username}")
    
    # Формируем ответ
    full_name_db = getattr(user, 'full_name', None) or ''
    name_parts = full_name_db.split(maxsplit=1) if full_name_db else ['', '']
    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = name_parts[1] if len(name_parts) > 1 else None
    role = getattr(user, 'role', 'client')
    
    user_dict = {
        "id": user.id,
        "telegram_id": getattr(user, 'telegram_id', 0) or 0,
        "username": getattr(user, 'username', None),
        "first_name": first_name,
        "last_name": last_name,
        "phone": getattr(user, 'phone', None),
        "is_admin": role == 'admin',
        "is_master": role == 'master',
        "is_blocked": not getattr(user, 'is_active', True),
        "created_at": getattr(user, 'created_at', datetime.now()),
        "updated_at": getattr(user, 'updated_at', datetime.now()),
    }
    
    return UserResponse.model_validate(user_dict)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: dict,
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
    if "first_name" in user_data and user_data["first_name"] is not None:
        # Объединяем first_name и last_name в full_name
        last_name = user_data.get("last_name", "")
        full_name = f"{user_data['first_name']} {last_name}".strip()
        update_data["full_name"] = full_name
    if "phone" in user_data and user_data["phone"] is not None:
        update_data["phone"] = user_data["phone"]
    if "is_admin" in user_data and user_data["is_admin"] is not None:
        update_data["role"] = "admin" if user_data["is_admin"] else "client"
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
    # Получаем full_name из БД, если есть
    full_name = getattr(user, 'full_name', None) or ''
    # Разбиваем full_name на first_name и last_name
    name_parts = full_name.split(maxsplit=1) if full_name else ['', '']
    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    # Определяем is_admin и is_master из role
    role = getattr(user, 'role', 'client')
    is_admin = role == 'admin'
    is_master = role == 'master'
    
    user_dict = {
        "id": user.id,
        "telegram_id": getattr(user, 'telegram_id', 0) or 0,
        "username": getattr(user, 'username', None),
        "first_name": first_name,
        "last_name": last_name,
        "phone": getattr(user, 'phone', None),
        "is_admin": is_admin,
        "is_master": is_master,
        "is_blocked": not getattr(user, 'is_active', True),
        "created_at": getattr(user, 'created_at', datetime.now()),
        "updated_at": getattr(user, 'updated_at', datetime.now()),
    }
    
    return UserResponse.model_validate(user_dict)

