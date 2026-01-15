"""
API для работы с пользователями (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

Обеспечивает мульти-тенантность:
- Поддержка company_id для переключения на tenant схемы
- Использование get_tenant_session() для работы с tenant сессиями
- Изоляция данных между компаниями
"""
from datetime import datetime
from hashlib import sha256
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.deps.tenant import get_tenant_db
from app.api.auth import get_current_user
from app.schemas.user import UserResponse, UserListResponse, UserCreateRequest
from shared.database.models import User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def get_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Получить список пользователей"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")

    # Используем text() для прямых SQL запросов, так как структура таблицы отличается от модели
    # В tenant схеме users имеет: id, username, email, password_hash, full_name, phone, role, telegram_id, is_active, created_at, updated_at
    
    # Подсчет общего количества
    if search:
        search_term = f"%{search}%"
        count_query = text("""
            SELECT COUNT(*) FROM users
            WHERE username ILIKE :search
               OR phone ILIKE :search
               OR CAST(telegram_id AS TEXT) ILIKE :search
               OR full_name ILIKE :search
        """)
        count_result = await tenant_session.execute(count_query, {"search": search_term})
        total = count_result.scalar() or 0
    else:
        count_result = await tenant_session.execute(text('SELECT COUNT(*) FROM users'))
        total = count_result.scalar() or 0
    
    # Получаем пользователей с пагинацией
    offset = (page - 1) * page_size
    if search:
        search_term = f"%{search}%"
        users_query = text("""
            SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            FROM users
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
        users_query = text("""
            SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        result = await tenant_session.execute(
            users_query,
            {"limit": page_size, "offset": offset}
        )
    
    users_rows = result.fetchall()
    
    company_id = getattr(request.state, "company_id", None)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📊 Запрос пользователей: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
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
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о пользователе"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать пользователей")

    result = await tenant_session.execute(
        text(
            """
            SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            FROM users
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    (
        user_id_db,
        telegram_id,
        username,
        full_name,
        phone,
        role,
        is_active,
        created_at,
        updated_at,
    ) = row

    name_parts = (full_name or "").split(maxsplit=1) if full_name else ["", ""]
    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = name_parts[1] if len(name_parts) > 1 else None

    company_id = getattr(request.state, "company_id", None)
    logger.info(f"🔍 Запрос пользователя: user_id={user_id}, company_id={company_id}")

    return UserResponse.model_validate(
        {
            "id": user_id_db,
            "telegram_id": telegram_id or 0,
            "username": username,
            "first_name": first_name or None,
            "last_name": last_name or None,
            "phone": phone,
            "is_admin": role == "admin",
            "is_master": role == "master",
            "is_blocked": not bool(is_active),
            "created_at": created_at,
            "updated_at": updated_at or created_at,
        }
    )


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Создать нового пользователя"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать пользователей")

    # В tenant таблице users есть NOT NULL password_hash — генерируем служебное значение.
    password_hash = sha256(f"tenant_user:{user_data.telegram_id}:{datetime.utcnow().isoformat()}".encode("utf-8")).hexdigest()

    full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip() or None

    if user_data.is_admin:
        role = "admin"
    elif user_data.is_master:
        role = "master"
    else:
        role = "client"

    is_active = not user_data.is_blocked

    # Проверяем уникальность telegram_id
    existing_tg = await tenant_session.execute(
        text("SELECT 1 FROM users WHERE telegram_id = :telegram_id LIMIT 1"),
        {"telegram_id": user_data.telegram_id},
    )
    if existing_tg.fetchone():
        raise HTTPException(status_code=400, detail=f"Пользователь с telegram_id {user_data.telegram_id} уже существует")

    # Проверяем уникальность username (если указан)
    if user_data.username:
        existing_username = await tenant_session.execute(
            text("SELECT 1 FROM users WHERE username = :username LIMIT 1"),
            {"username": user_data.username},
        )
        if existing_username.fetchone():
            raise HTTPException(status_code=400, detail=f"Пользователь с username {user_data.username} уже существует")

    now = datetime.utcnow()
    insert_result = await tenant_session.execute(
        text(
            """
            INSERT INTO users (telegram_id, username, full_name, phone, role, is_active, password_hash, created_at, updated_at)
            VALUES (:telegram_id, :username, :full_name, :phone, :role, :is_active, :password_hash, :created_at, :updated_at)
            RETURNING id
            """
        ),
        {
            "telegram_id": user_data.telegram_id,
            "username": user_data.username,
            "full_name": full_name,
            "phone": user_data.phone,
            "role": role,
            "is_active": is_active,
            "password_hash": password_hash,
            "created_at": now,
            "updated_at": now,
        },
    )
    await tenant_session.commit()
    new_id = insert_result.scalar_one()

    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Создан пользователь: id={new_id}, telegram_id={user_data.telegram_id}, company_id={company_id}")

    return UserResponse.model_validate(
        {
            "id": new_id,
            "telegram_id": user_data.telegram_id,
            "username": user_data.username,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "is_admin": role == "admin",
            "is_master": role == "master",
            "is_blocked": not is_active,
            "created_at": now,
            "updated_at": now,
        }
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    user_data: dict = Body(...),
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить информацию о пользователе"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять пользователей")

    exists = await tenant_session.execute(text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id})
    if not exists.fetchone():
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    update_fields: dict[str, object] = {}

    if "username" in user_data and user_data["username"] is not None:
        update_fields["username"] = user_data["username"]
    if "phone" in user_data and user_data["phone"] is not None:
        update_fields["phone"] = user_data["phone"]

    if "first_name" in user_data or "last_name" in user_data:
        first_name = (user_data.get("first_name") or "").strip()
        last_name = (user_data.get("last_name") or "").strip()
        update_fields["full_name"] = f"{first_name} {last_name}".strip() or None

    is_admin = user_data.get("is_admin")
    is_master = user_data.get("is_master")
    if is_admin is not None or is_master is not None:
        if bool(is_admin):
            update_fields["role"] = "admin"
        elif bool(is_master):
            update_fields["role"] = "master"
        else:
            update_fields["role"] = "client"

    if "is_blocked" in user_data and user_data["is_blocked"] is not None:
        update_fields["is_active"] = not bool(user_data["is_blocked"])

    update_fields["updated_at"] = datetime.utcnow()

    set_parts = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
    await tenant_session.execute(
        text(f"UPDATE users SET {set_parts} WHERE id = :id"),
        {"id": user_id, **update_fields},
    )
    await tenant_session.commit()

    # Возвращаем актуальную строку
    result = await tenant_session.execute(
        text(
            """
            SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            FROM users
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    (
        user_id_db,
        telegram_id,
        username,
        full_name,
        phone,
        role,
        is_active,
        created_at,
        updated_at,
    ) = row

    name_parts = (full_name or "").split(maxsplit=1) if full_name else ["", ""]
    first_name = name_parts[0] if len(name_parts) > 0 else None
    last_name = name_parts[1] if len(name_parts) > 1 else None

    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Обновлен пользователь: user_id={user_id}, company_id={company_id}")

    return UserResponse.model_validate(
        {
            "id": user_id_db,
            "telegram_id": telegram_id or 0,
            "username": username,
            "first_name": first_name or None,
            "last_name": last_name or None,
            "phone": phone,
            "is_admin": role == "admin",
            "is_master": role == "master",
            "is_blocked": not bool(is_active),
            "created_at": created_at,
            "updated_at": updated_at or created_at,
        }
    )

