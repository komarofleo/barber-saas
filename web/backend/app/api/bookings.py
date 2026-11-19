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
from app.models.public_models import Company
from sqlalchemy.orm import selectinload, load_only
from app.services.tenant_service import get_tenant_service
from jose import jwt
from app.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from aiogram import Bot

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


async def get_client_telegram_id(tenant_session: AsyncSession, company_id: int, client: Client) -> Optional[int]:
    """Получить telegram_id клиента из tenant схемы users"""
    if not client or not client.user_id:
        return None
    
    try:
        user_result = await tenant_session.execute(
            text(f'SELECT telegram_id FROM "tenant_{company_id}".users WHERE id = :user_id'),
            {"user_id": client.user_id}
        )
        user_row = user_result.fetchone()
        if user_row and user_row[0]:
            return user_row[0]
    except Exception as e:
        logger.warning(f"⚠️ Ошибка получения telegram_id для user_id={client.user_id}: {e}")
    
    return None


async def notify_admins_about_new_booking(company_id: int, booking_id: int, tenant_session: AsyncSession) -> bool:
    """Отправить уведомление администраторам о новой записи
    
    Args:
        company_id: ID компании
        booking_id: ID созданной записи
        tenant_session: Сессия БД с установленным search_path для tenant схемы
    
    Returns:
        True если хотя бы одно уведомление отправлено успешно, False в противном случае
    """
    from sqlalchemy import text as sql_text
    
    logger.info(f"📤 [NOTIFY_ADMIN] === НАЧАЛО ОТПРАВКИ УВЕДОМЛЕНИЯ АДМИНАМ ===")
    logger.info(f"📤 [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking_id}")
    
    schema_name = f"tenant_{company_id}"
    original_search_path = None
    
    try:
        # Сохраняем текущий search_path
        path_result = await tenant_session.execute(sql_text("SHOW search_path"))
        original_search_path = path_result.scalar()
        logger.info(f"📤 [NOTIFY_ADMIN] Текущий search_path: {original_search_path}")
        
        # Получаем компанию и bot token из public схемы
        await tenant_session.execute(sql_text('SET search_path TO public'))
        company_result = await tenant_session.execute(
            sql_text('SELECT id, name, telegram_bot_token FROM public.companies WHERE id = :company_id'),
            {"company_id": company_id}
        )
        company_row = company_result.fetchone()
        
        if not company_row or not company_row[2]:
            logger.warning(f"⚠️ [NOTIFY_ADMIN] Компания {company_id} не найдена или нет bot token")
            return False
        
        bot_token = company_row[2]
        company_name = company_row[1]
        logger.info(f"📤 [NOTIFY_ADMIN] Компания найдена: name={company_name}, bot_token={bot_token[:10]}...")
        
        # Возвращаем search_path для tenant схемы
        await tenant_session.execute(sql_text(f'SET search_path TO "{schema_name}", public'))
        
        # Загружаем запись с клиентом через прямой SQL
        booking_result = await tenant_session.execute(
            sql_text(f"""
                SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id
                FROM "{schema_name}".bookings b
                WHERE b.id = :booking_id
            """),
            {"booking_id": booking_id}
        )
        booking_row = booking_result.fetchone()
        
        if not booking_row:
            logger.error(f"❌ [NOTIFY_ADMIN] Запись {booking_id} не найдена в схеме {schema_name}")
            return False
        
        # Загружаем клиента
        client_result = await tenant_session.execute(
            sql_text(f"""
                SELECT id, user_id, full_name, phone
                FROM "{schema_name}".clients
                WHERE id = :client_id
            """),
            {"client_id": booking_row[4]}  # client_id из booking
        )
        client_row = client_result.fetchone()
        
        if not client_row:
            logger.error(f"❌ [NOTIFY_ADMIN] Клиент {booking_row[4]} не найден")
            return False
        
        # Загружаем услугу
        service_result = await tenant_session.execute(
            sql_text(f"""
                SELECT id, name, price, duration
                FROM "{schema_name}".services
                WHERE id = :service_id
            """),
            {"service_id": booking_row[5]}  # service_id из booking
        )
        service_row = service_result.fetchone()
        
        # Получаем всех администраторов с Telegram ID
        logger.info(f"📤 [NOTIFY_ADMIN] Ищем администраторов в {schema_name}.users")
        logger.info(f"📤 [NOTIFY_ADMIN] Условия: role='admin' AND telegram_id IS NOT NULL")
        
        admins_result = await tenant_session.execute(
            sql_text(f"""
                SELECT id, telegram_id, username, full_name, phone, role
                FROM "{schema_name}".users
                WHERE role = 'admin' AND telegram_id IS NOT NULL
            """)
        )
        admin_rows = admins_result.fetchall()
        
        if not admin_rows:
            logger.warning(f"⚠️ [NOTIFY_ADMIN] === НЕ НАЙДЕНО АДМИНИСТРАТОРОВ ===")
            logger.warning(f"⚠️ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking_id}")
            logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: В {schema_name}.users нет пользователей с role='admin' и telegram_id IS NOT NULL")
            return False
        
        logger.info(f"✅ [NOTIFY_ADMIN] === НАЙДЕНО {len(admin_rows)} АДМИНИСТРАТОРОВ ===")
        logger.info(f"✅ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking_id}")
        
        # Формируем сообщение
        booking_date = booking_row[2]  # date
        booking_time = booking_row[3]  # time
        date_str = booking_date.strftime("%d.%m.%Y")
        time_str = booking_time.strftime("%H:%M")
        
        client_name = client_row[2] if client_row[2] else "Неизвестно"  # full_name
        client_phone = client_row[3] if client_row[3] else "Не указан"  # phone
        service_name = service_row[1] if service_row else "Не указана"  # name
        
        logger.info(f"📋 [NOTIFY_ADMIN] Данные записи: booking_number={booking_row[1]}, client_name={client_name}, client_phone={client_phone}, service_name={service_name}")
        
        message_text = f"🔔 Новая запись!\n\n"
        message_text += f"📋 {booking_row[1]}\n"  # booking_number
        message_text += f"   👤 {client_name}\n"
        message_text += f"   📞 {client_phone}\n"
        message_text += f"   📅 {date_str} в {time_str}\n"
        message_text += f"   🛠️ {service_name}\n"
        
        # Отправляем уведомление всем администраторам
        logger.info(f"📤 [NOTIFY_ADMIN] === ОТПРАВКА УВЕДОМЛЕНИЙ АДМИНИСТРАТОРАМ ===")
        logger.info(f"📤 [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking_id}")
        logger.info(f"📤 [NOTIFY_ADMIN] Количество админов: {len(admin_rows)}")
        
        bot = Bot(token=bot_token)
        sent_count = 0
        failed_count = 0
        
        try:
            for admin_row in admin_rows:
                admin_telegram_id = admin_row[1]
                admin_id = admin_row[0]
                admin_name = admin_row[3] or "Администратор"
                
                try:
                    logger.info(f"📤 [NOTIFY_ADMIN] Отправляем уведомление админу: user_id={admin_id}, telegram_id={admin_telegram_id}, full_name={admin_name}")
                    result = await bot.send_message(
                        chat_id=admin_telegram_id,
                        text=message_text
                    )
                    sent_count += 1
                    logger.info(f"✅ [NOTIFY_ADMIN] Уведомление отправлено успешно: user_id={admin_id}, telegram_id={admin_telegram_id}, message_id={result.message_id}")
                except Exception as e:
                    error_msg = str(e)
                    failed_count += 1
                    logger.error(f"❌ [NOTIFY_ADMIN] Ошибка отправки админу {admin_id} (telegram_id={admin_telegram_id}): {error_msg}")
                    
                    # Проверяем специфичные ошибки Telegram API
                    error_lower = error_msg.lower()
                    if "chat not found" in error_lower or "user not found" in error_lower:
                        logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: Админ {admin_id} не начал диалог с ботом")
                    elif "blocked" in error_lower:
                        logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: Админ {admin_id} заблокировал бота")
                    elif "forbidden" in error_lower:
                        logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: Бот не может отправить сообщение админу {admin_id}")
        finally:
            try:
                await bot.session.close()
            except Exception as e:
                logger.warning(f"⚠️ [NOTIFY_ADMIN] Ошибка закрытия bot session: {e}")
        
        logger.info(f"✅ [NOTIFY_ADMIN] === ИТОГИ ОТПРАВКИ ===")
        logger.info(f"✅ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking_id}")
        logger.info(f"✅ [NOTIFY_ADMIN] Отправлено успешно: {sent_count} из {len(admin_rows)}")
        if failed_count > 0:
            logger.warning(f"⚠️ [NOTIFY_ADMIN] Не отправлено: {failed_count} из {len(admin_rows)}")
        
        return sent_count > 0
        
    except Exception as e:
        logger.error(f"❌ [NOTIFY_ADMIN] === КРИТИЧЕСКАЯ ОШИБКА ===")
        logger.error(f"❌ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking_id}")
        logger.error(f"❌ [NOTIFY_ADMIN] Ошибка: {e}", exc_info=True)
        return False
    finally:
        # Восстанавливаем search_path
        try:
            if original_search_path:
                await tenant_session.execute(sql_text(f'SET search_path TO {original_search_path}'))
            else:
                await tenant_session.execute(sql_text(f'SET search_path TO "{schema_name}", public'))
        except Exception as e:
            logger.warning(f"⚠️ [NOTIFY_ADMIN] Ошибка восстановления search_path: {e}")


async def send_booking_status_notification(company_id: int, booking_id: int, new_status: str, tenant_session: AsyncSession) -> bool:
    """Отправить уведомление об изменении статуса записи клиенту через Telegram
    
    Returns:
        True если уведомление отправлено успешно, False в противном случае
    """
    # ВАЖНО: не используем имя `text` для строковых переменных в этой функции,
    # так как `text()` используется для SQLAlchemy (иначе будет UnboundLocalError).
    from sqlalchemy import text as sql_text

    logger.info(f"📤 [NOTIFICATION] Начало отправки уведомления: company_id={company_id}, booking_id={booking_id}, status={new_status}")
    
    # Сохраняем текущий search_path
    original_search_path = None
    try:
        # Получаем текущий search_path
        path_result = await tenant_session.execute(sql_text("SHOW search_path"))
        original_search_path = path_result.scalar()
        logger.info(f"📤 [NOTIFICATION] Текущий search_path: {original_search_path}")
        
        # Получаем компанию и bot token из public схемы
        await tenant_session.execute(sql_text('SET search_path TO public'))
        company_result = await tenant_session.execute(
            sql_text('SELECT id, name, telegram_bot_token FROM public.companies WHERE id = :company_id'),
            {"company_id": company_id}
        )
        company_row = company_result.fetchone()
        
        if not company_row or not company_row[2]:
            logger.warning(f"⚠️ [NOTIFICATION] Компания {company_id} не найдена или нет bot token")
            return False
        
        bot_token = company_row[2]
        company_name = company_row[1]
        logger.info(f"📤 [NOTIFICATION] Компания найдена: name={company_name}, bot_token={bot_token[:10]}...")
        
        # Возвращаем search_path для tenant схемы
        await tenant_session.execute(sql_text(f'SET search_path TO "tenant_{company_id}", public'))
        
        # Получаем запись через прямой SQL (избегаем ORM проблем с total_visits)
        booking_result = await tenant_session.execute(
            sql_text(f"""
                SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id
                FROM "tenant_{company_id}".bookings b
                WHERE b.id = :booking_id
            """),
            {"booking_id": booking_id}
        )
        booking_row = booking_result.fetchone()
        
        if not booking_row:
            logger.warning(f"⚠️ [NOTIFICATION] Запись {booking_id} не найдена в tenant_{company_id}")
            return False
        
        booking_id_db = booking_row[0]
        booking_number = booking_row[1]
        booking_date = booking_row[2]
        booking_time = booking_row[3]
        client_id = booking_row[4]
        service_id = booking_row[5]
        
        logger.info(f"📤 [NOTIFICATION] Запись найдена: booking_number={booking_number}, client_id={client_id}")
        
        # Получаем client.user_id через прямой SQL
        client_result = await tenant_session.execute(
            sql_text(f'SELECT user_id FROM "tenant_{company_id}".clients WHERE id = :client_id'),
            {"client_id": client_id}
        )
        client_row = client_result.fetchone()
        
        if not client_row or not client_row[0]:
            logger.warning(f"⚠️ [NOTIFICATION] Клиент {client_id} не найден или нет user_id")
            return False
        
        user_id = client_row[0]
        logger.info(f"📤 [NOTIFICATION] Ищем telegram_id для user_id={user_id}")
        
        # Получаем telegram_id из users
        user_result = await tenant_session.execute(
            sql_text(f'SELECT telegram_id FROM "tenant_{company_id}".users WHERE id = :user_id'),
            {"user_id": user_id}
        )
        user_row = user_result.fetchone()
        
        telegram_id = None
        if user_row and user_row[0]:
            telegram_id = user_row[0]
            logger.info(f"✅ [NOTIFICATION] telegram_id найден: {telegram_id}")
        else:
            logger.warning(f"⚠️ [NOTIFICATION] telegram_id не найден для user_id={user_id}")
            return False
        
        # Получаем название услуги
        service_result = await tenant_session.execute(
            sql_text(f'SELECT name FROM "tenant_{company_id}".services WHERE id = :service_id'),
            {"service_id": service_id}
        )
        service_row = service_result.fetchone()
        service_name = service_row[0] if service_row else "Услуга"
        
        # Формируем сообщение
        status_messages = {
            "new": "🆕 Ваша запись создана и ожидает подтверждения.",
            "confirmed": "✅ Ваша запись подтверждена!",
            "completed": "✔️ Запись завершена. Спасибо за визит!",
            "cancelled": "❌ Запись отменена",
            "no_show": "⚠️ Вы не явились на запись",
        }
        
        message = status_messages.get(new_status, f"Статус записи изменен: {new_status}")
        
        date_str = booking_date.strftime("%d.%m.%Y")
        time_str = booking_time.strftime("%H:%M")
        
        message_text = f"{message}\n\n"
        message_text += f"Номер записи: {booking_number}\n"
        message_text += f"Дата: {date_str}\n"
        message_text += f"Время: {time_str}\n"
        message_text += f"Услуга: {service_name}\n"
        
        logger.info(f"📤 [NOTIFICATION] Отправляем сообщение в Telegram: company_id={company_id}, chat_id={telegram_id}, text_length={len(message_text)}")
        logger.info(f"📤 [NOTIFICATION] Текст сообщения: {message_text[:100]}...")
        
        # Создаем бота с токеном компании
        logger.info(f"📤 [NOTIFICATION] Создаем Bot объект с токеном: {bot_token[:10]}...")
        bot = Bot(token=bot_token)
        try:
            logger.info(f"📤 [NOTIFICATION] Пытаемся отправить сообщение: chat_id={telegram_id}, text_length={len(message_text)}")
            result = await bot.send_message(
                chat_id=telegram_id,
                text=message_text
            )
            logger.info(f"✅ [NOTIFICATION] Сообщение отправлено успешно: message_id={result.message_id}, chat_id={telegram_id}, date={result.date}")
            return True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ [NOTIFICATION] Ошибка отправки сообщения в Telegram: {error_msg}", exc_info=True)
            
            # Проверяем специфичные ошибки Telegram API
            if "chat not found" in error_msg.lower() or "user not found" in error_msg.lower():
                logger.warning(f"⚠️ [NOTIFICATION] Клиент {telegram_id} не найден или не начал диалог с ботом. Нужно отправить /start боту.")
            elif "blocked" in error_msg.lower():
                logger.warning(f"⚠️ [NOTIFICATION] Клиент {telegram_id} заблокировал бота.")
            elif "forbidden" in error_msg.lower():
                logger.warning(f"⚠️ [NOTIFICATION] Бот не может отправить сообщение клиенту {telegram_id} (возможно, клиент не начал диалог).")
            
            return False
        finally:
            try:
                await bot.session.close()
                logger.debug(f"🔒 [NOTIFICATION] Bot session закрыт")
            except Exception as e:
                logger.warning(f"⚠️ [NOTIFICATION] Ошибка закрытия bot session: {e}")
            
    except Exception as e:
        logger.error(f"❌ [NOTIFICATION] Ошибка отправки уведомления об изменении статуса для записи {booking_id}: {e}", exc_info=True)
        return False
    finally:
        # Восстанавливаем search_path
        try:
            if original_search_path:
                await tenant_session.execute(sql_text(f'SET search_path TO {original_search_path}'))
            else:
                await tenant_session.execute(sql_text(f'SET search_path TO "tenant_{company_id}", public'))
        except Exception as e:
            logger.warning(f"⚠️ [NOTIFICATION] Ошибка восстановления search_path: {e}")


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
        selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at),
        selectinload(Booking.service),
        selectinload(Booking.master),
        selectinload(Booking.post)
    )
    
    # Фильтры
    conditions = []
    if status:
        conditions.append(Booking.status == status)
    if start_date:
        conditions.append(Booking.service_date >= start_date)
    if end_date:
        conditions.append(Booking.service_date <= end_date)
    if master_id:
        conditions.append(Booking.master_id == master_id)
    if service_id:
        conditions.append(Booking.service_id == service_id)
    if post_id:
        conditions.append(Booking.post_id == post_id)
    
    # Создаем отдельный запрос для подсчета (без selectinload)
    count_query = select(func.count(Booking.id))
    
    # Применяем условия фильтрации
    if conditions:
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))
    
    # Применяем поиск после условий фильтрации
    if search:
        search_term = f"%{search}%"
        # Поиск по номеру записи, ФИО клиента, телефону
        # В tenant схемах User не имеет first_name/last_name, только full_name в Client
        from sqlalchemy.orm import outerjoin
        search_condition = or_(
            Booking.booking_number.ilike(search_term),
            Client.phone.ilike(search_term),
            Client.full_name.ilike(search_term)
        )
        query = query.outerjoin(Client).where(search_condition)
        count_query = count_query.outerjoin(Client).where(search_condition)
    
    # Подсчет общего количества
    total = await tenant_session.scalar(count_query) or 0
    
    logger.info(f"📊 Запрос записей: total={total}, page={page}, page_size={page_size}")
    logger.info(f"📅 Фильтры: start_date={start_date}, end_date={end_date}, status={status}, search={search}")
    
    # Проверяем общее количество записей в БД без фильтров (для отладки)
    total_all_query = select(func.count(Booking.id))
    total_all = await tenant_session.scalar(total_all_query) or 0
    logger.info(f"📈 Всего записей в БД (без фильтров): {total_all}")
    
    # Сортировка перед пагинацией
    query = query.order_by(Booking.service_date.desc(), Booking.time.desc(), Booking.created_at.desc())
    
    # Пагинация
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await tenant_session.execute(query)
    bookings = result.scalars().all()
    
    logger.info(f"✅ Получено записей: {len(bookings)}")
    if len(bookings) > 0:
        logger.info(f"📋 Первая запись: date={bookings[0].service_date}, status={bookings[0].status}")
    
    # Получаем все user_id для записей одним запросом
    user_ids = set()
    for booking in bookings:
        if booking.client and booking.client.user_id:
            user_ids.add(booking.client.user_id)
    
    # Получаем telegram_id для всех user_id одним запросом
    telegram_ids_map = {}
    if user_ids:
        user_ids_list = list(user_ids)
        telegram_result = await tenant_session.execute(
            text(f'SELECT id, telegram_id FROM "tenant_{company_id}".users WHERE id = ANY(:user_ids)'),
            {"user_ids": user_ids_list}
        )
        for row in telegram_result.fetchall():
            if row[1]:  # telegram_id не None
                telegram_ids_map[row[0]] = row[1]
    
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
            "service_date": booking.service_date,
            "request_date": booking.request_date,
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
            # В tenant схемах User не имеет first_name/last_name, используем только full_name из Client
            booking_dict["client_name"] = booking.client.full_name
            booking_dict["client_phone"] = booking.client.phone
            # Получаем telegram_id из кэша
            booking_dict["client_telegram_id"] = telegram_ids_map.get(booking.client.user_id) if booking.client.user_id else None
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
    booked_query = select(Booking).where(Booking.service_date == booking_date)
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
                    booking_start = datetime.combine(booking.service_date, booking.time)
                    booking_end = datetime.combine(booking.service_date, booking.end_time)
                    
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
            booking_start = datetime.combine(booking.service_date, booking.time)
            booking_end = datetime.combine(booking.service_date, booking.end_time)
            
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
        selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at),
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
        "service_date": booking.service_date,
        "request_date": booking.request_date,
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
        # В tenant схемах User не имеет first_name/last_name, используем только full_name из Client
        booking_dict["client_name"] = booking.client.full_name
        # Пробуем получить telegram_id из Client, если есть
        if hasattr(booking.client, 'telegram_id'):
            booking_dict["client_telegram_id"] = booking.client.telegram_id
        else:
            booking_dict["client_telegram_id"] = None
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
    booking_number = f"BK{company_id:03d}{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Преобразуем time в объект time, если это строка
    booking_time = booking_data.time
    if isinstance(booking_time, str):
        from datetime import datetime as dt
        booking_time = dt.strptime(booking_time, "%H:%M").time()
    
    # Вычисляем end_time
    duration_minutes = booking_data.duration or 60
    booking_datetime = datetime.combine(booking_data.service_date, booking_time)
    end_time = (booking_datetime + timedelta(minutes=duration_minutes)).time()
    
    # Создаём запись: явно задаём NOT NULL поля (на случай отсутствия DEFAULT в tenant-схеме)
    booking = Booking(
        booking_number=booking_number,
        client_id=booking_data.client_id,
        service_id=booking_data.service_id,
        master_id=booking_data.master_id,
        post_id=booking_data.post_id,
        service_date=booking_data.service_date,
        request_date=date.today(),
        time=booking_time,
        duration=duration_minutes,
        end_time=end_time,
        status=booking_data.status or "new",
        amount=booking_data.amount,
        is_paid=False,
        discount_amount=0,
        comment=booking_data.comment,
        created_by=current_user.id,
    )
    
    tenant_session.add(booking)
    await tenant_session.flush()  # Получаем ID без коммита
    booking_id = booking.id
    
    await tenant_session.commit()
    
    # Убеждаемся, что search_path установлен для tenant схемы перед загрузкой
    await tenant_session.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    
    # Загружаем связанные объекты через прямой запрос с load_only (чтобы избежать проблем с несуществующими колонками)
    result = await tenant_session.execute(
        select(Booking).options(
            selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at),
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post)
        ).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        logger.error(f"❌ [CREATE] Не удалось загрузить созданную запись: booking_id={booking_id}, company_id={company_id}")
        raise HTTPException(status_code=500, detail="Не удалось загрузить созданную запись")
    
    # Формируем ответ
    booking_dict = {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "client_id": booking.client_id,
        "service_id": booking.service_id,
        "master_id": booking.master_id,
        "post_id": booking.post_id,
        "service_date": booking.service_date,
        "request_date": booking.request_date,
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
        # В tenant схемах User не имеет first_name/last_name, используем только full_name из Client
        booking_dict["client_name"] = booking.client.full_name
        # Пробуем получить telegram_id из Client, если есть
        if hasattr(booking.client, 'telegram_id'):
            booking_dict["client_telegram_id"] = booking.client.telegram_id
        else:
            booking_dict["client_telegram_id"] = None
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
    
    # Отправляем уведомление администраторам о новой записи
    try:
        await notify_admins_about_new_booking(company_id, booking_id, tenant_session)
        logger.info(f"✅ [CREATE] Уведомление администраторам отправлено: company_id={company_id}, booking_id={booking_id}")
    except Exception as e:
        logger.error(f"❌ [CREATE] Ошибка отправки уведомления администраторам: {e}", exc_info=True)
        # Не прерываем создание записи, если уведомление не отправилось
    
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
    
    # Важно: фиксируем старый статус ДО любых изменений, иначе уведомления не будут отправляться
    old_status = booking.status

    # Обновляем поля
    if booking_data.client_id is not None:
        booking.client_id = booking_data.client_id
    if booking_data.service_id is not None:
        booking.service_id = booking_data.service_id
    if booking_data.master_id is not None:
        booking.master_id = booking_data.master_id
    if booking_data.post_id is not None:
        booking.post_id = booking_data.post_id
    if booking_data.service_date is not None:
        booking.service_date = booking_data.service_date
    if booking_data.request_date is not None:
        booking.request_date = booking_data.request_date
    if booking_data.time is not None:
        booking.time = booking_data.time
    if booking_data.duration is not None:
        booking.duration = booking_data.duration
        booking.end_time = (datetime.combine(booking.service_date, booking.time) + timedelta(minutes=booking_data.duration)).time()
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
    
    # Обновляем временные метки при смене статуса
    if booking_data.status is not None:
        now = datetime.utcnow()
        # Сравниваем с old_status, потому что booking.status уже мог быть изменен выше
        if booking_data.status == "confirmed" and old_status != "confirmed":
            booking.confirmed_at = now
        elif booking_data.status == "completed" and old_status != "completed":
            booking.completed_at = now
        elif booking_data.status == "cancelled" and old_status != "cancelled":
            booking.cancelled_at = now
    
    await tenant_session.commit()
    
    # Планируем напоминания при подтверждении записи
    if booking_data.status is not None and booking_data.status == "confirmed" and old_status != "confirmed":
        try:
            from app.tasks.notifications import schedule_booking_reminders
            schedule_booking_reminders(
                company_id=company_id,
                booking_id=booking_id,
                booking_date=booking.service_date,
                booking_time=booking.time
            )
            logger.info(f"📅 Напоминания запланированы для записи {booking_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка планирования напоминаний для записи {booking_id}: {e}", exc_info=True)
    
    # Отправляем уведомление клиенту при смене статуса
    notification_sent = False
    if booking_data.status is not None and booking_data.status != old_status:
        logger.info(f"📤 [UPDATE] Статус изменился: {old_status} -> {booking_data.status}, отправляем уведомление")
        try:
            # Отправляем уведомление напрямую (без Celery, так как worker может быть не запущен)
            notification_sent = await send_booking_status_notification(company_id, booking_id, booking_data.status, tenant_session)
            if notification_sent:
                logger.info(f"✅ [UPDATE] Уведомление отправлено успешно: company_id={company_id}, booking_id={booking_id}, status={booking_data.status}")
            else:
                logger.warning(f"⚠️ [UPDATE] Уведомление не отправлено: company_id={company_id}, booking_id={booking_id}, status={booking_data.status}")
        except Exception as e:
            logger.error(f"❌ [UPDATE] Ошибка отправки уведомления: {e}", exc_info=True)
            notification_sent = False
    
    # Убеждаемся, что search_path установлен для tenant схемы
    await tenant_session.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
    
    # Загружаем связанные данные (refresh не нужен, так как мы перезагружаем через новый запрос)
    result = await tenant_session.execute(
        select(Booking).options(
            selectinload(Booking.client).load_only(Client.id, Client.user_id, Client.full_name, Client.phone, Client.created_at, Client.updated_at),
            selectinload(Booking.service),
            selectinload(Booking.master),
            selectinload(Booking.post)
        ).where(Booking.id == booking_id)
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена после обновления")
    
    # Формируем ответ
    booking_dict = {
        "id": booking.id,
        "booking_number": booking.booking_number,
        "client_id": booking.client_id,
        "service_id": booking.service_id,
        "master_id": booking.master_id,
        "post_id": booking.post_id,
        "service_date": booking.service_date,
        "request_date": booking.request_date,
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
        # В tenant схемах User не имеет first_name/last_name, используем только full_name из Client
        booking_dict["client_name"] = booking.client.full_name
        # Получаем telegram_id из users через user_id
        booking_dict["client_telegram_id"] = await get_client_telegram_id(tenant_session, company_id, booking.client)
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
    
    logger.info(f"📤 [UPDATE] Возвращаем ответ: booking_id={booking_id}, notification_sent={notification_sent}, client_telegram_id={booking_dict.get('client_telegram_id')}")
    
    return BookingResponse.model_validate(booking_dict)
