"""Утилиты для работы со временными слотами"""
from datetime import date, time, timedelta, datetime
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from shared.database.models import Booking, BlockedSlot, Post
from bot.config import WORK_START_TIME, WORK_END_TIME, SLOT_DURATION


async def generate_time_slots(
    session: AsyncSession,
    booking_date: date,
    duration: int,
    master_id: int = None,
    company_id: int = None
) -> List[Tuple[time, time]]:
    """Генерация доступных временных слотов на дату с учетом количества постов"""
    import logging
    from sqlalchemy import text
    logger = logging.getLogger(__name__)
    
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
    
    # Устанавливаем search_path для tenant схемы
    if company_id:
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        logger.info(f"✅ Установлен search_path: {schema_name}")
    
    try:
        # Получаем общее количество активных постов
        total_posts_query = select(func.count(Post.id)).where(Post.is_active == True)
        total_posts_result = await session.execute(total_posts_query)
        total_posts = total_posts_result.scalar() or 0
    except Exception as e:
        logger.error(f"Ошибка получения количества постов: {e}", exc_info=True)
        return []  # Возвращаем пустой список при ошибке
    
    if total_posts == 0:
        return []  # Если нет постов, нет доступных слотов
    
    # Парсим время начала и конца работы
    start_hour, start_min = map(int, WORK_START_TIME.split(":"))
    end_hour, end_min = map(int, WORK_END_TIME.split(":"))
    
    work_start = time(start_hour, start_min)
    work_end = time(end_hour, end_min)
    
    slot_duration_minutes = SLOT_DURATION
    
    # Генерируем слоты
    available_slots = []
    current_time = work_start
    
    while True:
        # Вычисляем время окончания слота
        current_datetime = datetime.combine(date.min, current_time)
        end_time = (current_datetime + timedelta(minutes=duration)).time()
        
        # Проверяем, не выходит ли за границы рабочего дня
        if end_time > work_end:
            break
        
        # Проверяем, свободен ли слот (с учетом количества постов)
        is_available = await check_slot_availability(
            session,
            booking_date,
            current_time,
            end_time,
            master_id,
            total_posts
        )
        
        if is_available:
            available_slots.append((current_time, end_time))
        
        # Переходим к следующему слоту
        current_datetime = datetime.combine(date.min, current_time)
        next_time = (current_datetime + timedelta(minutes=slot_duration_minutes)).time()
        current_time = next_time
    
    return available_slots


async def check_slot_availability(
    session: AsyncSession,
    booking_date: date,
    start_time: time,
    end_time: time,
    master_id: int = None,
    total_posts: int = None
) -> bool:
    """Проверить доступность временного слота с учетом количества постов"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Если total_posts не передан, получаем его
        if total_posts is None:
            total_posts_query = select(func.count(Post.id)).where(Post.is_active == True)
            total_posts_result = await session.execute(total_posts_query)
            total_posts = total_posts_result.scalar() or 0
        
        if total_posts == 0:
            return False  # Если нет постов, слот недоступен
        
        # Проверяем существующие записи на это время
        query = select(Booking).where(
            and_(
                Booking.service_date == booking_date,
                Booking.status.in_(["new", "confirmed"]),
                or_(
                    # Запись начинается в нашем слоте
                    and_(
                        Booking.time >= start_time,
                        Booking.time < end_time
                    ),
                    # Запись заканчивается в нашем слоте
                    and_(
                        Booking.end_time > start_time,
                        Booking.end_time <= end_time
                    ),
                    # Запись полностью перекрывает наш слот
                    and_(
                        Booking.time <= start_time,
                        Booking.end_time >= end_time
                    )
                )
            )
        )
        
        if master_id:
            query = query.where(Booking.master_id == master_id)
        
        result = await session.execute(query)
        existing_bookings = result.scalars().all()
    except Exception as e:
        logger.error(f"Ошибка проверки доступности слота: {e}", exc_info=True)
        return False  # При ошибке считаем слот недоступным
    
    # Подсчитываем количество занятых постов
    occupied_posts = set()
    bookings_without_post = 0  # Счетчик записей без поста (автоматический статус)
    
    for booking in existing_bookings:
        if booking.post_id:
            occupied_posts.add(booking.post_id)
        else:
            # Запись без поста (автоматический статус) - считаем как занятый один пост
            bookings_without_post += 1
    
    # Общее количество занятых постов = уникальные посты + записи без поста
    total_occupied = len(occupied_posts) + bookings_without_post
    
    # Слот доступен, если занято меньше постов, чем всего
    is_available = total_occupied < total_posts
    
    if not is_available:
        return False
    
    # Проверяем блокировки
    try:
        block_conditions = [
            BlockedSlot.start_date <= booking_date,
            BlockedSlot.end_date >= booking_date,
            BlockedSlot.block_type == "full_service"
        ]
        
        if master_id:
            block_conditions.append(
                or_(
                    BlockedSlot.block_type == "full_service",
                    and_(
                        BlockedSlot.block_type == "master",
                        BlockedSlot.master_id == master_id
                    )
                )
            )
        else:
            block_conditions.append(BlockedSlot.block_type == "full_service")
        
        result = await session.execute(
            select(BlockedSlot).where(and_(*block_conditions))
        )
        blocked = result.scalar_one_or_none()
        
        if blocked:
            # Если блокировка на весь день
            if not blocked.start_time:
                return False
            # Если блокировка перекрывает наш слот
            if blocked.start_time and blocked.end_time:
                if blocked.start_time <= start_time and blocked.end_time >= end_time:
                    return False
    except Exception as e:
        logger.error(f"Ошибка проверки блокировок: {e}", exc_info=True)
        # При ошибке проверки блокировок считаем слот доступным (не блокируем)
        pass
    
    return True

