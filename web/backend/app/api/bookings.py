"""API для работы с записями"""
import logging
from datetime import date, time, datetime
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.auth import get_current_user
from app.schemas.booking import BookingResponse, BookingListResponse, BookingCreateRequest, BookingUpdateRequest
from shared.database.models import Booking, User, Client, Service, Master, Post
from sqlalchemy.orm import selectinload
from app.services.tenant_service import get_tenant_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.get("", response_model=BookingListResponse)
async def get_bookings(
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
    
    Логирование для отладки проблемы с несуществующей таблицей bookings.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 get_bookings вызван: company_id={company_id}, page={page}, status={status}")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать записи")
    
    # Получаем tenant сессию для компании
    tenant_session = None
    if company_id:
        # Используем tenant сессию для конкретной компании
        tenant_service = get_tenant_service()
        async for session in tenant_service.get_tenant_session(company_id):
            tenant_session = session
            # Устанавливаем search_path явно
            await session.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
            break
    else:
        # Используем обычную сессию для публичного API
        tenant_session = db
    
    query = select(Booking).options(
        selectinload(Booking.client).selectinload(Client.user),
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
        # Поиск по номеру записи, ФИО клиента, телефону, госномеру
        query = query.join(Client).join(User).where(
            or_(
                Booking.booking_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.car_number.ilike(search_term)
            )
        )
        # Для подсчета тоже нужен join
        count_query = count_query.join(Client).join(User).where(
            or_(
                Booking.booking_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.car_number.ilike(search_term)
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # Подсчет общего количества
    total = await tenant_session.scalar(count_query) or 0
    
    print(f"📊 Запрос записей: total={total}, page={page}, page_size={page_size}")
    print(f"📅 Фильтры: start_date={start_date}, end_date={end_date}, status={status}, search={search}")
    print(f"🔍 Условия: {len(conditions)} условий применено")
    
    # Проверяем общее количество записей в БД без фильтров (для отладки)
    total_all_query = select(func.count(Booking.id))
    total_all = await tenant_session.scalar(total_all_query) or 0
    print(f"📈 Всего записей в БД (без фильтров): {total_all}")
    
    # Пагинация
    # Пагинация и сортировка
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Booking.date.desc(), Booking.time.desc())
    
    result = await tenant_session.execute(query)
    bookings = result.scalars().all()
    
    print(f"✅ Получено записей: {len(bookings)}")
    if len(bookings) > 0:
        print(f"📋 Первая запись: date={bookings[0].date}, status={bookings[0].status}")
    
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
                booking_dict["client_telegram_id"] = None
            booking_dict["client_phone"] = booking.client.phone
            
            # Извлекаем марку автомобиля из комментария заявки, если она там есть
            car_brand_from_comment = None
            if booking.comment and "Марка автомобиля:" in booking.comment:
                car_brand_from_comment = booking.comment.replace("Марка автомобиля:", "").strip()
                # Если есть перенос строки, берем только первую часть (марку)
                if car_brand_from_comment and "\n" in car_brand_from_comment:
                    car_brand_from_comment = car_brand_from_comment.split("\n")[0].strip()
                # Фильтруем некорректные значения (эмодзи, команды)
                if car_brand_from_comment:
                    invalid_prefixes = ["/", "📋", "⏭️", "❌"]
                    if any(car_brand_from_comment.startswith(prefix) for prefix in invalid_prefixes):
                        car_brand_from_comment = None
            
            # Используем марку из комментария заявки, если она есть, иначе из профиля клиента
            booking_dict["client_car_brand"] = car_brand_from_comment if car_brand_from_comment else booking.client.car_brand
            booking_dict["client_car_model"] = booking.client.car_model
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
    booking_date: date = Query(..., alias="date", description="Дата в формате YYYY-MM-DD"),
    master_id: Optional[int] = Query(None),
    post_id: Optional[int] = Query(None),
    service_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить доступные временные слоты для даты с учетом количества постов"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать слоты")
    
    print(f"✅ Получен запрос на слоты для даты: {booking_date}, тип: {type(booking_date)}")
    
    # Если выбран конкретный пост - проверяем только его доступность
    if post_id:
        # Получаем длительность услуги
        duration = 30  # по умолчанию
        if service_id:
            service_query = select(Service).where(Service.id == service_id)
            service_result = await tenant_session.execute(service_query)
            service = service_result.scalar_one_or_none()
            if service:
                duration = service.duration
        
        # Генерируем слоты (рабочий день 9:00 - 18:00)
        from datetime import timedelta
        slots = []
        start = datetime.combine(booking_date, time(9, 0))
        end = datetime.combine(booking_date, time(18, 0))
        
        current = start
        while current + timedelta(minutes=duration) <= end:
            slots.append(current.time().strftime("%H:%M"))
            current += timedelta(minutes=duration)
        
        # Проверяем занятые слоты для конкретного поста
        conditions = [
            Booking.date == booking_date,
            Booking.post_id == post_id,
            Booking.status.in_(["new", "confirmed"])
        ]
        if master_id:
            conditions.append(Booking.master_id == master_id)
        
        booked_query = select(Booking).where(and_(*conditions))
        booked_result = await tenant_session.execute(booked_query)
        booked = booked_result.scalars().all()
        
        # Удаляем занятые слоты для этого поста
        available_slots = []
        for slot_str in slots:
            slot_time = datetime.strptime(slot_str, "%H:%M").time()
            slot_datetime = datetime.combine(booking_date, slot_time)
            slot_end = slot_datetime + timedelta(minutes=duration)
            
            is_available = True
            for booking in booked:
                booking_start = datetime.combine(booking.date, booking.time)
                booking_end = datetime.combine(booking.date, booking.end_time)
                
                # Проверяем пересечение
                if not (slot_end <= booking_start or slot_datetime >= booking_end):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(slot_str)
        
        print(f"Возвращаем {len(available_slots)} свободных слотов из {len(slots)} возможных для поста {post_id} на дату {booking_date}")
        return available_slots
    
    # Если пост не выбран - проверяем общую доступность с учетом всех постов
    from sqlalchemy import func
    
    # Получаем общее количество активных постов (ВАЖНО: запрос выполняется каждый раз заново)
    total_posts_query = select(func.count(Post.id)).where(Post.is_active == True)
    total_posts_result = await tenant_session.execute(total_posts_query)
    total_posts = total_posts_result.scalar() or 0
    
    # Получаем также общее количество всех постов для логирования
    all_posts_query = select(func.count(Post.id))
    all_posts_result = await tenant_session.execute(all_posts_query)
    all_posts = all_posts_result.scalar() or 0
    
    # Получаем список активных постов для детального логирования
    active_posts_query = select(Post.id, Post.number, Post.name).where(Post.is_active == True)
    active_posts_result = await tenant_session.execute(active_posts_query)
    active_posts_list = active_posts_result.all()
    
    print(f"📊 Статистика постов для даты {booking_date}: всего постов={all_posts}, активных={total_posts}")
    if active_posts_list:
        print(f"📋 Активные посты: {[f'ID:{p.id} №{p.number}' for p in active_posts_list]}")
    else:
        print(f"📋 Активные посты: нет активных постов")
    
    if total_posts == 0:
        # Если нет постов, возвращаем пустой список
        print("⚠️ Нет активных постов")
        return []
    
    # Получаем длительность услуги
    duration = 30  # по умолчанию
    if service_id:
        service_query = select(Service).where(Service.id == service_id)
        service_result = await tenant_session.execute(service_query)
        service = service_result.scalar_one_or_none()
        if service:
            duration = service.duration
    
    # Генерируем слоты (рабочий день 9:00 - 18:00)
    from datetime import timedelta
    slots = []
    start = datetime.combine(booking_date, time(9, 0))
    end = datetime.combine(booking_date, time(18, 0))
    
    current = start
    while current + timedelta(minutes=duration) <= end:
        slots.append(current.time().strftime("%H:%M"))
        current += timedelta(minutes=duration)
    
    # Получаем все записи на эту дату
    conditions = [
        Booking.date == booking_date,
        Booking.status.in_(["new", "confirmed"])
    ]
    if master_id:
        conditions.append(Booking.master_id == master_id)
    
    booked_query = select(Booking).where(and_(*conditions))
    booked_result = await tenant_session.execute(booked_query)
    booked = booked_result.scalars().all()
    
    # Проверяем доступность слотов с учетом количества постов
    available_slots = []
    for slot_str in slots:
        slot_time = datetime.strptime(slot_str, "%H:%M").time()
        slot_datetime = datetime.combine(booking_date, slot_time)
        slot_end = slot_datetime + timedelta(minutes=duration)
        
        # Подсчитываем количество занятых постов на это время
        occupied_posts = set()
        bookings_without_post = 0  # Счетчик записей без поста (автоматический статус)
        
        for booking in booked:
            booking_start = datetime.combine(booking.date, booking.time)
            booking_end = datetime.combine(booking.date, booking.end_time)
            
            # Проверяем пересечение времени
            if not (slot_end <= booking_start or slot_datetime >= booking_end):
                # Если у записи есть пост
                if booking.post_id:
                    occupied_posts.add(booking.post_id)
                else:
                    # Запись без поста (автоматический статус) - считаем как занятый один пост
                    bookings_without_post += 1
        
        # Общее количество занятых постов = уникальные посты + записи без поста
        total_occupied = len(occupied_posts) + bookings_without_post
        
        # Слот доступен, если занято меньше постов, чем всего
        is_available = total_occupied < total_posts
        
        if is_available:
            available_slots.append(slot_str)
    
    print(f"✅ Возвращаем {len(available_slots)} свободных слотов из {len(slots)} возможных для даты {booking_date}")
    print(f"📊 Всего активных постов: {total_posts}, логика: слот доступен если занято < {total_posts} постов")
    print(f"📋 Детали: всего временных слотов={len(slots)}, доступных={len(available_slots)}, занятых записей={len(booked)}")
    return available_slots


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Получить информацию о записи"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать записи")
    
    query = select(Booking).options(
        selectinload(Booking.client).selectinload(Client.user),
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
            booking_dict["client_telegram_id"] = None
        booking_dict["client_phone"] = booking.client.phone
        
        # Извлекаем марку автомобиля из комментария заявки, если она там есть
        car_brand_from_comment = None
        if booking.comment and "Марка автомобиля:" in booking.comment:
            car_brand_from_comment = booking.comment.replace("Марка автомобиля:", "").strip()
        
        # Используем марку из комментария заявки, если она есть, иначе из профиля клиента
        booking_dict["client_car_brand"] = car_brand_from_comment if car_brand_from_comment else booking.client.car_brand
        booking_dict["client_car_model"] = booking.client.car_model
    if booking.service:
        booking_dict["service_name"] = booking.service.name
    if booking.master:
        booking_dict["master_name"] = booking.master.full_name
    if booking.post:
        booking_dict["post_number"] = booking.post.number
    
    return BookingResponse.model_validate(booking_dict)


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    booking_data: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Создать новую запись"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать записи")
    
    # Проверяем существование клиента
    client_query = select(Client).where(Client.id == booking_data.client_id)
    client_result = await tenant_session.execute(client_query)
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Генерируем номер записи
    from datetime import datetime
    last_booking = await tenant_session.execute(
        select(Booking).order_by(Booking.id.desc()).limit(1)
    )
    last = last_booking.scalar_one_or_none()
    if last and last.booking_number:
        try:
            last_num = int(last.booking_number.split('-')[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    booking_number = f"BK-{datetime.now().strftime('%Y%m%d')}-{new_num:04d}"
    
    # Вычисляем время окончания
    from datetime import timedelta
    time_obj = booking_data.time
    duration_minutes = booking_data.duration or 30
    end_time = (
        datetime.combine(booking_data.date, time_obj) + timedelta(minutes=duration_minutes)
    ).time()
    
    booking = Booking(
        booking_number=booking_number,
        client_id=booking_data.client_id,
        service_id=booking_data.service_id,
        master_id=booking_data.master_id,
        post_id=booking_data.post_id,
        date=booking_data.date,
        time=booking_data.time,
        duration=duration_minutes,
        end_time=end_time,
        status=booking_data.status or "new",
        amount=booking_data.amount,
        comment=booking_data.comment,
        created_by=current_user.id
    )
    
    db.add(booking)
    await tenant_session.commit()
    
    # Отправляем немедленное уведомление администраторам о новой записи
    try:
        from app.tasks.notifications import notify_admin_new_bookings_task
        # Запускаем задачу немедленно для только что созданной записи
        notify_admin_new_bookings_task.delay()
    except Exception as e:
        print(f"Ошибка отправки уведомления о новой записи: {e}")
    
    # Загружаем связанные данные
    query = select(Booking).options(
        selectinload(Booking.client).selectinload(Client.user),
        selectinload(Booking.service),
        selectinload(Booking.master),
        selectinload(Booking.post)
    ).where(Booking.id == booking.id)
    result = await tenant_session.execute(query)
    booking = result.scalar_one_or_none()
    
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
            booking_dict["client_telegram_id"] = None
        booking_dict["client_phone"] = booking.client.phone
        
        # Извлекаем марку автомобиля из комментария заявки, если она там есть
        car_brand_from_comment = None
        if booking.comment and "Марка автомобиля:" in booking.comment:
            car_brand_from_comment = booking.comment.replace("Марка автомобиля:", "").strip()
        
        # Используем марку из комментария заявки, если она есть, иначе из профиля клиента
        booking_dict["client_car_brand"] = car_brand_from_comment if car_brand_from_comment else booking.client.car_brand
        booking_dict["client_car_model"] = booking.client.car_model
    if booking.service:
        booking_dict["service_name"] = booking.service.name
    if booking.master:
        booking_dict["master_name"] = booking.master.full_name
    if booking.post:
        booking_dict["post_number"] = booking.post.number
    
    return BookingResponse.model_validate(booking_dict)


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_booking(
    booking_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Обновить запись"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять записи")
    
    # Обрабатываем строки date и time в объекты
    processed_data = body.copy()
    if 'date' in processed_data and processed_data['date'] is not None:
        if isinstance(processed_data['date'], str):
            try:
                processed_data['date'] = date.fromisoformat(processed_data['date'])
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Неверный формат даты: {processed_data['date']}")
    
    if 'time' in processed_data and processed_data['time'] is not None:
        if isinstance(processed_data['time'], str):
            try:
                time_str = processed_data['time']
                if len(time_str.split(':')) == 2:
                    time_str = f"{time_str}:00"
                processed_data['time'] = time.fromisoformat(time_str)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Неверный формат времени: {processed_data['time']}")
    
    # Создаем BookingUpdateRequest из обработанных данных
    # Используем model_construct для обхода валидации, так как мы уже обработали данные
    try:
        booking_update = BookingUpdateRequest.model_construct(**processed_data)
    except Exception as e:
        print(f"[ERROR] Ошибка создания BookingUpdateRequest: {e}")
        print(f"[ERROR] processed_data: {processed_data}")
        print(f"[ERROR] Типы данных: date={type(processed_data.get('date'))}, time={type(processed_data.get('time'))}")
        raise HTTPException(status_code=422, detail=f"Ошибка валидации данных: {str(e)}")
    
    # Логируем входящие данные для отладки
    print(f"[DEBUG] update_booking: booking_id={booking_id}")
    print(f"[DEBUG] update_booking: booking_update={booking_update}")
    print(f"[DEBUG] update_booking: booking_update.date={booking_update.date}, type={type(booking_update.date)}")
    print(f"[DEBUG] update_booking: booking_update.time={booking_update.time}, type={type(booking_update.time)}")
    
    query = select(Booking).where(Booking.id == booking_id)
    result = await tenant_session.execute(query)
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # Обновляем поля
    if booking_update.client_id is not None:
        booking.client_id = booking_update.client_id
    if booking_update.service_id is not None:
        booking.service_id = booking_update.service_id
    if booking_update.master_id is not None:
        booking.master_id = booking_update.master_id
    if booking_update.post_id is not None:
        booking.post_id = booking_update.post_id
    
    # Флаг для пересчета end_time
    need_recalculate_end_time = False
    
    if booking_update.date is not None:
        booking.date = booking_update.date
        need_recalculate_end_time = True
    if booking_update.time is not None:
        booking.time = booking_update.time
        need_recalculate_end_time = True
    if booking_update.duration is not None:
        booking.duration = booking_update.duration
        need_recalculate_end_time = True
    
    # Пересчитываем end_time если изменились date, time или duration
    if need_recalculate_end_time:
        from datetime import timedelta
        duration_minutes = booking.duration or 30
        end_time = (
            datetime.combine(booking.date, booking.time) + timedelta(minutes=duration_minutes)
        ).time()
        booking.end_time = end_time
    old_status = booking.status
    new_status = None
    if booking_update.status is not None:
        booking.status = booking_update.status
        new_status = booking_update.status
        # Обновляем соответствующие даты
        if booking_update.status == "confirmed" and not booking.confirmed_at:
            booking.confirmed_at = datetime.utcnow()
        elif booking_update.status == "completed" and not booking.completed_at:
            booking.completed_at = datetime.utcnow()
        elif booking_update.status == "cancelled" and not booking.cancelled_at:
            booking.cancelled_at = datetime.utcnow()
    
    # Обрабатываем оплату: если сумма введена и статус "completed", автоматически помечаем как оплаченную
    # Но только если is_paid не был явно передан (чтобы можно было снять оплату)
    if booking_update.amount is not None:
        booking.amount = booking_update.amount
        # Если сумма введена (> 0) и статус "completed", автоматически помечаем как оплаченную
        # Но только если is_paid не был явно передан в запросе
        if booking_update.amount > 0 and booking.status == "completed" and booking_update.is_paid is None:
            booking.is_paid = True
        # Если сумма очищена (0 или None), сбрасываем оплату
        elif (booking_update.amount == 0 or booking_update.amount is None) and booking_update.is_paid is None:
            booking.is_paid = False
    
    # Явная установка is_paid имеет приоритет
    if booking_update.is_paid is not None:
        booking.is_paid = booking_update.is_paid
    
    if booking_update.payment_method is not None:
        booking.payment_method = booking_update.payment_method
    if booking_update.comment is not None:
        booking.comment = booking_update.comment
    if booking_update.admin_comment is not None:
        booking.admin_comment = booking_update.admin_comment
    
    await tenant_session.commit()
    
    # Отправляем уведомление об изменении статуса (асинхронно, не блокируем ответ)
    notification_sent = False
    if new_status and new_status != old_status:
        print(f"[NOTIFICATION] Статус заявки {booking.id} изменен: {old_status} -> {new_status}")
        try:
            from app.celery_app import celery_app
            from app.tasks.notifications import send_status_change_notification_task
            print(f"[NOTIFICATION] Вызываем задачу send_status_change_notification_task для booking_id={booking.id}, status={new_status}")
            # Используем celery_app для отправки задачи (неблокирующий вызов)
            result = celery_app.send_task(
                'app.tasks.notifications.send_status_change_notification_task',
                args=[booking.id, new_status],
                countdown=0  # Выполнить немедленно
            )
            print(f"[NOTIFICATION] Задача send_status_change_notification_task успешно поставлена в очередь: task_id={result.id}")
            notification_sent = True
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Ошибка отправки уведомления об изменении статуса: {e}")
            print(f"[ERROR] Traceback: {error_trace}")
            # Не устанавливаем notification_sent = True при ошибке
    
    # Загружаем связанные данные
    query = select(Booking).options(
        selectinload(Booking.client).selectinload(Client.user),
        selectinload(Booking.service),
        selectinload(Booking.master),
        selectinload(Booking.post)
    ).where(Booking.id == booking.id)
    result = await tenant_session.execute(query)
    booking = result.scalar_one_or_none()
    
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
        "notification_sent": notification_sent,
    }
    
    if booking.client:
        if booking.client.user:
            booking_dict["client_name"] = f"{booking.client.user.first_name or ''} {booking.client.user.last_name or ''}".strip() or booking.client.full_name
            booking_dict["client_telegram_id"] = booking.client.user.telegram_id
        else:
            booking_dict["client_name"] = booking.client.full_name
            booking_dict["client_telegram_id"] = None
        booking_dict["client_phone"] = booking.client.phone
        
        # Извлекаем марку автомобиля из комментария заявки, если она там есть
        car_brand_from_comment = None
        if booking.comment and "Марка автомобиля:" in booking.comment:
            car_brand_from_comment = booking.comment.replace("Марка автомобиля:", "").strip()
        
        # Используем марку из комментария заявки, если она есть, иначе из профиля клиента
        booking_dict["client_car_brand"] = car_brand_from_comment if car_brand_from_comment else booking.client.car_brand
        booking_dict["client_car_model"] = booking.client.car_model
    if booking.service:
        booking_dict["service_name"] = booking.service.name
    if booking.master:
        booking_dict["master_name"] = booking.master.full_name
    if booking.post:
        booking_dict["post_number"] = booking.post.number
    
    return BookingResponse.model_validate(booking_dict)
