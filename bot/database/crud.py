"""CRUD операции для работы с БД"""
from datetime import date, time, datetime, timedelta
from typing import Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.orm import selectinload

from shared.database.models import (
    User, Client, Service, Booking, Master, Post
)
from bot.config import ADMIN_IDS


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int, company_id: Optional[int] = None) -> Optional[User]:
    """
    Получить пользователя по Telegram ID.
    
    В tenant схеме User имеет только: id, username, email, password_hash, full_name, phone, role, telegram_id, is_active, created_at, updated_at
    Используем прямой SQL запрос, чтобы избежать проблем с моделью.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from sqlalchemy import text
    
    # Если company_id не указан, пытаемся получить его из текущего search_path
    if not company_id:
        # Пытаемся определить схему из текущего search_path
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                # Извлекаем company_id из search_path
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    logger.info(f"🔍 Определен company_id={company_id} из search_path: {search_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔍 Получаем пользователя по telegram_id={telegram_id} из схемы {schema_name}")
        
        # Устанавливаем search_path
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Используем прямой SQL запрос
        result = await session.execute(
            text(f"""
                SELECT id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
                FROM "{schema_name}".users
                WHERE telegram_id = :telegram_id
            """),
            {"telegram_id": telegram_id}
        )
        row = result.fetchone()
        if row:
            # Создаем объект User с правильными полями
            # Используем type() для создания экземпляра без вызова __init__
            user = type('User', (), {})()
            user.id = row[0]
            user.telegram_id = row[1]
            user.username = row[2] or ''
            user.full_name = row[3]
            user.phone = row[4]
            user.role = row[5] or 'client'
            user.is_active = row[6] if row[6] is not None else True
            user.created_at = row[7]
            user.updated_at = row[8]
            # Добавляем совместимые атрибуты для старого кода
            user.is_admin = (user.role == 'admin')
            user.is_master = (user.role == 'master')
            user.is_blocked = (not user.is_active)
            # Для совместимости с кодом, который использует first_name/last_name
            if user.full_name:
                name_parts = user.full_name.split(maxsplit=1)
                user.first_name = name_parts[0] if len(name_parts) > 0 else None
                user.last_name = name_parts[1] if len(name_parts) > 1 else None
            else:
                user.first_name = None
                user.last_name = None
            return user
        return None
    else:
        # Если company_id не указан и не определен, используем обычный запрос
        # Это может не работать для tenant схемы, но попробуем
        logger.warning("⚠️ company_id не указан для get_user_by_telegram_id, используем обычный запрос")
        try:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователя: {e}", exc_info=True)
            return None


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    company_id: Optional[int] = None,
) -> User:
    """
    Создать пользователя.
    
    Args:
        session: Сессия БД
        telegram_id: Telegram ID пользователя
        username: Имя пользователя
        first_name: Имя (объединяется с last_name в full_name)
        last_name: Фамилия (объединяется с first_name в full_name)
        phone: Телефон
        company_id: ID компании (для проверки прав админа)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # В tenant схеме User имеет только full_name, а не first_name/last_name
    # Объединяем first_name и last_name в full_name
    full_name = None
    if first_name or last_name:
        name_parts = []
        if first_name:
            name_parts.append(first_name)
        if last_name:
            name_parts.append(last_name)
        full_name = " ".join(name_parts).strip() if name_parts else None
    # Проверяем, является ли пользователь админом компании
    is_admin = False
    if company_id:
        # Запрашиваем админов компании из public схемы
        try:
            result = await session.execute(
                text("""
                    SELECT admin_telegram_id, telegram_admin_ids
                    FROM public.companies
                    WHERE id = :company_id
                """),
                {"company_id": company_id}
            )
            row = result.fetchone()
            if row:
                admin_telegram_id = row[0]
                telegram_admin_ids = row[1] or []
                
                # Проверяем, является ли пользователь админом
                if admin_telegram_id == telegram_id:
                    is_admin = True
                elif telegram_id in telegram_admin_ids:
                    is_admin = True
        except Exception as e:
            # Если не удалось проверить, используем глобальный список как fallback
            is_admin = telegram_id in ADMIN_IDS
    else:
        # Если company_id не передан, используем глобальный список
        is_admin = telegram_id in ADMIN_IDS
    
    # В tenant схеме User имеет только full_name, role, is_active
    # Объединяем first_name и last_name в full_name
    full_name = None
    if first_name or last_name:
        name_parts = []
        if first_name:
            name_parts.append(first_name)
        if last_name:
            name_parts.append(last_name)
        full_name = " ".join(name_parts).strip() if name_parts else None
    
    # Используем role вместо is_admin/is_master
    role = 'admin' if is_admin else 'client'
    
    # В tenant схеме нужно использовать прямой SQL, так как модель User не соответствует структуре таблицы
    if company_id:
        from sqlalchemy import text
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Используем прямой SQL для создания пользователя
        # Для пользователей из Telegram бота password_hash не нужен, но поле обязательное
        # Используем пустую строку или генерируем случайный хеш
        import hashlib
        import secrets
        # Генерируем случайный пароль и хешируем его (для пользователей из бота пароль не используется)
        random_password = secrets.token_urlsafe(32)
        password_hash = hashlib.sha256(random_password.encode()).hexdigest()
        
        result = await session.execute(
            text(f"""
                INSERT INTO "{schema_name}".users (telegram_id, username, password_hash, full_name, phone, role, is_active, created_at, updated_at)
                VALUES (:telegram_id, :username, :password_hash, :full_name, :phone, :role, :is_active, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id, telegram_id, username, full_name, phone, role, is_active, created_at, updated_at
            """),
            {
                "telegram_id": telegram_id,
                "username": username or '',
                "password_hash": password_hash,
                "full_name": full_name,
                "phone": phone,
                "role": role,
                "is_active": True
            }
        )
        row = result.fetchone()
        await session.commit()
        
        if row:
            # Создаем объект User с правильными полями
            user = type('User', (), {})()
            user.id = row[0]
            user.telegram_id = row[1]
            user.username = row[2] or ''
            user.full_name = row[3]
            user.phone = row[4]
            user.role = row[5] or 'client'
            user.is_active = row[6] if row[6] is not None else True
            user.created_at = row[7]
            user.updated_at = row[8]
            # Добавляем совместимые атрибуты для старого кода
            user.is_admin = (user.role == 'admin')
            user.is_master = (user.role == 'master')
            user.is_blocked = (not user.is_active)
            # Для совместимости с кодом, который использует first_name/last_name
            if user.full_name:
                name_parts = user.full_name.split(maxsplit=1)
                user.first_name = name_parts[0] if len(name_parts) > 0 else None
                user.last_name = name_parts[1] if len(name_parts) > 1 else None
            else:
                user.first_name = None
                user.last_name = None
            return user
        return None
    else:
        # Если company_id не указан, используем обычный способ (может не работать)
        logger.warning("⚠️ company_id не указан для create_user, используем обычный способ")
        user = User(
            telegram_id=telegram_id,
            username=username or '',
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            is_admin=is_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    company_id: Optional[int] = None,
) -> User:
    """
    Получить или создать пользователя.
    
    Args:
        session: Сессия БД
        telegram_id: Telegram ID пользователя
        username: Имя пользователя
        first_name: Имя
        last_name: Фамилия
        company_id: ID компании (для проверки прав админа)
    """
    # Устанавливаем search_path для tenant схемы, если указан company_id
    if company_id:
        from sqlalchemy import text
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    user = await get_user_by_telegram_id(session, telegram_id, company_id=company_id)
    if not user:
        user = await create_user(session, telegram_id, username, first_name, last_name, company_id=company_id)
    else:
        # Обновить данные если изменились
        if company_id:
            from sqlalchemy import text
            schema_name = f"tenant_{company_id}"
            
            # Объединяем first_name и last_name в full_name
            new_full_name = None
            if first_name or last_name:
                name_parts = []
                if first_name:
                    name_parts.append(first_name)
                if last_name:
                    name_parts.append(last_name)
                new_full_name = " ".join(name_parts).strip() if name_parts else None
            
            # Формируем UPDATE запрос
            update_fields = []
            update_params = {"telegram_id": telegram_id}
            
            if username and getattr(user, 'username', None) != username:
                update_fields.append("username = :username")
                update_params["username"] = username or ''
            
            if new_full_name and getattr(user, 'full_name', None) != new_full_name:
                update_fields.append("full_name = :full_name")
                update_params["full_name"] = new_full_name
            
            # Обновляем права админа если company_id передан
            new_role = getattr(user, 'role', 'client')
            try:
                result = await session.execute(
                    text("""
                        SELECT admin_telegram_id, telegram_admin_ids
                        FROM public.companies
                        WHERE id = :company_id
                    """),
                    {"company_id": company_id}
                )
                row = result.fetchone()
                if row:
                    admin_telegram_id = row[0]
                    telegram_admin_ids = row[1] or []
                    
                    # Проверяем, является ли пользователь админом
                    should_be_admin = False
                    if admin_telegram_id == telegram_id:
                        should_be_admin = True
                    elif telegram_id in telegram_admin_ids:
                        should_be_admin = True
                    
                    # Обновляем role если изменилось
                    new_role = 'admin' if should_be_admin else 'client'
                    current_role = getattr(user, 'role', 'client')
                    if current_role != new_role:
                        update_fields.append("role = :role")
                        update_params["role"] = new_role
            except Exception:
                # Если не удалось проверить, оставляем как есть
                pass
            
            # Выполняем UPDATE если есть изменения
            if update_fields:
                update_sql = f"""
                    UPDATE "{schema_name}".users
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = :telegram_id
                """
                await session.execute(text(update_sql), update_params)
                await session.commit()
                
                # Обновляем объект user
                updated_user = await get_user_by_telegram_id(session, telegram_id, company_id=company_id)
                if updated_user:
                    user = updated_user
        else:
            # Если company_id не указан, используем обычный способ обновления
            if username and user.username != username:
                user.username = username
            await session.commit()
            await session.refresh(user)
    return user


async def get_client_by_user_id(session: AsyncSession, user_id: int, company_id: Optional[int] = None) -> Optional[Client]:
    """Получить клиента по user_id"""
    import logging
    logger = logging.getLogger(__name__)
    
    from sqlalchemy import text
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔍 Получаем клиента по user_id={user_id} из схемы {schema_name}")
        
        # Устанавливаем search_path
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Используем прямой SQL запрос (в tenant схеме clients не имеет total_visits и total_amount)
        result = await session.execute(
            text(f"""
                SELECT id, user_id, full_name, phone, created_at, updated_at
                FROM "{schema_name}".clients
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
        row = result.fetchone()
        if row:
            # Создаем объект Client с правильными полями
            client = type('Client', (), {})()
            client.id = row[0]
            client.user_id = row[1]
            client.full_name = row[2]
            client.phone = row[3]
            client.created_at = row[4]
            client.updated_at = row[5]
            # Добавляем совместимые атрибуты для старого кода
            client.total_visits = 0
            client.total_amount = 0
            return client
        return None
    else:
        # Если company_id не указан, возвращаем None
        logger.error("❌ company_id обязателен для get_client_by_user_id в tenant схеме!")
        return None


async def get_all_clients(session: AsyncSession, company_id: Optional[int] = None) -> List[Client]:
    """Получить список всех клиентов"""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if not company_id:
        logger.error("❌ company_id обязателен для get_all_clients в tenant схеме!")
        return []
    
    schema_name = f"tenant_{company_id}"
    logger.info(f"🔍 Получаем список клиентов из схемы {schema_name}")
    
    # Устанавливаем search_path
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    # Используем прямой SQL запрос
    result = await session.execute(
        text('SELECT id, user_id, full_name, phone, created_at, updated_at FROM clients ORDER BY full_name')
    )
    rows = result.fetchall()
    
    # Преобразуем в объекты Client
    clients = []
    for row in rows:
        client = type('Client', (), {})()
        client.id = row[0]
        client.user_id = row[1]
        client.full_name = row[2]
        client.phone = row[3]
        client.created_at = row[4]
        client.updated_at = row[5]
        clients.append(client)
    
    logger.info(f"✅ Найдено клиентов: {len(clients)}")
    return clients


async def create_client(
    session: AsyncSession,
    user_id: int,
    full_name: str,
    phone: str,
    company_id: Optional[int] = None,
) -> Client:
    """Создать клиента"""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text
    from datetime import datetime
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if not company_id:
        logger.error("❌ company_id обязателен для create_client в tenant схеме!")
        raise ValueError("company_id обязателен для create_client в tenant схеме!")
    
    schema_name = f"tenant_{company_id}"
    logger.info(f"🔍 Создаем клиента для user_id={user_id} в схеме {schema_name}")
    
    # Устанавливаем search_path
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    # Используем прямой SQL INSERT (в tenant схеме clients не имеет total_visits и total_amount)
    now = datetime.utcnow()
    result = await session.execute(
        text(f"""
            INSERT INTO "{schema_name}".clients (user_id, full_name, phone, created_at, updated_at)
            VALUES (:user_id, :full_name, :phone, :created_at, :updated_at)
            RETURNING id, user_id, full_name, phone, created_at, updated_at
        """),
        {
            "user_id": user_id,
            "full_name": full_name,
            "phone": phone,
            "created_at": now,
            "updated_at": now,
        }
    )
    row = result.fetchone()
    if row:
        # Создаем объект Client с правильными полями
        client = type('Client', (), {})()
        client.id = row[0]
        client.user_id = row[1]
        client.full_name = row[2]
        client.phone = row[3]
        client.created_at = row[4]
        client.updated_at = row[5]
        # Добавляем совместимые атрибуты для старого кода
        client.total_visits = 0
        client.total_amount = 0
        await session.commit()
        logger.info(f"✅ Клиент создан: id={client.id}, full_name={client.full_name}, phone={client.phone}")
        return client
    else:
        await session.rollback()
        raise Exception("Не удалось создать клиента")


async def get_or_create_client(
    session: AsyncSession,
    user_id: int,
    full_name: str,
    phone: str,
    company_id: Optional[int] = None,
) -> Client:
    """Получить или создать клиента, обновляя full_name и phone если клиент уже существует"""
    import logging
    logger = logging.getLogger(__name__)
    from datetime import datetime
    from sqlalchemy import text
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if not company_id:
        logger.error("❌ company_id обязателен для get_or_create_client в tenant схеме!")
        raise ValueError("company_id обязателен для get_or_create_client в tenant схеме!")
    
    schema_name = f"tenant_{company_id}"
    
    # Устанавливаем search_path
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    client = await get_client_by_user_id(session, user_id, company_id=company_id)
    if not client:
        # Создаем нового клиента
        client = await create_client(session, user_id, full_name, phone, company_id=company_id)
        logger.info(f"✅ Создан новый клиент: id={client.id}, full_name={full_name}, phone={phone}")
    else:
        # Обновляем full_name и phone если они изменились
        needs_update = False
        update_fields = []
        update_params = {"user_id": user_id, "updated_at": datetime.utcnow()}
        
        if client.full_name != full_name:
            update_fields.append("full_name = :full_name")
            update_params["full_name"] = full_name
            needs_update = True
            logger.info(f"📝 Обновляем full_name: {client.full_name} -> {full_name}")
        
        if client.phone != phone:
            update_fields.append("phone = :phone")
            update_params["phone"] = phone
            needs_update = True
            logger.info(f"📝 Обновляем phone: {client.phone} -> {phone}")
        
        if needs_update:
            await session.execute(
                text(f"""
                    UPDATE "{schema_name}".clients
                    SET {', '.join(update_fields)}, updated_at = :updated_at
                    WHERE user_id = :user_id
                """),
                update_params
            )
            await session.commit()
            logger.info(f"✅ Клиент обновлен: id={client.id}, full_name={full_name}, phone={phone}")
            
            # Обновляем объект client
            client.full_name = full_name
            client.phone = phone
    
    return client


async def update_client_car_brand(
    session: AsyncSession,
    client_id: int,
    car_brand: Optional[str] = None,
) -> Optional[Client]:
    """Обновить марку автомобиля клиента"""
    from sqlalchemy import update
    from shared.database.models import Client
    
    # Если марка указана и она отличается от текущей, обновляем
    if car_brand and car_brand.strip():
        car_brand_clean = car_brand.strip()
        
        # Получаем текущего клиента
        result = await session.execute(
            select(Client).where(Client.id == client_id)
        )
        client = result.scalar_one_or_none()
        
        if client:
            # Если у клиента нет марки или она отличается, обновляем
            if not client.car_brand or client.car_brand != car_brand_clean:
                await session.execute(
                    update(Client)
                    .where(Client.id == client_id)
                    .values(car_brand=car_brand_clean)
                )
                await session.commit()
                await session.refresh(client)
                return client
    
    return None


async def get_available_dates(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> Set[date]:
    """Получить доступные даты для записи (проверяет блокировки и наличие свободных слотов)"""
    from sqlalchemy import and_, func
    from shared.database.models import BlockedSlot, Setting, Booking, Post
    from bot.config import WORK_START_TIME, WORK_END_TIME, SLOT_DURATION
    
    # Получаем настройки
    result = await session.execute(
        select(Setting).where(Setting.key == "accepting_bookings")
    )
    accepting_setting = result.scalar_one_or_none()
    if accepting_setting and accepting_setting.value.lower() == "false":
        return set()  # Прием заявок отключен
    
    # Получаем общее количество активных постов
    total_posts_query = select(func.count(Post.id)).where(Post.is_active == True)
    total_posts_result = await session.execute(total_posts_query)
    total_posts = total_posts_result.scalar() or 0
    
    if total_posts == 0:
        return set()  # Если нет постов, нет доступных дат
    
    # Получаем все даты в диапазоне
    available = set()
    current = start_date
    today = date.today()
    
    # Парсим время начала и конца работы
    start_hour, start_min = map(int, WORK_START_TIME.split(":"))
    end_hour, end_min = map(int, WORK_END_TIME.split(":"))
    
    work_start = time(start_hour, start_min)
    work_end = time(end_hour, end_min)
    
    while current <= end_date:
        if current < today:
            current += timedelta(days=1)
            continue
        
        # Проверяем блокировки
        result = await session.execute(
            select(BlockedSlot).where(
                and_(
                    BlockedSlot.block_type == "full_service",
                    BlockedSlot.start_date <= current,
                    BlockedSlot.end_date >= current
                )
            )
        )
        blocked = result.scalar_one_or_none()
        
        if blocked:
            current += timedelta(days=1)
            continue
        
        # Упрощенная проверка: если есть активные посты и нет блокировки на день,
        # дата доступна, а свободные слоты проверяются на следующем шаге (выбор времени).
        # Это устраняет ложные "нет свободных дат" при наличии записей без поста.
        available.add(current)
        
        current += timedelta(days=1)
    
    return available


async def get_masters(session: AsyncSession, company_id: Optional[int] = None) -> List[Master]:
    """Получить список всех мастеров"""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    logger.info(f"🔍 Определен company_id={company_id} из search_path: {search_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔍 Получаем список мастеров из схемы {schema_name}")
        
        # Устанавливаем search_path
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Используем прямой SQL запрос
        result = await session.execute(
            text('SELECT id, user_id, full_name, phone, telegram_id, specialization, is_universal, created_at, updated_at FROM masters ORDER BY full_name')
        )
        rows = result.fetchall()
        
        # Преобразуем в объекты Master
        masters = []
        for row in rows:
            master = type('Master', (), {})()
            master.id = row[0]
            master.user_id = row[1]
            master.full_name = row[2]
            master.phone = row[3]
            master.telegram_id = row[4]
            master.specialization = row[5]
            master.is_universal = row[6] if row[6] is not None else True
            master.created_at = row[7]
            master.updated_at = row[8]
            # Для совместимости со старым кодом
            master.is_active = True  # Мастера всегда активны, если они в таблице
            masters.append(master)
        
        logger.info(f"✅ Найдено мастеров: {len(masters)}")
        return masters
    else:
        # Fallback на ORM (может не работать в tenant схемах)
        logger.warning("⚠️ company_id не указан, используем ORM (может не работать)")
        result = await session.execute(
            select(Master).order_by(Master.full_name)
        )
        return list(result.scalars().all())


async def get_posts(session: AsyncSession, company_id: Optional[int] = None) -> List[Post]:
    """Получить список всех постов"""
    import logging
    logger = logging.getLogger(__name__)
    from sqlalchemy import text
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    logger.info(f"🔍 Определен company_id={company_id} из search_path: {search_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔍 Получаем список постов из схемы {schema_name}")
        
        # Устанавливаем search_path
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Используем прямой SQL запрос
        result = await session.execute(
            text('SELECT id, number, name, is_active, created_at, updated_at FROM posts ORDER BY name')
        )
        rows = result.fetchall()
        
        # Преобразуем в объекты Post
        posts = []
        for row in rows:
            post = type('Post', (), {})()
            post.id = row[0]
            post.number = row[1]
            post.name = row[2]
            post.is_active = row[3] if row[3] is not None else True
            post.created_at = row[4]
            post.updated_at = row[5]
            posts.append(post)
        
        logger.info(f"✅ Найдено постов: {len(posts)}")
        return posts
    else:
        # Fallback на ORM (может не работать в tenant схемах)
        logger.warning("⚠️ company_id не указан, используем ORM (может не работать)")
        result = await session.execute(
            select(Post).order_by(Post.name)
        )
        return list(result.scalars().all())


async def get_services(session: AsyncSession, active_only: bool = True, company_id: Optional[int] = None) -> List[Service]:
    """Получить список услуг"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔍 get_services вызвана: active_only={active_only}, company_id={company_id}")
    
    # Устанавливаем search_path для tenant схемы, если указан company_id
    if company_id:
        from sqlalchemy import text
        schema_name = f"tenant_{company_id}"
        logger.info(f"📋 Устанавливаем search_path на схему: {schema_name}")
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    else:
        logger.warning("⚠️ company_id не указан! Запрос может не найти услуги в tenant схеме")
    
    query = select(Service)
    if active_only:
        query = query.where(Service.is_active == True)
    query = query.order_by(Service.name)
    
    logger.info(f"🔍 Выполняем запрос: {query}")
    result = await session.execute(query)
    services = list(result.scalars().all())
    logger.info(f"✅ Найдено услуг: {len(services)}")
    for service in services:
        logger.info(f"  - {service.name} (ID: {service.id}, активна: {service.is_active})")
    
    return services


async def get_service_by_id(session: AsyncSession, service_id: int, company_id: Optional[int] = None) -> Optional[Service]:
    """Получить услугу по ID"""
    # Устанавливаем search_path для tenant схемы, если указан company_id
    if company_id:
        from sqlalchemy import text
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    result = await session.execute(
        select(Service).where(Service.id == service_id)
    )
    return result.scalar_one_or_none()


async def create_booking(
    session: AsyncSession,
    client_id: int,
    service_id: int,
    booking_date: date,
    booking_time: time,
    duration: int,
    end_time: time,
    comment: Optional[str] = None,
    created_by: Optional[int] = None,
    company_id: Optional[int] = None,
) -> Booking:
    """Создать запись"""
    import logging
    logger = logging.getLogger(__name__)
    from datetime import datetime
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if not company_id:
        logger.error("❌ company_id обязателен для create_booking в tenant схеме!")
        raise ValueError("company_id обязателен для create_booking в tenant схеме!")
    
    schema_name = f"tenant_{company_id}"
    logger.info(f"🔍 Создаем запись в схеме {schema_name}")
    
    # Устанавливаем search_path
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    # Генерация booking_number
    date_str = booking_date.strftime("%Y%m%d")
    result = await session.execute(
        text(f"""
            SELECT booking_number
            FROM "{schema_name}".bookings
            WHERE booking_number LIKE :pattern
            ORDER BY booking_number DESC
            LIMIT 1
        """),
        {"pattern": f"B-{date_str}-%"}
    )
    last_booking_row = result.fetchone()
    
    if last_booking_row and last_booking_row[0]:
        try:
            counter = int(last_booking_row[0].split("-")[-1]) + 1
        except (ValueError, IndexError):
            counter = 1
    else:
        counter = 1
    
    booking_number = f"B-{date_str}-{counter:03d}"
    
    # Используем прямой SQL INSERT
    now = datetime.utcnow()
    today = date.today()  # Дата заявки - когда клиент отправил заявку
    
    logger.info(
        f"📝 [CRUD] Вставка записи: booking_number={booking_number}, service_date={booking_date}, "
        f"time={booking_time}, duration={duration}, end_time={end_time}, request_date={today}"
    )
    result = await session.execute(
        text(f"""
            INSERT INTO "{schema_name}".bookings (
                booking_number, client_id, service_id, service_date, time, duration, end_time,
                request_date, comment, created_by, status, created_at, updated_at
            )
            VALUES (
                :booking_number, :client_id, :service_id, :service_date, :time, :duration, :end_time,
                :request_date, :comment, :created_by, :status, :created_at, :updated_at
            )
            RETURNING id, booking_number, client_id, service_id, service_date, time, duration, end_time,
                      request_date, comment, created_by, status, created_at, updated_at
        """),
        {
            "booking_number": booking_number,
            "client_id": client_id,
            "service_id": service_id,
            "service_date": booking_date,
            "time": booking_time,
            "duration": duration,
            "end_time": end_time,
            "request_date": today,  # Дата заявки
            "comment": comment,
            "created_by": created_by,
            "status": "new",
            "created_at": now,
            "updated_at": now,
        }
    )
    row = result.fetchone()
    if row:
        # Создаем объект Booking с правильными полями
        booking = type('Booking', (), {})()
        booking.id = row[0]
        booking.booking_number = row[1]
        booking.client_id = row[2]
        booking.service_id = row[3]
        booking.service_date = row[4]  # Было booking.date, переименовано
        booking.time = row[5]
        booking.duration = row[6]
        booking.end_time = row[7]
        booking.request_date = row[8]
        booking.comment = row[9]
        booking.created_by = row[10]
        booking.status = row[11]
        booking.created_at = row[12]
        booking.updated_at = row[13]
        # Добавляем совместимые атрибуты для старого кода
        booking.master_id = None
        booking.post_id = None
        booking.amount = None
        booking.is_paid = False
        booking.payment_method = None
        booking.promocode_id = None
        booking.discount_amount = 0
        booking.admin_comment = None
        booking.confirmed_at = None
        booking.completed_at = None
        booking.cancelled_at = None
        await session.commit()
        logger.info(f"✅ Запись создана: id={booking.id}, booking_number={booking.booking_number}")
        return booking
    else:
        await session.rollback()
        raise Exception("Не удалось создать запись")


async def get_bookings_by_client(session: AsyncSession, client_id: int) -> List[Booking]:
    """Получить записи клиента"""
    result = await session.execute(
        select(Booking)
        .where(Booking.client_id == client_id)
        .order_by(Booking.service_date.desc(), Booking.time.desc())
        .options(
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post),
        )
    )
    return list(result.scalars().all())


async def get_all_bookings(session: AsyncSession, company_id: Optional[int] = None, limit: Optional[int] = None) -> List[Booking]:
    """Получить все записи (независимо от статуса)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔵 [CRUD] get_all_bookings: company_id={company_id}, limit={limit}")

    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            logger.info(f"🔵 [CRUD] Текущий search_path: {search_path}")
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    logger.info(f"🔵 [CRUD] Определен company_id={company_id} из search_path: {search_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")

    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔵 [CRUD] Получаем все записи из схемы {schema_name}")

        # Устанавливаем search_path
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        logger.info(f"🔵 [CRUD] Установлен search_path: {schema_name}")
        
        # Используем прямой SQL запрос для получения всех записей
        query = f"""
            SELECT b.id, b.booking_number, b.client_id, b.service_id, b.master_id, b.post_id,
                   b.service_date, b.time, b.duration, b.end_time, b.status, b.amount, b.is_paid,
                   b.payment_method, b.comment, b.admin_comment, b.created_at, b.updated_at,
                   b.confirmed_at, b.completed_at, b.cancelled_at, b.created_by
            FROM "{schema_name}".bookings b
            ORDER BY b.service_date DESC, b.time DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"🔵 [CRUD] Выполняем SQL запрос: SELECT ... FROM {schema_name}.bookings")
        result = await session.execute(text(query))
        rows = result.fetchall()
        logger.info(f"🔵 [CRUD] SQL запрос выполнен, получено строк: {len(rows)}")
        
        if len(rows) == 0:
            logger.warning(f"⚠️ [CRUD] Нет записей в схеме {schema_name}")
            # Проверяем, есть ли вообще записи в таблице
            count_result = await session.execute(
                text(f'SELECT COUNT(*) FROM "{schema_name}".bookings')
            )
            total_count = count_result.scalar()
            logger.info(f"🔵 [CRUD] Всего записей в таблице bookings: {total_count}")
        
        # Преобразуем результаты в объекты Booking (та же логика что в get_bookings_by_status)
        bookings = []
        for row in rows:
            booking = type('Booking', (), {})()
            booking.id = row[0]
            booking.booking_number = row[1]
            booking.client_id = row[2]
            booking.service_id = row[3]
            booking.master_id = row[4]
            booking.post_id = row[5]
            booking.service_date = row[6]  # Было booking.date, переименовано
            booking.time = row[7]
            booking.duration = row[8]
            booking.end_time = row[9]
            booking.status = row[10]
            booking.amount = row[11]
            booking.is_paid = row[12] if row[12] is not None else False
            booking.payment_method = row[13]
            booking.comment = row[14]
            booking.admin_comment = row[15]
            booking.created_at = row[16]
            booking.updated_at = row[17]
            booking.confirmed_at = row[18]
            booking.completed_at = row[19]
            booking.cancelled_at = row[20]
            booking.created_by = row[21]
            
            # Загружаем связанные объекты
            if booking.client_id:
                client_result = await session.execute(
                    text(f'SELECT id, user_id, full_name, phone FROM "{schema_name}".clients WHERE id = :client_id'),
                    {"client_id": booking.client_id}
                )
                client_row = client_result.fetchone()
                if client_row:
                    booking.client = type('Client', (), {})()
                    booking.client.id = client_row[0]
                    booking.client.user_id = client_row[1]
                    booking.client.full_name = client_row[2]
                    booking.client.phone = client_row[3]
            
            if booking.service_id:
                service = await get_service_by_id(session, booking.service_id, company_id=company_id)
                booking.service = service
            
            if booking.master_id:
                master_result = await session.execute(
                    text(f'SELECT id, full_name, phone FROM "{schema_name}".masters WHERE id = :master_id'),
                    {"master_id": booking.master_id}
                )
                master_row = master_result.fetchone()
                if master_row:
                    booking.master = type('Master', (), {})()
                    booking.master.id = master_row[0]
                    booking.master.full_name = master_row[1]
                    booking.master.phone = master_row[2]
            
            if booking.post_id:
                post_result = await session.execute(
                    text(f'SELECT id, number, name FROM "{schema_name}".posts WHERE id = :post_id'),
                    {"post_id": booking.post_id}
                )
                post_row = post_result.fetchone()
                if post_row:
                    booking.post = type('Post', (), {})()
                    booking.post.id = post_row[0]
                    booking.post.number = post_row[1]
                    booking.post.name = post_row[2]
            
            bookings.append(booking)
        
        logger.info(f"✅ Найдено всех записей: {len(bookings)}")
        return bookings
    else:
        logger.error("❌ company_id обязателен для get_all_bookings в tenant схеме!")
        return []


async def get_bookings_by_status(session: AsyncSession, status: str, company_id: Optional[int] = None) -> List[Booking]:
    """Получить записи по статусу"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🔵 [CRUD] get_bookings_by_status: status='{status}', company_id={company_id}")
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            logger.info(f"🔵 [CRUD] Текущий search_path: {search_path}")
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    logger.info(f"🔵 [CRUD] Определен company_id={company_id} из search_path: {search_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔵 [CRUD] Получаем записи со статусом '{status}' из схемы {schema_name}")
        
        # Устанавливаем search_path (если еще не установлен)
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        logger.info(f"🔵 [CRUD] Установлен search_path: {schema_name}")
    
    # Используем прямой SQL запрос - search_path уже установлен
    logger.info(f"🔵 [CRUD] Выполняем SQL запрос: SELECT ... WHERE status='{status}'")
    result = await session.execute(
        text("""
            SELECT b.id, b.booking_number, b.client_id, b.service_id, b.master_id, b.post_id,
                   b.service_date, b.time, b.duration, b.end_time, b.status, b.amount, b.is_paid,
                   b.payment_method, b.comment, b.admin_comment, b.created_at, b.updated_at,
                   b.confirmed_at, b.completed_at, b.cancelled_at, b.created_by
            FROM bookings b
            WHERE b.status = :status
            ORDER BY b.service_date ASC, b.time ASC
        """),
        {"status": status}
    )
    rows = result.fetchall()
    logger.info(f"🔵 [CRUD] SQL запрос выполнен, получено строк: {len(rows)}")
    
    if len(rows) == 0:
        logger.warning(f"⚠️ [CRUD] Нет записей со статусом '{status}'")
        # Проверяем, есть ли вообще записи в таблице
        count_result = await session.execute(text('SELECT COUNT(*) FROM bookings'))
        total_count = count_result.scalar()
        logger.info(f"🔵 [CRUD] Всего записей в таблице bookings: {total_count}")
        if total_count > 0:
            # Проверяем, какие статусы есть
            status_result = await session.execute(text('SELECT DISTINCT status FROM bookings'))
            statuses = [row[0] for row in status_result.fetchall()]
            logger.info(f"🔵 [CRUD] Найденные статусы в таблице: {statuses}")
    
    # Преобразуем результаты в объекты Booking
    bookings = []
    logger.info(f"🔵 [CRUD] Начинаем преобразование {len(rows)} строк в объекты Booking")
    for idx, row in enumerate(rows):
        logger.debug(f"🔵 [CRUD] Обрабатываем строку {idx+1}/{len(rows)}: booking_id={row[0]}, status={row[10]}")
        booking = type('Booking', (), {})()
        booking.id = row[0]
        booking.booking_number = row[1]
        booking.client_id = row[2]
        booking.service_id = row[3]
        booking.master_id = row[4]
        booking.post_id = row[5]
        booking.service_date = row[6]
        booking.time = row[7]
        booking.duration = row[8]
        booking.end_time = row[9]
        booking.status = row[10]
        booking.amount = row[11]
        booking.is_paid = row[12] if row[12] is not None else False
        booking.payment_method = row[13]
        booking.comment = row[14]
        booking.admin_comment = row[15]
        booking.created_at = row[16]
        booking.updated_at = row[17]
        booking.confirmed_at = row[18]
        booking.completed_at = row[19]
        booking.cancelled_at = row[20]
        booking.created_by = row[21]
        
        # Загружаем связанные объекты
        if booking.client_id:
            # Получаем клиента по client_id (search_path уже установлен)
            client_result = await session.execute(
                text('SELECT id, user_id, full_name, phone FROM clients WHERE id = :client_id'),
                {"client_id": booking.client_id}
            )
            client_row = client_result.fetchone()
            if client_row:
                booking.client = type('Client', (), {})()
                booking.client.id = client_row[0]
                booking.client.user_id = client_row[1]
                booking.client.full_name = client_row[2]
                booking.client.phone = client_row[3]
                # Загружаем user если есть
                if booking.client.user_id:
                    user_result = await session.execute(
                        text('SELECT id, telegram_id, username, full_name, phone, role FROM users WHERE id = :user_id'),
                        {"user_id": booking.client.user_id}
                    )
                    user_row = user_result.fetchone()
                    if user_row:
                        booking.client.user = type('User', (), {})()
                        booking.client.user.id = user_row[0]
                        booking.client.user.telegram_id = user_row[1]
                        booking.client.user.username = user_row[2]
                        booking.client.user.full_name = user_row[3]
                        booking.client.user.phone = user_row[4]
                        booking.client.user.role = user_row[5]
        
        if booking.service_id:
            service = await get_service_by_id(session, booking.service_id, company_id=company_id)
            booking.service = service
        
        if booking.master_id:
            master_result = await session.execute(
                text('SELECT id, full_name, phone FROM masters WHERE id = :master_id'),
                {"master_id": booking.master_id}
            )
            master_row = master_result.fetchone()
            if master_row:
                booking.master = type('Master', (), {})()
                booking.master.id = master_row[0]
                booking.master.full_name = master_row[1]
                booking.master.phone = master_row[2]
        
        if booking.post_id:
            post_result = await session.execute(
                text('SELECT id, number, name FROM posts WHERE id = :post_id'),
                {"post_id": booking.post_id}
            )
            post_row = post_result.fetchone()
            if post_row:
                booking.post = type('Post', (), {})()
                booking.post.id = post_row[0]
                booking.post.number = post_row[1]
                booking.post.name = post_row[2]
        
        bookings.append(booking)
    
    logger.info(f"✅ Найдено записей со статусом '{status}': {len(bookings)}")
    return bookings


async def get_booking_by_id(session: AsyncSession, booking_id: int, company_id: Optional[int] = None) -> Optional[Booking]:
    """Получить запись по ID"""
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    
    # ЛОГИРУЕМ ВСЕ ВХОДЯЩИЕ ПАРАМЕТРЫ
    logger.info(f"🔵 [get_booking_by_id] ВХОД: booking_id={booking_id} (type={type(booking_id)}), company_id={company_id}")
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Если booking_id == 0, это новый заказ, не возвращаем ничего
    # ДО ВСЕХ ОСТАЛЬНЫХ ОПЕРАЦИЙ!
    if booking_id == 0:
        # Получаем traceback, чтобы понять, откуда вызывается
        tb = ''.join(traceback.format_stack()[-5:-1])  # Последние 4 уровня стека
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Попытка получить запись с ID=0 - это новый заказ, возвращаем None\n{tb}")
        return None
    
    # Если company_id не указан, пытаемся определить из search_path
    if not company_id:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    logger.info(f"🔍 Определен company_id={company_id} из search_path: {search_path}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось определить company_id из search_path: {e}")
    
    if company_id:
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔍 Получаем запись по ID={booking_id} из схемы {schema_name}")
        
        # Устанавливаем search_path
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Используем прямой SQL запрос для получения записи
        result = await session.execute(
            text(f"""
                SELECT b.id, b.booking_number, b.client_id, b.service_id, b.master_id, b.post_id,
                       b.service_date, b.time, b.duration, b.end_time, b.status, b.amount, b.is_paid,
                       b.payment_method, b.comment, b.admin_comment, b.created_at, b.updated_at,
                       b.confirmed_at, b.completed_at, b.cancelled_at, b.created_by
                FROM "{schema_name}".bookings b
                WHERE b.id = :booking_id
            """),
            {"booking_id": booking_id}
        )
        row = result.fetchone()
        
        if not row:
            return None
        
        # Создаем объект Booking
        booking = type('Booking', (), {})()
        booking.id = row[0]
        booking.booking_number = row[1]
        booking.client_id = row[2]
        booking.service_id = row[3]
        booking.master_id = row[4]
        booking.post_id = row[5]
        booking.service_date = row[6]
        booking.time = row[7]
        booking.duration = row[8]
        booking.end_time = row[9]
        booking.status = row[10]
        booking.amount = row[11]
        booking.is_paid = row[12] if row[12] is not None else False
        booking.payment_method = row[13]
        booking.comment = row[14]
        booking.admin_comment = row[15]
        booking.created_at = row[16]
        booking.updated_at = row[17]
        booking.confirmed_at = row[18]
        booking.completed_at = row[19]
        booking.cancelled_at = row[20]
        booking.created_by = row[21]
        
        # Загружаем связанные объекты
        if booking.client_id:
            client_result = await session.execute(
                text(f'SELECT id, user_id, full_name, phone FROM "{schema_name}".clients WHERE id = :client_id'),
                {"client_id": booking.client_id}
            )
            client_row = client_result.fetchone()
            if client_row:
                booking.client = type('Client', (), {})()
                booking.client.id = client_row[0]
                booking.client.user_id = client_row[1]
                booking.client.full_name = client_row[2]
                booking.client.phone = client_row[3]
                # Загружаем user если есть
                if booking.client.user_id:
                    user_result = await session.execute(
                        text(f'SELECT id, telegram_id, username, full_name, phone, role FROM "{schema_name}".users WHERE id = :user_id'),
                        {"user_id": booking.client.user_id}
                    )
                    user_row = user_result.fetchone()
                    if user_row:
                        booking.client.user = type('User', (), {})()
                        booking.client.user.id = user_row[0]
                        booking.client.user.telegram_id = user_row[1]
                        booking.client.user.username = user_row[2]
                        booking.client.user.full_name = user_row[3]
                        booking.client.user.phone = user_row[4]
                        booking.client.user.role = user_row[5]
        
        if booking.service_id:
            service = await get_service_by_id(session, booking.service_id, company_id=company_id)
            booking.service = service
        
        if booking.master_id:
            master_result = await session.execute(
                text(f'SELECT id, full_name, phone FROM "{schema_name}".masters WHERE id = :master_id'),
                {"master_id": booking.master_id}
            )
            master_row = master_result.fetchone()
            if master_row:
                booking.master = type('Master', (), {})()
                booking.master.id = master_row[0]
                booking.master.full_name = master_row[1]
                booking.master.phone = master_row[2]
        
        if booking.post_id:
            post_result = await session.execute(
                text(f'SELECT id, number, name FROM "{schema_name}".posts WHERE id = :post_id'),
                {"post_id": booking.post_id}
            )
            post_row = post_result.fetchone()
            if post_row:
                booking.post = type('Post', (), {})()
                booking.post.id = post_row[0]
                booking.post.number = post_row[1]
                booking.post.name = post_row[2]
        
        logger.info(f"✅ Запись найдена: id={booking.id}, booking_number={booking.booking_number}")
        return booking
    else:
        # Fallback на ORM (может не работать в tenant схемах)
        logger.warning("⚠️ company_id не указан, используем ORM (может не работать)")
        result = await session.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
                selectinload(Booking.master),
                selectinload(Booking.post),
            )
        )
        return result.scalar_one_or_none()


async def get_master_bookings_by_date(
    session: AsyncSession,
    master_id: int,
    booking_date: date,
) -> List[Booking]:
    """Получить записи мастера на дату"""
    from sqlalchemy import and_
    result = await session.execute(
        select(Booking)
        .where(
            and_(
                Booking.master_id == master_id,
                Booking.service_date == booking_date,
                Booking.status.in_(["confirmed", "new", "completed"])
            )
        )
        .order_by(Booking.time.asc())
        .options(
            selectinload(Booking.client).selectinload(Client.user),
            selectinload(Booking.service),
            selectinload(Booking.post),
        )
    )
    return list(result.scalars().all())


async def update_booking_status(
    session: AsyncSession,
    booking_id: int,
    status: str,
    master_id: Optional[int] = None,
    post_id: Optional[int] = None,
    company_id: Optional[int] = None,
) -> Optional[Booking]:
    """Обновить статус записи"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Определяем company_id и schema_name
    schema_name = None
    if company_id:
        schema_name = f"tenant_{company_id}"
    else:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    schema_name = f"tenant_{company_id}"
        except Exception:
            pass
    
    if schema_name:
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    # Получаем booking
    booking = await get_booking_by_id(session, booking_id, company_id=company_id)
    if not booking:
        logger.error(f"❌ [CRUD] Запись {booking_id} не найдена")
        return None

    # Сохраняем старый статус ДО обновления
    old_status = booking.status
    
    logger.info(f"🔵 [CRUD] Обновляем статус записи {booking_id}: {old_status} -> {status}")
    
    # Обновляем через SQL запрос (search_path уже установлен)
    update_fields = ["status = :status"]
    params = {"status": status, "booking_id": booking_id}
    
    if master_id:
        update_fields.append("master_id = :master_id")
        params["master_id"] = master_id
        logger.info(f"🔵 [CRUD] Назначаем мастера: {master_id}")
    
    if post_id:
        update_fields.append("post_id = :post_id")
        params["post_id"] = post_id
        logger.info(f"🔵 [CRUD] Назначаем пост: {post_id}")
    
    if status == "confirmed":
        update_fields.append("confirmed_at = CURRENT_TIMESTAMP")
    elif status == "completed":
        update_fields.append("completed_at = CURRENT_TIMESTAMP")
    elif status == "cancelled":
        update_fields.append("cancelled_at = CURRENT_TIMESTAMP")
    
    # Выполняем UPDATE через SQL (search_path уже установлен)
    await session.execute(
        text(f"UPDATE bookings SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = :booking_id"),
        params
    )
    await session.commit()
    
    logger.info(f"✅ [CRUD] Статус записи {booking_id} обновлен на '{status}'")
    
    # Получаем обновленную запись
    if schema_name:
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    booking = await get_booking_by_id(session, booking_id, company_id=company_id)
    if not booking:
        logger.warning(f"⚠️ [CRUD] Не удалось получить обновленную запись {booking_id}, но обновление выполнено успешно")
        # Создаем минимальный объект booking для возврата
        booking = type('Booking', (), {})()
        booking.id = booking_id
        booking.status = status
        booking.master_id = master_id
        booking.post_id = post_id
    
    # Планируем напоминания при подтверждении записи (только если статус изменился с другого на confirmed)
    if status == "confirmed" and old_status != "confirmed" and company_id and booking:
        try:
            # Импортируем функцию планирования из веб-бэкенда
            import sys
            import os
            from pathlib import Path
            
            # Получаем путь к корню проекта
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            backend_path = project_root / "web" / "backend"
            
            if backend_path.exists() and str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
            
            try:
                from app.tasks.notifications import schedule_booking_reminders
                schedule_booking_reminders(
                    company_id=company_id,
                    booking_id=booking_id,
                    booking_date=booking.service_date,
                    booking_time=booking.time
                )
                logger.info(f"📅 [CRUD] Напоминания запланированы для записи {booking_id}")
            except ImportError as e:
                logger.warning(f"⚠️ [CRUD] Не удалось импортировать schedule_booking_reminders: {e}")
            except Exception as e:
                logger.error(f"❌ [CRUD] Ошибка планирования напоминаний для записи {booking_id}: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"❌ [CRUD] Ошибка планирования напоминаний для записи {booking_id}: {e}", exc_info=True)
    
    return booking


async def update_booking_request_date(
    session: AsyncSession,
    booking_id: int,
    new_request_date: Optional[date] = None,
    company_id: Optional[int] = None,
) -> Optional[Booking]:
    """
    Обновить дату заявки записи.
    
    Args:
        session: Сессия БД
        booking_id: ID записи
        new_request_date: Новая дата заявки (если None, обновляется текущая)
        company_id: ID компании (для tenant схемы)
    
    Returns:
        Обновленный объект записи или None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Определяем company_id и schema_name
    schema_name = None
    if company_id:
        schema_name = f"tenant_{company_id}"
    else:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    schema_name = f"tenant_{company_id}"
        except Exception:
            pass
    
    if schema_name:
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    # Получаем booking
    booking = await get_booking_by_id(session, booking_id, company_id=company_id)
    if not booking:
        logger.error(f"❌ Запись {booking_id} не найдена")
        return None
    
    old_request_date = booking.request_date
    logger.info(f"🔵 Обновляем дату заявки записи {booking_id}: {old_request_date} -> {new_request_date}")
    
    # Выполняем UPDATE через SQL (search_path уже установлен)
    await session.execute(
        text(f"UPDATE bookings SET request_date = :request_date, updated_at = CURRENT_TIMESTAMP WHERE id = :booking_id"),
        {"request_date": new_request_date, "booking_id": booking_id}
    )
    await session.commit()
    
    logger.info(f"✅ Дата заявки записи {booking_id} обновлена на {new_request_date}")
    
    # Получаем обновленную запись
    if schema_name:
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    booking = await get_booking_by_id(session, booking_id, company_id=company_id)
    
    return booking


async def update_booking_service_date(
    session: AsyncSession,
    booking_id: int,
    new_service_date: Optional[date] = None,
    company_id: Optional[int] = None,
) -> Optional[Booking]:
    """
    Обновить дату услуги записи.
    
    Args:
        session: Сессия БД
        booking_id: ID записи
        new_service_date: Новая дата услуги
        company_id: ID компании (для tenant схемы)
    
    Returns:
        Обновленный объект записи или None
    """
    import logging
    logger = logging.getLogger(__name__)
    
    schema_name = None
    if company_id:
        schema_name = f"tenant_{company_id}"
    else:
        try:
            result = await session.execute(text("SHOW search_path"))
            search_path = result.scalar()
            if search_path and "tenant_" in search_path:
                import re
                match = re.search(r'tenant_(\d+)', search_path)
                if match:
                    company_id = int(match.group(1))
                    schema_name = f"tenant_{company_id}"
        except Exception:
            pass
    
    if schema_name:
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    booking = await get_booking_by_id(session, booking_id, company_id=company_id)
    if not booking:
        logger.error(f"❌ Запись {booking_id} не найдена")
        return None
    
    logger.info(f"🔵 Обновляем дату услуги записи {booking_id}: {booking.service_date} -> {new_service_date}")
    
    await session.execute(
        text("UPDATE bookings SET service_date = :service_date, updated_at = CURRENT_TIMESTAMP WHERE id = :booking_id"),
        {"service_date": new_service_date, "booking_id": booking_id}
    )
    await session.commit()
    
    logger.info(f"✅ Дата услуги записи {booking_id} обновлена на {new_service_date}")
    
    if schema_name:
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    booking = await get_booking_by_id(session, booking_id, company_id=company_id)
    
    return booking
