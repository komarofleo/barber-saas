"""
API для работы с мастерами (МУЛЬТИ-ТЕНАНТНАЯ ВЕРСИЯ).

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
from sqlalchemy import select, and_, or_, func, text, delete
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.deps.tenant import get_tenant_db
from app.schemas.master import (
    MasterResponse, MasterListResponse,
    MasterCreateRequest, MasterUpdateRequest
)
from app.schemas.booking import BookingResponse
from datetime import date
from shared.database.models import User, Master, Booking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/masters", tags=["masters"])

@router.get("", response_model=MasterListResponse)
async def get_masters(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить список мастеров.
    
    Аргументы:
        page: номер страницы
        page_size: количество элементов на странице
        search: строка для поиска
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать мастеров")
    
    query = select(Master)
    
    # Фильтры
    if search:
        search_term = f"%{search}%"
        query = query.where(Master.full_name.ilike(search_term))
    
    # Подсчет общего количества
    count_query = select(func.count(Master.id))
    total = await tenant_session.scalar(count_query) or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Master.full_name)
    
    result = await tenant_session.execute(query)
    masters = result.scalars().all()
    
    company_id = getattr(request.state, "company_id", None)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"📊 Запрос мастеров: total={total}, page={page}, page_size={page_size}, company_id={company_id}")
    
    # Формируем ответы с дополнительными данными
    items = []
    for master in masters:
        # Считаем количество записей для мастера
        booking_count = await tenant_session.scalar(
            select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master.id)
        )
        
        master_dict = {
            "id": master.id,
            "user_id": master.user_id,
            "full_name": master.full_name,
            "phone": master.phone,
            "telegram_id": master.telegram_id,
            "specialization": master.specialization,
            "is_universal": master.is_universal,
            "booking_count": booking_count or 0,
            "created_at": master.created_at,
            "updated_at": master.updated_at,
        }
        items.append(MasterResponse.model_validate(master_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "company_id": company_id,
    }


@router.get("/{master_id}", response_model=MasterResponse)
async def get_master(
    master_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о мастере.
    
    Аргументы:
        master_id: ID мастера
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать мастеров")

    query = select(Master).where(Master.id == master_id)
    result = await tenant_session.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"🔍 Запрос мастера: master_id={master_id}, company_id={company_id}")
    
    # Считаем количество записей для мастера
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master.id)
    )
    
    # Формируем ответ
    master_dict = {
        "id": master.id,
        "user_id": master.user_id,
        "full_name": master.full_name,
        "phone": master.phone,
        "telegram_id": master.telegram_id,
        "specialization": master.specialization,
        "is_universal": master.is_universal,
        "booking_count": booking_count or 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
    }
    
    return MasterResponse.model_validate(master_dict)


@router.post("", response_model=MasterResponse, status_code=201)
async def create_master(
    master_data: MasterCreateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать нового мастера.
    
    Аргументы:
        master_data: данные мастера
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать мастеров")
    
    # Нормализуем значения для проверки дублей
    full_name = master_data.full_name.strip()
    phone = master_data.phone.strip() if master_data.phone else None

    # Проверяем, существует ли мастер с таким именем и телефоном (если указан)
    duplicate_query = select(Master).where(func.lower(Master.full_name) == full_name.lower())
    if phone:
        duplicate_query = duplicate_query.where(Master.phone == phone)

    result = await tenant_session.execute(duplicate_query)
    existing_master = result.scalar_one_or_none()

    if existing_master:
        raise HTTPException(
            status_code=400,
            detail="Мастер с таким ФИО и телефоном уже существует"
            if phone
            else "Мастер с таким ФИО уже существует"
        )
    
    # Создаем нового мастера
    master = Master(
        user_id=master_data.user_id,
        full_name=full_name,
        phone=phone,
        telegram_id=master_data.telegram_id,
        specialization=master_data.specialization,
        is_universal=master_data.is_universal if master_data.is_universal is not None else True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    tenant_session.add(master)
    await tenant_session.flush()
    await tenant_session.commit()
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Создан мастер: name={master.full_name}, phone={master.phone}, company_id={company_id}")
    
    # Отправляем уведомление
    # TODO: Создать Celery задачу для уведомления о новом мастере
    
    # Формируем ответ
    master_dict = {
        "id": master.id,
        "user_id": master.user_id,
        "full_name": master.full_name,
        "phone": master.phone,
        "telegram_id": master.telegram_id,
        "specialization": master.specialization,
        "is_universal": master.is_universal,
        "booking_count": 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
    }
    
    return MasterResponse.model_validate(master_dict)


@router.post("/from-client/{client_id}", response_model=MasterResponse, status_code=201)
async def create_master_from_client(
    client_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Создать мастера на основе клиента (по user_id и telegram_id).
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут назначать мастеров")

    result = await tenant_session.execute(
        text("""
            SELECT c.id, c.user_id, c.full_name, c.phone, u.telegram_id
            FROM clients c
            LEFT JOIN users u ON u.id = c.user_id
            WHERE c.id = :client_id
        """),
        {"client_id": client_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    client_user_id = row[1]
    client_full_name = row[2]
    client_phone = row[3]
    client_telegram_id = row[4]

    if not client_user_id:
        raise HTTPException(
            status_code=400,
            detail="Клиент не связан с пользователем. Попросите его написать боту /start",
        )

    existing_master_result = await tenant_session.execute(
        select(Master).where(
            or_(
                Master.user_id == client_user_id,
                Master.telegram_id == client_telegram_id,
            )
        )
    )
    existing_master = existing_master_result.scalar_one_or_none()
    if existing_master:
        raise HTTPException(status_code=400, detail="Мастер уже назначен")

    master = Master(
        user_id=client_user_id,
        full_name=client_full_name,
        phone=client_phone,
        telegram_id=client_telegram_id,
        specialization=None,
        is_universal=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    tenant_session.add(master)
    await tenant_session.flush()

    await tenant_session.execute(
        text("UPDATE users SET role = :role WHERE id = :user_id"),
        {"role": "master", "user_id": client_user_id},
    )

    await tenant_session.commit()

    company_id = getattr(request.state, "company_id", None)
    logger.info(
        f"✅ Назначен мастер из клиента: client_id={client_id}, master_id={master.id}, company_id={company_id}"
    )

    master_dict = {
        "id": master.id,
        "user_id": master.user_id,
        "full_name": master.full_name,
        "phone": master.phone,
        "telegram_id": master.telegram_id,
        "specialization": master.specialization,
        "is_universal": master.is_universal,
        "booking_count": 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
    }

    return MasterResponse.model_validate(master_dict)


@router.patch("/{master_id}", response_model=MasterResponse)
async def update_master(
    master_id: int,
    master_data: MasterUpdateRequest,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Обновить информацию о мастере.
    
    Аргументы:
        master_id: ID мастера
        master_data: данные для обновления
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять мастеров")
    
    # Проверяем существование мастера
    query = select(Master).where(Master.id == master_id)
    result = await tenant_session.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    if master_data.full_name is not None:
        master.full_name = master_data.full_name
    if master_data.phone is not None:
        master.phone = master_data.phone
    if master_data.specialization is not None:
        master.specialization = master_data.specialization
    if master_data.telegram_id is not None:
        master.telegram_id = master_data.telegram_id
    if master_data.user_id is not None:
        master.user_id = master_data.user_id
    if master_data.is_universal is not None:
        master.is_universal = master_data.is_universal
    
    master.updated_at = datetime.utcnow()
    await tenant_session.commit()
    await tenant_session.refresh(master)
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Обновлен мастер: master_id={master_id}, company_id={company_id}")
    
    # Формируем ответ
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master.id)
    )
    
    master_dict = {
        "id": master.id,
        "user_id": master.user_id,
        "full_name": master.full_name,
        "phone": master.phone,
        "telegram_id": master.telegram_id,
        "specialization": master.specialization,
        "is_universal": master.is_universal,
        "booking_count": booking_count or 0,
        "created_at": master.created_at,
        "updated_at": master.updated_at,
    }
    
    return MasterResponse.model_validate(master_dict)


@router.delete("/{master_id}", status_code=204)
async def delete_master(
    master_id: int,
    request: Request,
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """
    Удалить мастера.
    
    Аргументы:
        master_id: ID мастера
        company_id: ID компании для мульти-тенантности
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять мастеров")
    
    # Проверяем существование мастера
    query = select(Master).where(Master.id == master_id)
    result = await tenant_session.execute(query)
    master = result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Проверяем, используются ли записи с этим мастером
    booking_count = await tenant_session.scalar(
        select(func.count(Booking.id)).select_from(Booking).where(Booking.master_id == master_id)
    )
    
    if booking_count and booking_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить мастера '{master.full_name}', так как с ним связаны {booking_count} записей"
        )
    
    # Удаляем мастера
    await tenant_session.execute(delete(Master).where(Master.id == master_id))
    await tenant_session.commit()
    
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"✅ Удален мастер: master_id={master_id}, company_id={company_id}")
    
    return None


@router.get("/{master_id}/schedule")
async def get_master_schedule(
    request: Request,
    master_id: int,
    schedule_date: date = Query(..., alias="date"),
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить расписание мастера на дату (список записей на день)"""
    # Проверяем существование мастера
    master_query = select(Master).where(Master.id == master_id)
    master_result = await tenant_session.execute(master_query)
    master = master_result.scalar_one_or_none()
    
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")
    
    # Проверяем права доступа: админ может видеть любое расписание, мастер - только свое
    if not current_user.is_admin:
        # Если пользователь не админ, проверяем, что он является этим мастером
        if master.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Вы можете просматривать только свое расписание")
    
    # Получаем записи мастера на дату через прямой SQL
    bookings_query = text("""
        SELECT b.id, b.booking_number, b.client_id, b.service_id, b.master_id, b.post_id,
               b.service_date, b.time, b.duration, b.end_time, b.status, b.amount, b.is_paid,
               b.payment_method, b.comment, b.admin_comment, b.created_at,
               b.confirmed_at, b.completed_at, b.cancelled_at,
               c.full_name as client_name, c.phone as client_phone,
               s.name as service_name, p.number as post_number
        FROM bookings b
        LEFT JOIN clients c ON b.client_id = c.id
        LEFT JOIN services s ON b.service_id = s.id
        LEFT JOIN posts p ON b.post_id = p.id
        WHERE b.master_id = :master_id
          AND b.service_date = :schedule_date
          AND b.status IN ('confirmed', 'new')
        ORDER BY b.time ASC
    """)
    
    bookings_result = await tenant_session.execute(
        bookings_query,
        {"master_id": master_id, "schedule_date": schedule_date}
    )
    bookings_rows = bookings_result.fetchall()
    
    # Формируем ответ
    items = []
    for row in bookings_rows:
        booking_dict = {
            "id": row[0],
            "booking_number": row[1],
            "client_id": row[2],
            "service_id": row[3],
            "master_id": row[4],
            "post_id": row[5],
            "service_date": row[6],
            "time": row[7],
            "duration": row[8],
            "end_time": row[9],
            "status": row[10],
            "amount": row[11],
            "is_paid": row[12] or False,
            "payment_method": row[13],
            "comment": row[14],
            "admin_comment": row[15],
            "created_at": row[16],
            "confirmed_at": row[17],
            "completed_at": row[18],
            "cancelled_at": row[19],
            "client_name": row[20],
            "client_phone": row[21],
            "client_telegram_id": None,
            "client_car_brand": None,
            "client_car_model": None,
            "service_name": row[22],
            "master_name": master.full_name,
            "post_number": row[23],
        }
        
        items.append(BookingResponse.model_validate(booking_dict))
    
    return {
        "master_id": master.id,
        "master_name": master.full_name,
        "date": schedule_date.isoformat(),
        "bookings": items
    }


@router.get("/work-orders/all")
async def get_all_work_orders(
    request: Request,
    schedule_date: date = Query(..., alias="date"),
    company_id: Optional[int] = Query(None, description="ID компании для tenant сессии"),
    tenant_session: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить все лист-наряды всех мастеров на дату (только для админов)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать все лист-наряды")
    
    logger = logging.getLogger(__name__)
    company_id = getattr(request.state, "company_id", None)
    logger.info(f"📋 Запрос лист-нарядов: date={schedule_date}, company_id={company_id}, user_id={current_user.id}")
    
    # Сначала проверяем количество записей в БД на эту дату
    count_query = text("""
        SELECT COUNT(*) as total
        FROM bookings
        WHERE service_date = :schedule_date
    """)
    count_result = await tenant_session.execute(count_query, {"schedule_date": schedule_date})
    total_count = count_result.scalar()
    logger.info(f"📊 Всего записей в БД на {schedule_date}: {total_count}")
    
    # Получаем все записи на дату через прямой SQL
    # Показываем все записи (как в календаре), но группируем по мастерам
    # Записи без мастера будут в отдельной группе "Без мастера"
    bookings_query = text("""
        SELECT b.id, b.booking_number, b.client_id, b.service_id, b.master_id, b.post_id,
               b.service_date, b.time, b.duration, b.end_time, b.status, b.amount, b.is_paid,
               b.payment_method, b.comment, b.admin_comment, b.created_at,
               b.confirmed_at, b.completed_at, b.cancelled_at,
               c.full_name as client_name, c.phone as client_phone,
               s.name as service_name, p.number as post_number,
               COALESCE(m.full_name, 'Без мастера') as master_name
        FROM bookings b
        LEFT JOIN clients c ON b.client_id = c.id
        LEFT JOIN services s ON b.service_id = s.id
        LEFT JOIN posts p ON b.post_id = p.id
        LEFT JOIN masters m ON b.master_id = m.id
        WHERE b.service_date = :schedule_date
        ORDER BY 
          CASE WHEN m.full_name IS NULL THEN 1 ELSE 0 END,
          m.full_name ASC NULLS LAST, 
          b.time ASC
    """)
    
    bookings_result = await tenant_session.execute(
        bookings_query,
        {"schedule_date": schedule_date}
    )
    bookings_rows = bookings_result.fetchall()
    logger.info(f"📊 Количество записей после выполнения запроса: {len(bookings_rows)}")
    
    # Формируем ответ, группируя по мастерам
    masters_dict: dict[int, dict] = {}
    
    for row in bookings_rows:
        # Правильная индексация полей из SELECT запроса:
        # 0: b.id, 1: booking_number, 2: client_id, 3: service_id, 4: master_id, 5: post_id,
        # 6: date, 7: time, 8: duration, 9: end_time, 10: status, 11: amount, 12: is_paid,
        # 13: payment_method, 14: comment, 15: admin_comment, 16: created_at,
        # 17: confirmed_at, 18: completed_at, 19: cancelled_at,
        # 20: client_name, 21: client_phone, 22: service_name, 23: post_number, 24: master_name
        master_id = row[4]  # b.master_id (может быть None)
        master_name = row[24] if len(row) > 24 else "Без мастера"  # COALESCE(m.full_name, 'Без мастера')
        
        # Используем специальный ключ для записей без мастера
        dict_key = master_id if master_id is not None else -1
        
        if dict_key not in masters_dict:
            masters_dict[dict_key] = {
                "master_id": master_id,
                "master_name": str(master_name) if master_name else "Без мастера",
                "bookings": []
            }
        
        booking_dict = {
            "id": row[0],
            "booking_number": row[1],
            "client_id": row[2],
            "service_id": row[3],
            "master_id": row[4],
            "post_id": row[5],
            "service_date": row[6],
            "time": row[7],
            "duration": row[8],
            "end_time": row[9],
            "status": row[10],
            "amount": row[11],
            "is_paid": row[12] or False,
            "payment_method": row[13],
            "comment": row[14],
            "admin_comment": row[15],
            "created_at": row[16],
            "confirmed_at": row[17],
            "completed_at": row[18],
            "cancelled_at": row[19],
            "client_name": row[20],
            "client_phone": row[21],
            "client_telegram_id": None,
            "client_car_brand": None,
            "client_car_model": None,
            "service_name": row[22],
            "master_name": str(master_name) if master_name else "Неизвестный мастер",
            "post_number": row[23] if row[23] is not None else None,
        }
        
        masters_dict[dict_key]["bookings"].append(BookingResponse.model_validate(booking_dict))
    
    # Преобразуем в список
    masters_list = list(masters_dict.values())
    
    # Логируем результат перед возвратом
    logger.info(f"✅ Подготовка ответа: {len(masters_list)} мастеров")
    for master in masters_list:
        logger.info(f"  - {master['master_name']}: {len(master['bookings'])} записей")
    
    return {
        "date": schedule_date.isoformat(),
        "masters": masters_list
    }

