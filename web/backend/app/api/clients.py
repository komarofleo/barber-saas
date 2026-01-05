from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload
from typing import Optional

from ..database import get_db
from .auth import get_current_user
from shared.database.models import User, Client, Booking
from ..schemas.client import ClientResponse, ClientListResponse, ClientCreateRequest

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
async def get_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список клиентов"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать клиентов")
    
    query = select(Client).options(
        selectinload(Client.user)
    )
    
    # Подсчет общего количества (до применения фильтров)
    count_query = select(func.count(Client.id))
    
    # Поиск по имени, телефону, госномеру
    if search:
        search_term = f"%{search}%"
        # Используем left join, чтобы не исключать клиентов без user
        query = query.outerjoin(User).where(
            or_(
                Client.full_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.car_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
        # Применяем те же условия для подсчета
        count_query = count_query.outerjoin(User).where(
            or_(
                Client.full_name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.car_number.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term)
            )
        )
    
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(Client.full_name)
    
    result = await db.execute(query)
    clients = result.scalars().all()
    
    # Формируем ответы
    items = []
    for client in clients:
        await db.refresh(client, ["user"])
        
        # Получаем все заявки клиента для извлечения марок из комментариев
        bookings_query = select(Booking).where(Booking.client_id == client.id)
        bookings_result = await db.execute(bookings_query)
        bookings = bookings_result.scalars().all()
        
        # Извлекаем марки из комментариев заявок
        car_brands_from_bookings = set()
        for booking in bookings:
            if booking.comment and "Марка автомобиля:" in booking.comment:
                car_brand = booking.comment.replace("Марка автомобиля:", "").strip()
                # Если есть перенос строки, берем только первую часть (марку)
                if car_brand and "\n" in car_brand:
                    car_brand = car_brand.split("\n")[0].strip()
                # Фильтруем некорректные значения
                if car_brand and len(car_brand) >= 2 and len(car_brand) <= 50:
                    # Игнорируем значения, которые начинаются с "/" или содержат известные некорректные значения
                    invalid_prefixes = ["/", "📋", "⏭️", "❌"]
                    if not any(car_brand.startswith(prefix) for prefix in invalid_prefixes):
                        # Убираем лишние пробелы
                        car_brand = car_brand.strip()
                        if car_brand:
                            car_brands_from_bookings.add(car_brand)
        
        # Используем марки из заявок, если они есть, иначе марку из профиля клиента
        if car_brands_from_bookings:
            # Объединяем все уникальные марки через запятую
            car_brand_display = ", ".join(sorted(car_brands_from_bookings))
        else:
            # Если марок из заявок нет, используем марку из профиля клиента
            car_brand_display = client.car_brand
        
        client_dict = {
            "id": client.id,
            "user_id": client.user_id,
            "full_name": client.full_name,
            "phone": client.phone,
            "car_brand": car_brand_display,  # Используем марки из заявок или из профиля
            "car_model": client.car_model,
            "car_year": None,  # Поле отсутствует в модели БД
            "car_number": client.car_number,
            "total_visits": client.total_visits,
            "total_amount": float(client.total_amount) if client.total_amount else None,
            "created_at": client.created_at,
            "user_telegram_id": None,
            "user_first_name": None,
            "user_last_name": None,
            "user_is_admin": None,  # Статус администратора пользователя
        }
        
        if client.user:
            client_dict["user_telegram_id"] = client.user.telegram_id
            client_dict["user_first_name"] = client.user.first_name
            client_dict["user_last_name"] = client.user.last_name
            client_dict["user_is_admin"] = client.user.is_admin
        
        items.append(ClientResponse.model_validate(client_dict))
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    client_data: ClientCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать нового клиента"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать клиентов")
    
    # Проверяем, существует ли уже клиент с таким телефоном
    existing_client = await db.execute(
        select(Client).where(Client.phone == client_data.phone)
    )
    existing = existing_client.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Клиент с таким телефоном уже существует")
    
    # Ищем или создаем пользователя по телефону
    user_query = select(User).where(User.phone == client_data.phone)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        # Создаем нового пользователя
        # Генерируем telegram_id как отрицательное число для клиентов без Telegram
        # Используем хеш от телефона для уникальности
        import hashlib
        phone_hash = int(hashlib.md5(client_data.phone.encode()).hexdigest()[:8], 16)
        # Делаем отрицательным, чтобы не конфликтовать с реальными telegram_id
        telegram_id = -abs(phone_hash) % (10**10)  # Ограничиваем до 10 цифр
        
        # Проверяем уникальность telegram_id
        while True:
            existing_user = await db.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            if not existing_user.scalar_one_or_none():
                break
            telegram_id = -abs(telegram_id + 1) % (10**10)
        
        # Извлекаем имя и фамилию из full_name
        name_parts = client_data.full_name.strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else None
        last_name = name_parts[1] if len(name_parts) > 1 else None
        
        user = User(
            telegram_id=telegram_id,
            phone=client_data.phone,
            first_name=first_name,
            last_name=last_name,
            is_admin=False,
            is_master=False
        )
        db.add(user)
        await db.flush()  # Получаем ID пользователя
    
    # Проверяем, не связан ли уже этот пользователь с клиентом
    existing_client_by_user = await db.execute(
        select(Client).where(Client.user_id == user.id)
    )
    if existing_client_by_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="У этого пользователя уже есть профиль клиента")
    
    # Создаем клиента
    client = Client(
        user_id=user.id,
        full_name=client_data.full_name,
        phone=client_data.phone,
        car_brand=client_data.car_brand,
        car_model=client_data.car_model,
        car_number=client_data.car_number,
        total_visits=0,
        total_amount=0
    )
    
    db.add(client)
    await db.commit()
    await db.refresh(client)
    await db.refresh(client, ["user"])
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "user_id": client.user_id,
        "full_name": client.full_name,
        "phone": client.phone,
        "car_brand": client.car_brand,
        "car_model": client.car_model,
        "car_year": None,  # Поле отсутствует в модели БД
        "car_number": client.car_number,
        "total_visits": client.total_visits,
        "total_amount": float(client.total_amount) if client.total_amount else None,
        "created_at": client.created_at,
        "user_telegram_id": None,
        "user_first_name": None,
        "user_last_name": None,
        "user_is_admin": None,  # Статус администратора пользователя
    }
    
    if client.user:
        client_dict["user_telegram_id"] = client.user.telegram_id
        client_dict["user_first_name"] = client.user.first_name
        client_dict["user_last_name"] = client.user.last_name
        client_dict["user_is_admin"] = client.user.is_admin
    
    return ClientResponse.model_validate(client_dict)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить данные клиента"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут обновлять клиентов")
    
    # Получаем клиента
    result = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    
    # Обновляем поля
    if "full_name" in client_data:
        client.full_name = client_data["full_name"]
    if "phone" in client_data:
        client.phone = client_data["phone"]
    if "car_brand" in client_data:
        client.car_brand = client_data["car_brand"] if client_data["car_brand"] else None
    if "car_model" in client_data:
        client.car_model = client_data["car_model"] if client_data["car_model"] else None
    if "car_number" in client_data:
        client.car_number = client_data["car_number"] if client_data["car_number"] else None
    
    await db.commit()
    await db.refresh(client)
    await db.refresh(client, ["user"])
    
    # Формируем ответ
    client_dict = {
        "id": client.id,
        "user_id": client.user_id,
        "full_name": client.full_name,
        "phone": client.phone,
        "car_brand": client.car_brand,
        "car_model": client.car_model,
        "car_year": None,
        "car_number": client.car_number,
        "total_visits": client.total_visits,
        "total_amount": float(client.total_amount) if client.total_amount else None,
        "created_at": client.created_at,
        "user_telegram_id": None,
        "user_first_name": None,
        "user_last_name": None,
    }
    
    if client.user:
        client_dict["user_telegram_id"] = client.user.telegram_id
        client_dict["user_first_name"] = client.user.first_name
        client_dict["user_last_name"] = client.user.last_name
    
    return ClientResponse.model_validate(client_dict)

