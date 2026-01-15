from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_, or_, text
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import os
import shutil
from pathlib import Path

from ..database import DATABASE_URL
from app.deps.tenant import get_tenant_db
from .auth import get_current_user
from shared.database.models import User, Broadcast, Client, Booking
from ..schemas.broadcast import BroadcastResponse, BroadcastListResponse, BroadcastCreateRequest
from aiogram import Bot

router = APIRouter(prefix="/api/broadcasts", tags=["broadcasts"])

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Директория для хранения загруженных изображений
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "broadcasts")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def send_broadcast_task(company_id: int, broadcast_id: int, db_url: str):
    """Фоновая задача для отправки рассылки"""
    # Создаем движок для этой задачи
    engine = create_async_engine(db_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    bot = Bot(token=BOT_TOKEN)
    
    try:
        async with async_session_maker() as session:
            # Переключаемся на tenant схему для фоновой задачи.
            # ВАЖНО: в фоне нет dependency/middleware, поэтому search_path задаём явно.
            await session.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
            # Получаем рассылку
            result = await session.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()
            
            if not broadcast:
                print(f"Рассылка {broadcast_id} не найдена")
                return
            
            # Обновляем статус на "sending"
            broadcast.status = "sending"
            broadcast.total_sent = 0
            broadcast.total_errors = 0
            await session.commit()
            
            # Получаем список получателей на основе target_audience и filter_params
            recipients = []
            
            if broadcast.target_audience == "all":
                # Все пользователи с telegram_id
                result = await session.execute(
                    select(User).where(User.telegram_id.isnot(None))
                )
                recipients = result.scalars().all()
                
            elif broadcast.target_audience == "active":
                # Пользователи с активными записями
                result = await session.execute(
                    select(User)
                    .join(Client, User.id == Client.user_id)
                    .join(Booking, Client.id == Booking.client_id)
                    .where(
                        and_(
                            User.telegram_id.isnot(None),
                            Booking.status.in_(["new", "confirmed"])
                        )
                    )
                    .distinct()
                )
                recipients = result.scalars().all()
                
            elif broadcast.target_audience == "new":
                # Новые пользователи (созданные за последние 30 дней)
                from datetime import timedelta
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                result = await session.execute(
                    select(User).where(
                        and_(
                            User.telegram_id.isnot(None),
                            User.created_at >= cutoff_date
                        )
                    )
                )
                recipients = result.scalars().all()
                
            elif broadcast.target_audience == "by_service" and broadcast.filter_params:
                # Пользователи по услуге
                service_id = broadcast.filter_params.get("service_id")
                if service_id:
                    result = await session.execute(
                        select(User)
                        .join(Client, User.id == Client.user_id)
                        .join(Booking, Client.id == Booking.client_id)
                        .where(
                            and_(
                                User.telegram_id.isnot(None),
                                Booking.service_id == service_id
                            )
                        )
                        .distinct()
                    )
                    recipients = result.scalars().all()
            
            elif broadcast.target_audience == "selected_clients" and broadcast.filter_params:
                # Выбранные клиенты
                client_ids = broadcast.filter_params.get("client_ids", [])
                if client_ids:
                    result = await session.execute(
                        select(User)
                        .join(Client, User.id == Client.user_id)
                        .where(
                            and_(
                                User.telegram_id.isnot(None),
                                Client.id.in_(client_ids)
                            )
                        )
                    )
                    recipients = result.scalars().all()
            
            # Отправляем сообщения
            for user in recipients:
                try:
                    # Отправляем текст
                    if broadcast.image_path:
                        # Если есть изображение, отправляем фото с подписью
                        from aiogram.types import FSInputFile
                        photo = FSInputFile(broadcast.image_path)
                        await bot.send_photo(
                            chat_id=user.telegram_id,
                            photo=photo,
                            caption=broadcast.text
                        )
                    else:
                        # Отправляем только текст
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=broadcast.text
                        )
                    
                    broadcast.total_sent += 1
                    
                except Exception as e:
                    print(f"Ошибка отправки рассылки пользователю {user.id}: {e}")
                    broadcast.total_errors += 1
            
            # Обновляем статус
            broadcast.status = "completed"
            broadcast.sent_at = datetime.utcnow()
            await session.commit()
            
    except Exception as e:
        print(f"Ошибка в send_broadcast_task: {e}")
        # Обновляем статус на "failed"
        async with async_session_maker() as session:
            await session.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
            result = await session.execute(
                select(Broadcast).where(Broadcast.id == broadcast_id)
            )
            broadcast = result.scalar_one_or_none()
            if broadcast:
                broadcast.status = "failed"
                await session.commit()
    finally:
        await bot.session.close()
        await engine.dispose()

@router.get("", response_model=BroadcastListResponse)
async def get_broadcasts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список рассылок"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать рассылки")
    
    query = select(Broadcast)
    
    if status:
        query = query.where(Broadcast.status == status)
    
    query = query.order_by(Broadcast.created_at.desc())
    
    result = await db.execute(query)
    all_broadcasts = result.scalars().all()
    
    total = len(all_broadcasts)
    start = (page - 1) * page_size
    end = start + page_size
    broadcasts = all_broadcasts[start:end]
    
    items = [BroadcastResponse.model_validate(b) for b in broadcasts]
    
    return BroadcastListResponse(items=items, total=total)

@router.post("", response_model=BroadcastResponse, status_code=201)
async def create_broadcast(
    request: Request,
    broadcast_data: BroadcastCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Создать рассылку"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут создавать рассылки")
    
    broadcast = Broadcast(
        text=broadcast_data.text,
        image_path=broadcast_data.image_path,
        target_audience=broadcast_data.target_audience,
        filter_params=broadcast_data.filter_params,
        status="pending",
        created_by=current_user.id,
    )
    
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)
    
    # Запускаем фоновую задачу отправки
    company_id = int(getattr(request.state, "company_id", 0) or 0)
    background_tasks.add_task(send_broadcast_task, company_id, broadcast.id, DATABASE_URL)
    
    return BroadcastResponse.model_validate(broadcast)

@router.get("/{broadcast_id}", response_model=BroadcastResponse)
async def get_broadcast(
    broadcast_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить детали рассылки"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать рассылки")
    
    result = await db.execute(select(Broadcast).where(Broadcast.id == broadcast_id))
    broadcast = result.scalar_one_or_none()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    
    return BroadcastResponse.model_validate(broadcast)

@router.delete("/{broadcast_id}", status_code=204)
async def delete_broadcast(
    broadcast_id: int,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить рассылку"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут удалять рассылки")
    
    result = await db.execute(select(Broadcast).where(Broadcast.id == broadcast_id))
    broadcast = result.scalar_one_or_none()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Рассылка не найдена")
    
    # Удаляем изображение если есть
    if broadcast.image_path and os.path.exists(broadcast.image_path):
        try:
            os.remove(broadcast.image_path)
        except Exception as e:
            print(f"Ошибка удаления изображения: {e}")
    
    await db.delete(broadcast)
    await db.commit()
    
    return None

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Загрузить изображение для рассылки"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут загружать изображения")
    
    # Проверяем тип файла
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")
    
    # Генерируем уникальное имя файла
    file_ext = Path(file.filename).suffix if file.filename else '.jpg'
    file_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{current_user.id}{file_ext}"
    file_path = UPLOAD_DIR / file_name
    
    # Сохраняем файл
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"image_path": str(file_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")



