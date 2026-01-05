"""CRUD операции для работы с БД"""
from datetime import date, time, datetime, timedelta
from typing import Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from shared.database.models import (
    User, Client, Service, Booking, Master, Post
)
from bot.config import ADMIN_IDS


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
) -> User:
    """Создать пользователя"""
    is_admin = telegram_id in ADMIN_IDS
    user = User(
        telegram_id=telegram_id,
        username=username,
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
) -> User:
    """Получить или создать пользователя"""
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        user = await create_user(session, telegram_id, username, first_name, last_name)
    else:
        # Обновить данные если изменились
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
        await session.commit()
        await session.refresh(user)
    return user


async def get_client_by_user_id(session: AsyncSession, user_id: int) -> Optional[Client]:
    """Получить клиента по user_id"""
    result = await session.execute(
        select(Client).where(Client.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_client(
    session: AsyncSession,
    user_id: int,
    full_name: str,
    phone: str,
    car_brand: Optional[str] = None,
    car_model: Optional[str] = None,
    car_number: Optional[str] = None,
) -> Client:
    """Создать клиента"""
    client = Client(
        user_id=user_id,
        full_name=full_name,
        phone=phone,
        car_brand=car_brand,
        car_model=car_model,
        car_number=car_number,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def get_or_create_client(
    session: AsyncSession,
    user_id: int,
    full_name: str,
    phone: str,
) -> Client:
    """Получить или создать клиента"""
    client = await get_client_by_user_id(session, user_id)
    if not client:
        client = await create_client(session, user_id, full_name, phone)
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
    """Получить доступные даты для записи"""
    from sqlalchemy import and_, func
    from shared.database.models import BlockedSlot, Setting
    
    # Получаем настройки
    result = await session.execute(
        select(Setting).where(Setting.key == "accepting_bookings")
    )
    accepting_setting = result.scalar_one_or_none()
    if accepting_setting and accepting_setting.value.lower() == "false":
        return set()  # Прием заявок отключен
    
    # Получаем все даты в диапазоне
    available = set()
    current = start_date
    today = date.today()
    
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
        
        if not blocked:
            available.add(current)
        
        current += timedelta(days=1)
    
    return available


async def get_masters(session: AsyncSession) -> List[Master]:
    """Получить список всех мастеров"""
    result = await session.execute(
        select(Master).order_by(Master.full_name)
    )
    return list(result.scalars().all())


async def get_posts(session: AsyncSession) -> List[Post]:
    """Получить список всех постов"""
    result = await session.execute(
        select(Post).order_by(Post.name)
    )
    return list(result.scalars().all())


async def get_services(session: AsyncSession, active_only: bool = True) -> List[Service]:
    """Получить список услуг"""
    query = select(Service)
    if active_only:
        query = query.where(Service.is_active == True)
    query = query.order_by(Service.name)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_service_by_id(session: AsyncSession, service_id: int) -> Optional[Service]:
    """Получить услугу по ID"""
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
) -> Booking:
    """Создать запись"""
    # Генерация booking_number
    from datetime import datetime
    date_str = booking_date.strftime("%Y%m%d")
    result = await session.execute(
        select(Booking)
        .where(Booking.booking_number.like(f"B-{date_str}-%"))
        .order_by(Booking.booking_number.desc())
        .limit(1)
    )
    last_booking = result.scalar_one_or_none()
    
    if last_booking and last_booking.booking_number:
        try:
            counter = int(last_booking.booking_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            counter = 1
    else:
        counter = 1
    
    booking_number = f"B-{date_str}-{counter:03d}"
    
    booking = Booking(
        booking_number=booking_number,
        client_id=client_id,
        service_id=service_id,
        date=booking_date,
        time=booking_time,
        duration=duration,
        end_time=end_time,
        comment=comment,
        created_by=created_by,
        status="new",
    )
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_bookings_by_client(session: AsyncSession, client_id: int) -> List[Booking]:
    """Получить записи клиента"""
    result = await session.execute(
        select(Booking)
        .where(Booking.client_id == client_id)
        .order_by(Booking.date.desc(), Booking.time.desc())
        .options(
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post),
        )
    )
    return list(result.scalars().all())


async def get_bookings_by_status(session: AsyncSession, status: str) -> List[Booking]:
    """Получить записи по статусу"""
    result = await session.execute(
        select(Booking)
        .where(Booking.status == status)
        .order_by(Booking.date.asc(), Booking.time.asc())
        .options(
            selectinload(Booking.client).selectinload(Client.user),
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post),
        )
    )
    return list(result.scalars().all())


async def get_booking_by_id(session: AsyncSession, booking_id: int) -> Optional[Booking]:
    """Получить запись по ID"""
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
                Booking.date == booking_date,
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
) -> Optional[Booking]:
    """Обновить статус записи"""
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        return None

    booking.status = status
    if master_id:
        booking.master_id = master_id
    if post_id:
        booking.post_id = post_id
    if status == "confirmed":
        booking.confirmed_at = datetime.utcnow()
    elif status == "completed":
        booking.completed_at = datetime.utcnow()
    elif status == "cancelled":
        booking.cancelled_at = datetime.utcnow()

    await session.commit()
    await session.refresh(booking)
    return booking

