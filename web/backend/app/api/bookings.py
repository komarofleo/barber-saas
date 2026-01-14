"""API для работы с записями"""
import logging
from datetime import date, time, datetime, timedelta
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload, load_only

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.booking import BookingResponse, BookingListResponse, BookingCreateRequest, BookingUpdateRequest
from shared.database.models import Booking, User, Client, Service, Master, Post
from sqlalchemy.orm import selectinload, load_only
from app.services.tenant_service import get_tenant_service
from jose import jwt
from app.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

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


@router.get("", response_model=BookingListResponse)
async def get_bookings(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    master_id: Optional[int] = None,
    service_id: Optional[int] = None,
    post_id: Optional[int] = None,
    search: Optional[str] = None,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список записей.
    """
    logger.info(f"🔍 get_bookings вызван: company_id={company_id}, page={page}, status={status}, current_user.id={current_user.id}")
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать записи")
    
    # Получаем company_id из токена, если не передан в query параметрах
    if not company_id:
        company_id = await get_company_id_from_token(request)
        logger.info(f"🔍 company_id из токена: {company_id}")
    
    # Если company_id все еще не найден, ищем пользователя во всех tenant схемах
    if not company_id:
        logger.info(f"🔍 Поиск company_id для user_id={current_user.id} во всех tenant схемах...")
        from app.services.tenant_service import get_tenant_service
        tenant_service = get_tenant_service()
        
        companies_result = await db.execute(
            text("SELECT id FROM public.companies WHERE is_active = true")
        )
        companies = companies_result.fetchall()
        
        for company_row in companies:
            test_company_id = company_row[0]
            schema_name = f"tenant_{test_company_id}"
            
            try:
                async for test_session in tenant_service.get_tenant_session(test_company_id):
                    result = await test_session.execute(
                        text(f'SELECT id FROM "{schema_name}".users WHERE id = :user_id'),
                        {"user_id": current_user.id}
                    )
                    if result.fetchone():
                        company_id = test_company_id
                        logger.info(f"✅ Найден company_id={company_id} для user_id={current_user.id}")
                        break
                if company_id:
                    break
            except Exception as e:
                logger.warning(f"Ошибка при поиске в схеме {schema_name}: {e}")
                continue
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден. Необходимо указать company_id в query параметрах или войти как пользователь компании.")
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    logger.info(f"✅ Установлен search_path для tenant_{company_id}")
    
    # Получаем tenant сессию для компании
    tenant_session = db
    
    query = select(Booking).options(
        selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at).selectinload(Client.user),
        selectinload(Booking.service),
        selectinload(Booking.master),
        selectinload(Booking.post)
    )
    
    # Фильтры
    conditions = []
    if status:
        conditions.append(Booking.status == status)
    if start_date:
        conditions.append(Booking.date >= start_date)
    if end_date:
        conditions.append(Booking.date <= end_date)
    if master_id:
        conditions.append(Booking.master_id == master_id)
    if service_id:
        conditions.append(Booking.service_id == service_id)
    if post_id:
        conditions.append(Booking.post_id == post_id)
    
    # Создаем отдельный запрос для подсчета (без selectinload)
    count_query = select(func.count(Booking.id))
    
    if search:
        search_term = f"%{search}%"
        # Поиск по номеру записи, ФИО клиента, телефону
        from sqlalchemy.orm import outerjoin
        query = query.outerjoin(Client).outerjoin(User, Client.user_id == User.id).where(
            or_(
                Booking.booking_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.full_name.ilike(search_term)
            )
        )
        # Для подсчета тоже нужен join
        count_query = count_query.outerjoin(Client).outerjoin(User, Client.user_id == User.id).where(
            or_(
                Booking.booking_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.full_name.ilike(search_term)
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # Подсчет общего количества
    total = await tenant_session.scalar(count_query) or 0
    
    logger.info(f"📊 Запрос записей: total={total}, page={page}, page_size={page_size}")
    logger.info(f"📅 Фильтры: start_date={start_date}, end_date={end_date}, status={status}, search={search}")
    
    # Проверяем общее количество записей в БД без фильтров (для отладки)
    total_all_query = select(func.count(Booking.id))
    total_all = await tenant_session.scalar(total_all_query) or 0
    logger.info(f"📈 Всего записей в БД (без фильтров): {total_all}")
    
    # Пагинация и сортировка
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Booking.date.desc(), Booking.time.desc())
    
    result = await tenant_session.execute(query)
    bookings = result.scalars().all()
    
    logger.info(f"✅ Получено записей: {len(bookings)}")
    if len(bookings) > 0:
        logger.info(f"📋 Первая запись: date={bookings[0].date}, status={bookings[0].status}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for booking in bookings:
        booking_dict = {
            "id": booking.id,
            "booking_number": booking.booking_number,
            "client_id": booking.client_id,
            "service_id": booking.service_id,
            "master_id": booking.master_id,
            "post_id": booking.post_id,
            "date": booking.date,
            "time": booking.time,
            "duration": booking.duration,
            "end_time": booking.end_time,
            "status": booking.status,
            "amount": booking.amount,
            "is_paid": booking.is_paid or False,
            "payment_method": booking.payment_method,
            "comment": booking.comment,
            "admin_comment": booking.admin_comment,
            "created_at": booking.created_at,
            "confirmed_at": booking.confirmed_at,
            "completed_at": booking.completed_at,
            "cancelled_at": booking.cancelled_at,
            "client_name": None,
            "client_phone": None,
            "client_telegram_id": None,
            "client_car_brand": None,
            "client_car_model": None,
            "service_name": None,
            "master_name": None,
            "post_number": None,
        }
        
        if booking.client:
            if booking.client.user:
                booking_dict["client_name"] = f"{booking.client.user.first_name or ''} {booking.client.user.last_name or ''}".strip() or booking.client.full_name
                booking_dict["client_telegram_id"] = booking.client.user.telegram_id
            else:
                booking_dict["client_name"] = booking.client.full_name
            booking_dict["client_phone"] = booking.client.phone
            # Для салона красоты нет car_brand и car_model
            booking_dict["client_car_brand"] = None
            booking_dict["client_car_model"] = None
        if booking.service:
            booking_dict["service_name"] = booking.service.name
        if booking.master:
            booking_dict["master_name"] = booking.master.full_name
        if booking.post:
            booking_dict["post_number"] = booking.post.number
        
        items.append(BookingResponse.model_validate(booking_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/available-slots", response_model=list[str])
async def get_available_slots(
    request: Request,
    booking_date: date = Query(..., alias="date", description="Дата в формате YYYY-MM-DD"),
    master_id: Optional[int] = Query(None),
    post_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список доступных временных слотов на указанную дату.
    """
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    # Если company_id все еще не найден, ищем пользователя во всех tenant схемах
    if not company_id:
        from app.services.tenant_service import get_tenant_service
        tenant_service = get_tenant_service()
        
        companies_result = await db.execute(
            text("SELECT id FROM public.companies WHERE is_active = true")
        )
        companies = companies_result.fetchall()
        
        for company_row in companies:
            test_company_id = company_row[0]
            try:
                async for test_session in tenant_service.get_tenant_session(test_company_id):
                    result = await test_session.execute(
                        text(f'SELECT id FROM "tenant_{test_company_id}".users WHERE id = :user_id'),
                        {"user_id": current_user.id}
                    )
                    if result.fetchone():
                        company_id = test_company_id
                        break
                if company_id:
                    break
            except:
                continue
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    tenant_session = db
    
    # Получаем услугу для определения длительности
    duration = 60  # По умолчанию 60 минут
    if service_id:
        service_query = select(Service).where(Service.id == service_id)
        service_result = await tenant_session.execute(service_query)
        service = service_result.scalar_one_or_none()
        if service:
            duration = service.duration
    
    # Получаем все записи на эту дату
    booked_query = select(Booking).where(Booking.date == booking_date)
    if master_id:
        booked_query = booked_query.where(Booking.master_id == master_id)
    booked_result = await tenant_session.execute(booked_query)
    booked = booked_result.scalars().all()
    
    # Генерируем список всех возможных временных слотов
    slots = []
    start_hour = 9
    end_hour = 18
    
    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:
            slot_time = time(hour, minute)
            slots.append(slot_time.strftime("%H:%M"))
    
    # Если выбран конкретный пост - проверяем доступность для этого поста
    if post_id:
        available_slots = []
        for slot_str in slots:
            slot_time = datetime.strptime(slot_str, "%H:%M").time()
            slot_datetime = datetime.combine(booking_date, slot_time)
            slot_end = slot_datetime + timedelta(minutes=duration)
            
            is_available = True
            for booking in booked:
                if booking.post_id == post_id:
                    booking_start = datetime.combine(booking.date, booking.time)
                    booking_end = datetime.combine(booking.date, booking.end_time)
                    
                    # Проверяем пересечение времени
                    if not (slot_end <= booking_start or slot_datetime >= booking_end):
                        is_available = False
                        break
            
            if is_available:
                available_slots.append(slot_str)
        
        return available_slots
    
    # Если пост не выбран - проверяем общую доступность с учетом всех постов
    from sqlalchemy import func
    
    # Получаем общее количество активных постов
    total_posts_query = select(func.count(Post.id)).where(Post.is_active == True)
    total_posts_result = await tenant_session.execute(total_posts_query)
    total_posts = total_posts_result.scalar() or 0
    
    if total_posts == 0:
        return []
    
    available_slots = []
    for slot_str in slots:
        slot_time = datetime.strptime(slot_str, "%H:%M").time()
        slot_datetime = datetime.combine(booking_date, slot_time)
        slot_end = slot_datetime + timedelta(minutes=duration)
        
        # Подсчитываем количество занятых постов
        occupied_posts = set()
        bookings_without_post = 0
        
        for booking in booked:
            booking_start = datetime.combine(booking.date, booking.time)
            booking_end = datetime.combine(booking.date, booking.end_time)
            
            # Проверяем пересечение времени
            if not (slot_end <= booking_start or slot_datetime >= booking_end):
                if booking.post_id:
                    occupied_posts.add(booking.post_id)
                else:
                    bookings_without_post += 1
        
        total_occupied = len(occupied_posts) + bookings_without_post
        is_available = total_occupied < total_posts
        
        if is_available:
            available_slots.append(slot_str)
    
    return available_slots


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    request: Request,
    booking_id: int,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о записи"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать записи")
    
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    # Если company_id все еще не найден, ищем пользователя во всех tenant схемах
    if not company_id:
        from app.services.tenant_service import get_tenant_service
        tenant_service = get_tenant_service()
        
        companies_result = await db.execute(
            text("SELECT id FROM public.companies WHERE is_active = true")
        )
        companies = companies_result.fetchall()
        
        for company_row in companies:
            test_company_id = company_row[0]
            try:
                async for test_session in tenant_service.get_tenant_session(test_company_id):
                    result = await test_session.execute(
                        text(f'SELECT id FROM "tenant_{test_company_id}".users WHERE id = :user_id'),
                        {"user_id": current_user.id}
                    )
                    if result.fetchone():
                        company_id = test_company_id
                        break
                if company_id:
                    break
            except:
                continue
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    tenant_session = db
    
    query = select(Booking).options(
        selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at).selectinload(Client.user),
        selectinload(Booking.service),
        selectinload(Booking.master),
        selectinload(Booking.post)
    ).where(Booking.id == booking_id)
    
    result = await tenant_session.execute(query)
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Формируем ответ с дополнительными данными
    booking_dict = {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "client_id": booking.client_id,
        "service_id": booking.service_id,
        "master_id": booking.master_id,
        "post_id": booking.post_id,
        "date": booking.date,
        "time": booking.time,
        "duration": booking.duration,
        "end_time": booking.end_time,
        "status": booking.status,
        "amount": booking.amount,
        "is_paid": booking.is_paid or False,
        "payment_method": booking.payment_method,
        "comment": booking.comment,
        "admin_comment": booking.admin_comment,
        "created_at": booking.created_at,
        "confirmed_at": booking.confirmed_at,
        "completed_at": booking.completed_at,
        "cancelled_at": booking.cancelled_at,
        "client_name": None,
        "client_phone": None,
        "client_telegram_id": None,
        "client_car_brand": None,
        "client_car_model": None,
        "service_name": None,
        "master_name": None,
        "post_number": None,
    }
    
    if booking.client:
        if booking.client.user:
            booking_dict["client_name"] = f"{booking.client.user.first_name or ''} {booking.client.user.last_name or ''}".strip() or booking.client.full_name
            booking_dict["client_telegram_id"] = booking.client.user.telegram_id
        else:
            booking_dict["client_name"] = booking.client.full_name
        booking_dict["client_phone"] = booking.client.phone
        # Для салона красоты нет car_brand и car_model
        booking_dict["client_car_brand"] = None
        booking_dict["client_car_model"] = None
    if booking.service:
        booking_dict["service_name"] = booking.service.name
    if booking.master:
        booking_dict["master_name"] = booking.master.full_name
    if booking.post:
        booking_dict["post_number"] = booking.post.number
    
    return BookingResponse.model_validate(booking_dict)


@router.post("", response_model=BookingResponse)
async def create_booking(
    request: Request,
    booking_data: BookingCreateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать новую запись"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать записи")
    
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    # Если company_id все еще не найден, ищем пользователя во всех tenant схемах
    if not company_id:
        from app.services.tenant_service import get_tenant_service
        tenant_service = get_tenant_service()
        
        companies_result = await db.execute(
            text("SELECT id FROM public.companies WHERE is_active = true")
        )
        companies = companies_result.fetchall()
        
        for company_row in companies:
            test_company_id = company_row[0]
            try:
                async for test_session in tenant_service.get_tenant_session(test_company_id):
                    result = await test_session.execute(
                        text(f'SELECT id FROM "tenant_{test_company_id}".users WHERE id = :user_id'),
                        {"user_id": current_user.id}
                    )
                    if result.fetchone():
                        company_id = test_company_id
                        break
                if company_id:
                    break
            except:
                continue
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    tenant_session = db
    
    # Генерируем номер записи
    from datetime import datetime
    booking_number = f"BK{company_id:03d}{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Создаем запись
    booking = Booking(
        booking_number=booking_number,
        client_id=booking_data.client_id,
        service_id=booking_data.service_id,
        master_id=booking_data.master_id,
        post_id=booking_data.post_id,
        date=booking_data.date,
        time=booking_data.time,
        duration=booking_data.duration or 60,
        end_time=(datetime.combine(booking_data.date, booking_data.time) + timedelta(minutes=booking_data.duration or 60)).time(),
        status=booking_data.status or "new",
        amount=booking_data.amount,
        comment=booking_data.comment,
        created_by=current_user.id
    )
    
    tenant_session.add(booking)
    await tenant_session.commit()
    await tenant_session.refresh(booking)
    
    # Загружаем связанные данные
    result = await tenant_session.execute(
        select(Booking).options(
            selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at).selectinload(Client.user),
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post)
        ).where(Booking.id == booking.id)
    )
    booking = result.scalar_one()
    
    # Формируем ответ
    booking_dict = {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "client_id": booking.client_id,
        "service_id": booking.service_id,
        "master_id": booking.master_id,
        "post_id": booking.post_id,
        "date": booking.date,
        "time": booking.time,
        "duration": booking.duration,
        "end_time": booking.end_time,
        "status": booking.status,
        "amount": booking.amount,
        "is_paid": booking.is_paid or False,
        "payment_method": booking.payment_method,
        "comment": booking.comment,
        "admin_comment": booking.admin_comment,
        "created_at": booking.created_at,
        "confirmed_at": booking.confirmed_at,
        "completed_at": booking.completed_at,
        "cancelled_at": booking.cancelled_at,
        "client_name": None,
        "client_phone": None,
        "client_telegram_id": None,
        "client_car_brand": None,
        "client_car_model": None,
        "service_name": None,
        "master_name": None,
        "post_number": None,
    }
    
    if booking.client:
        if booking.client.user:
            booking_dict["client_name"] = f"{booking.client.user.first_name or ''} {booking.client.user.last_name or ''}".strip() or booking.client.full_name
            booking_dict["client_telegram_id"] = booking.client.user.telegram_id
        else:
            booking_dict["client_name"] = booking.client.full_name
        booking_dict["client_phone"] = booking.client.phone
        # Для салона красоты нет car_brand и car_model
        booking_dict["client_car_brand"] = None
        booking_dict["client_car_model"] = None
    if booking.service:
        booking_dict["service_name"] = booking.service.name
    if booking.master:
        booking_dict["master_name"] = booking.master.full_name
    if booking.post:
        booking_dict["post_number"] = booking.post.number
    
    return BookingResponse.model_validate(booking_dict)


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    request: Request,
    booking_id: int,
    booking_data: BookingUpdateRequest,
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить запись"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять записи")
    
    # Получаем company_id из токена, если не передан
    if not company_id:
        company_id = await get_company_id_from_token(request)
    
    # Если company_id все еще не найден, ищем пользователя во всех tenant схемах
    if not company_id:
        from app.services.tenant_service import get_tenant_service
        tenant_service = get_tenant_service()
        
        companies_result = await db.execute(
            text("SELECT id FROM public.companies WHERE is_active = true")
        )
        companies = companies_result.fetchall()
        
        for company_row in companies:
            test_company_id = company_row[0]
            try:
                async for test_session in tenant_service.get_tenant_session(test_company_id):
                    result = await test_session.execute(
                        text(f'SELECT id FROM "tenant_{test_company_id}".users WHERE id = :user_id'),
                        {"user_id": current_user.id}
                    )
                    if result.fetchone():
                        company_id = test_company_id
                        break
                if company_id:
                    break
            except:
                continue
    
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")
    
    # Устанавливаем search_path для tenant схемы
    await db.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    tenant_session = db
    
    # Получаем запись
    result = await tenant_session.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Обновляем поля
    if booking_data.client_id is not None:
        booking.client_id = booking_data.client_id
    if booking_data.service_id is not None:
        booking.service_id = booking_data.service_id
    if booking_data.master_id is not None:
        booking.master_id = booking_data.master_id
    if booking_data.post_id is not None:
        booking.post_id = booking_data.post_id
    if booking_data.date is not None:
        booking.date = booking_data.date
    if booking_data.time is not None:
        booking.time = booking_data.time
    if booking_data.duration is not None:
        booking.duration = booking_data.duration
        booking.end_time = (datetime.combine(booking.date, booking.time) + timedelta(minutes=booking_data.duration)).time()
    if booking_data.status is not None:
        booking.status = booking_data.status
    if booking_data.amount is not None:
        booking.amount = booking_data.amount
    if booking_data.is_paid is not None:
        booking.is_paid = booking_data.is_paid
    if booking_data.payment_method is not None:
        booking.payment_method = booking_data.payment_method
    if booking_data.comment is not None:
        booking.comment = booking_data.comment
    if booking_data.admin_comment is not None:
        booking.admin_comment = booking_data.admin_comment
    
    await tenant_session.commit()
    await tenant_session.refresh(booking)
    
    # Загружаем связанные данные
    result = await tenant_session.execute(
        select(Booking).options(
            selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at).selectinload(Client.user),
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post)
        ).where(Booking.id == booking.id)
    )
    booking = result.scalar_one()
    
    # Формируем ответ
    booking_dict = {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "client_id": booking.client_id,
        "service_id": booking.service_id,
        "master_id": booking.master_id,
        "post_id": booking.post_id,
        "date": booking.date,
        "time": booking.time,
        "duration": booking.duration,
        "end_time": booking.end_time,
        "status": booking.status,
        "amount": booking.amount,
        "is_paid": booking.is_paid or False,
        "payment_method": booking.payment_method,
        "comment": booking.comment,
        "admin_comment": booking.admin_comment,
        "created_at": booking.created_at,
        "confirmed_at": booking.confirmed_at,
        "completed_at": booking.completed_at,
        "cancelled_at": booking.cancelled_at,
        "client_name": None,
        "client_phone": None,
        "client_telegram_id": None,
        "client_car_brand": None,
        "client_car_model": None,
        "service_name": None,
        "master_name": None,
        "post_number": None,
    }
    
    if booking.client:
        if booking.client.user:
            booking_dict["client_name"] = f"{booking.client.user.first_name or ''} {booking.client.user.last_name or ''}".strip() or booking.client.full_name
            booking_dict["client_telegram_id"] = booking.client.user.telegram_id
        else:
            booking_dict["client_name"] = booking.client.full_name
        booking_dict["client_phone"] = booking.client.phone
        # Для салона красоты нет car_brand и car_model
        booking_dict["client_car_brand"] = None
        booking_dict["client_car_model"] = None
    if booking.service:
        booking_dict["service_name"] = booking.service.name
    if booking.master:
        booking_dict["master_name"] = booking.master.full_name
    if booking.post:
        booking_dict["post_number"] = booking.post.number
    
    return BookingResponse.model_validate(booking_dict)
