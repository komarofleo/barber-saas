"""Задачи для отправки уведомлений через Telegram"""
import asyncio
import os
from datetime import date, datetime, timedelta, time as time_type
from typing import List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from shared.database.models import Booking, Client, User, Master
from app.models.public_models import Company
from sqlalchemy import text

# TODO: Создать модель Notification (пока заглушка)
class Notification:
    """Временная заглушка для модели Notification"""
    def __init__(self, **kwargs):
        pass
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from celery import shared_task

# Получаем настройки из переменных окружения
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "barber_db")
DB_USER = os.getenv("DB_USER", "barber_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Формируем URL базы данных
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаем движок для задач
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Инициализируем бота только при необходимости
_bot_instance = None

def get_bot():
    """Получить экземпляр бота (lazy initialization)"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=BOT_TOKEN)
    return _bot_instance


def _run_async(coro):
    """
    Запустить корутину в Celery-воркере.

    После закрытия event loop asyncpg/SQLAlchemy нельзя переиспользовать —
    dispose + новый engine на каждую задачу.
    """
    global engine, async_session_maker
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            loop.run_until_complete(engine.dispose())
        except Exception as e:
            print(f"Предупреждение: dispose async engine: {e}")
        try:
            loop.close()
        except Exception:
            pass
        asyncio.set_event_loop(None)
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )


def _parse_hhmm(value: str, fallback: time_type) -> time_type:
    """Разобрать HH:MM из настроек tenant."""
    try:
        hour_str, minute_str = (value or "").strip().split(":")
        return time_type(int(hour_str), int(minute_str))
    except Exception:
        return fallback


async def _load_reminder_settings(company_id: int) -> dict:
    """Прочитать настройки напоминаний из tenant.settings."""
    defaults = {
        "reminder_day_before_time": "18:00",
        "reminder_day_enabled": "true",
        "reminder_hour_before": "true",
        "reminder_hour_enabled": "true",
    }
    schema_name = f"tenant_{company_id}"
    async with async_session_maker() as session:
        await session.execute(text(f'SET search_path TO "{schema_name}", public'))
        result = await session.execute(
            text(
                f"""
                SELECT key, value FROM "{schema_name}".settings
                WHERE key IN (
                    'reminder_day_before_time',
                    'reminder_day_enabled',
                    'reminder_hour_before',
                    'reminder_hour_enabled'
                )
                """
            )
        )
        for key, value in result.fetchall():
            if value is not None:
                defaults[key] = str(value)
    return defaults


async def send_reminder_day_before():
    """Отправить напоминания за день до записи (мульти-тенантная версия).

    Учитывает settings каждой компании:
    - reminder_day_enabled
    - reminder_day_before_time (окно ±10 минут от текущего времени)
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    async with async_session_maker() as session:
        await session.execute(text("SET search_path TO public"))
        companies_result = await session.execute(
            text(
                "SELECT id, name, telegram_bot_token FROM public.companies WHERE is_active = true"
            )
        )
        companies = companies_result.fetchall()

        total_reminders = 0

        for company_row in companies:
            company_id = company_row[0]
            company_name = company_row[1]
            bot_token = company_row[2]

            if not bot_token:
                continue

            try:
                settings_map = await _load_reminder_settings(company_id)
                if settings_map.get("reminder_day_enabled", "true").lower() not in (
                    "true",
                    "1",
                    "yes",
                ):
                    continue

                day_time = _parse_hhmm(
                    settings_map.get("reminder_day_before_time", "18:00"),
                    time_type(18, 0),
                )
                target_minutes = day_time.hour * 60 + day_time.minute
                # Окно ±10 минут (beat каждые 15 мин)
                if abs(now_minutes - target_minutes) > 10:
                    continue

                schema_name = f"tenant_{company_id}"
                await session.execute(text(f'SET search_path TO "{schema_name}", public'))

                bookings_result = await session.execute(
                    text(
                        f"""
                        SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id,
                               b.master_id, b.post_id, b.status,
                               c.user_id,
                               u.telegram_id,
                               s.name as service_name,
                               m.full_name as master_name,
                               p.number as post_number
                        FROM "{schema_name}".bookings b
                        LEFT JOIN "{schema_name}".clients c ON b.client_id = c.id
                        LEFT JOIN "{schema_name}".users u ON c.user_id = u.id
                        LEFT JOIN "{schema_name}".services s ON b.service_id = s.id
                        LEFT JOIN "{schema_name}".masters m ON b.master_id = m.id
                        LEFT JOIN "{schema_name}".posts p ON b.post_id = p.id
                        WHERE b.service_date = :tomorrow
                          AND b.status = 'confirmed'
                          AND u.telegram_id IS NOT NULL
                          AND NOT EXISTS (
                              SELECT 1 FROM "{schema_name}".notifications n
                              WHERE n.booking_id = b.id
                                AND n.notification_type = 'reminder_day'
                                AND n.is_sent = true
                          )
                        """
                    ),
                    {"tomorrow": tomorrow},
                )
                bookings = bookings_result.fetchall()
                if not bookings:
                    continue

                bot = Bot(token=bot_token)
                for booking_row in bookings:
                    booking_id = booking_row[0]
                    booking_date = booking_row[2]
                    booking_time = booking_row[3]
                    user_id = booking_row[9]
                    telegram_id = booking_row[10]
                    service_name = booking_row[11] or "Услуга"
                    master_name = booking_row[12] or "Не назначен"
                    post_number = f"Пост №{booking_row[13]}" if booking_row[13] else "Не назначен"

                    try:
                        date_str = booking_date.strftime("%d.%m.%Y")
                        time_str = booking_time.strftime("%H:%M")
                        message_text = (
                            "🔔 Напоминание о записи\n\n"
                            f"Завтра {date_str} в {time_str}\n"
                            f"Услуга: {service_name}\n"
                            f"Мастер: {master_name}\n"
                            f"{post_number}\n\n"
                            "Ждем вас в салоне красоты!"
                        )
                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="✅ Подтверждаю",
                                        callback_data=f"confirm_attendance_{booking_id}",
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        text="❌ Отказ",
                                        callback_data=f"cancel_booking_{booking_id}",
                                    )
                                ],
                            ]
                        )
                        await bot.send_message(
                            chat_id=telegram_id, text=message_text, reply_markup=keyboard
                        )
                        await session.execute(
                            text(
                                f"""
                                INSERT INTO "{schema_name}".notifications
                                (user_id, booking_id, notification_type, message, is_sent, sent_at, created_at)
                                VALUES (:user_id, :booking_id, 'reminder_day', :message, true, :sent_at, :created_at)
                                """
                            ),
                            {
                                "user_id": user_id,
                                "booking_id": booking_id,
                                "message": message_text,
                                "sent_at": datetime.utcnow(),
                                "created_at": datetime.utcnow(),
                            },
                        )
                        await session.commit()
                        total_reminders += 1
                        print(
                            f"Напоминание за день отправлено: компания {company_name}, запись {booking_id}"
                        )
                    except Exception as e:
                        print(
                            f"Ошибка отправки напоминания за день для записи {booking_id} "
                            f"(компания {company_id}): {e}"
                        )

                await bot.session.close()

            except Exception as e:
                print(f"Ошибка обработки компании {company_id}: {e}")
                continue

        print(f"Всего отправлено напоминаний за день: {total_reminders}")


async def send_reminder_3_hours_before():
    """Отправить напоминания за час до записи (имя задачи историческое).

    Beat запускает каждые 5 минут; окно ±3 минуты вокруг «сейчас + 1 час».
    Не шлёт повторно, если в notifications уже есть reminder_hour.
    """
    now = datetime.now()
    target_time_start = (now + timedelta(hours=1, minutes=-3)).time()
    target_time_end = (now + timedelta(hours=1, minutes=3)).time()
    today = date.today()
    
    async with async_session_maker() as session:
        # Получаем все активные компании
        await session.execute(text('SET search_path TO public'))
        companies_result = await session.execute(
            text('SELECT id, name, telegram_bot_token FROM public.companies WHERE is_active = true')
        )
        companies = companies_result.fetchall()
        
        total_reminders = 0
        
        for company_row in companies:
            company_id = company_row[0]
            company_name = company_row[1]
            bot_token = company_row[2]
            
            if not bot_token:
                continue

            try:
                settings_map = await _load_reminder_settings(company_id)
                hour_on = settings_map.get("reminder_hour_before", "true").lower() in (
                    "true",
                    "1",
                    "yes",
                ) and settings_map.get("reminder_hour_enabled", "true").lower() in (
                    "true",
                    "1",
                    "yes",
                )
                if not hour_on:
                    continue

                schema_name = f"tenant_{company_id}"
                await session.execute(text(f'SET search_path TO "{schema_name}", public'))

                # Окно «через час»; не шлём повторно reminder_hour / legacy reminder_3_hours
                bookings_result = await session.execute(
                    text(
                        f"""
                        SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id,
                               b.post_id, b.status,
                               c.user_id,
                               u.telegram_id,
                               s.name as service_name,
                               p.number as post_number
                        FROM "{schema_name}".bookings b
                        LEFT JOIN "{schema_name}".clients c ON b.client_id = c.id
                        LEFT JOIN "{schema_name}".users u ON c.user_id = u.id
                        LEFT JOIN "{schema_name}".services s ON b.service_id = s.id
                        LEFT JOIN "{schema_name}".posts p ON b.post_id = p.id
                        WHERE b.service_date = :today
                          AND b.status = 'confirmed'
                          AND b.time >= :target_time_start
                          AND b.time <= :target_time_end
                          AND u.telegram_id IS NOT NULL
                          AND NOT EXISTS (
                              SELECT 1 FROM "{schema_name}".notifications n
                              WHERE n.booking_id = b.id
                                AND n.notification_type IN ('reminder_hour', 'reminder_3_hours')
                                AND n.is_sent = true
                          )
                        """
                    ),
                    {
                        "today": today,
                        "target_time_start": target_time_start,
                        "target_time_end": target_time_end,
                    },
                )
                bookings = bookings_result.fetchall()

                if not bookings:
                    continue

                bot = Bot(token=bot_token)

                for booking_row in bookings:
                    booking_id = booking_row[0]
                    booking_time = booking_row[3]
                    user_id = booking_row[8]
                    telegram_id = booking_row[9]
                    service_name = booking_row[10] or "Услуга"
                    post_number = f"Пост №{booking_row[11]}" if booking_row[11] else "Не назначен"

                    try:
                        time_str = booking_time.strftime("%H:%M")
                        text = (
                            "🔔 Напоминание о записи\n\n"
                            "Через час ваша запись!\n"
                            f"⏰ Время: {time_str}\n"
                            f"🛠️ Услуга: {service_name}\n"
                            f"🏢 {post_number}\n\n"
                            "Пожалуйста, подтвердите явку или отмените запись:"
                        )

                        keyboard = InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    InlineKeyboardButton(
                                        text="✅ Подтверждаю",
                                        callback_data=f"confirm_attendance_{booking_id}",
                                    )
                                ],
                                [
                                    InlineKeyboardButton(
                                        text="❌ Отказ",
                                        callback_data=f"cancel_booking_{booking_id}",
                                    )
                                ],
                            ]
                        )
                        
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=text,
                            reply_markup=keyboard
                        )
                        
                        # Сохраняем в историю уведомлений, чтобы не отправлять повторно
                        await session.execute(
                            text(f"""
                                INSERT INTO "{schema_name}".notifications 
                                (user_id, booking_id, notification_type, message, is_sent, sent_at, created_at)
                                VALUES (:user_id, :booking_id, 'reminder_hour', :message, true, :sent_at, :created_at)
                            """),
                            {
                                "user_id": user_id,
                                "booking_id": booking_id,
                                "message": text,
                                "sent_at": datetime.utcnow(),
                                "created_at": datetime.utcnow()
                            }
                        )
                        await session.commit()
                        
                        total_reminders += 1
                        print(f"✅ Напоминание за 3 часа отправлено: компания {company_name}, запись {booking_id}")
                        
                    except Exception as e:
                        print(f"❌ Ошибка отправки напоминания за 3 часа для записи {booking_id} (компания {company_id}): {e}")
                        # Сохраняем ошибку в историю
                        try:
                            await session.execute(
                                text(f"""
                                    INSERT INTO "{schema_name}".notifications 
                                    (user_id, booking_id, notification_type, message, is_sent, error_message, created_at)
                                    VALUES (:user_id, :booking_id, 'reminder_hour', :message, false, :error_message, :created_at)
                                """),
                                {
                                    "user_id": user_id,
                                    "booking_id": booking_id,
                                    "message": text,
                                    "error_message": str(e),
                                    "created_at": datetime.utcnow()
                                }
                            )
                            await session.commit()
                        except:
                            pass
                
                await bot.session.close()
                
            except Exception as e:
                print(f"❌ Ошибка обработки компании {company_id}: {e}")
                continue
        
        print(f"📊 Всего отправлено напоминаний за 3 часа: {total_reminders}")


async def send_status_change_notification(booking_id: int, new_status: str):
    """Отправить уведомление об изменении статуса записи пользователю, создавшему заявку"""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
                selectinload(Booking.creator),
            )
        )
        booking = result.scalar_one_or_none()
        
        if not booking:
            print(f"Запись {booking_id} не найдена для отправки уведомления")
            return
        
        print(f"[DEBUG] Запись {booking_id}: created_by={booking.created_by}, client_id={booking.client_id if booking.client else None}")
        
        # Определяем, кому отправлять уведомление:
        # 1. Если заявку создал пользователь через бота (creator) - отправляем ему
        # 2. Иначе отправляем клиенту записи
        target_user = None
        
        # Сначала проверяем creator (если заявка создана через бота)
        if booking.created_by:
            # Пытаемся загрузить creator отдельно, если не загрузился через selectinload
            if booking.creator and booking.creator.telegram_id:
                target_user = booking.creator
                print(f"[DEBUG] Используем creator: user_id={booking.creator.id}, telegram_id={booking.creator.telegram_id}")
            else:
                # Загружаем creator вручную
                creator_result = await session.execute(
                    select(User).where(User.id == booking.created_by)
                )
                creator = creator_result.scalar_one_or_none()
                if creator and creator.telegram_id:
                    target_user = creator
                    print(f"[DEBUG] Загружен creator вручную: user_id={creator.id}, telegram_id={creator.telegram_id}")
        
        # Если creator не подошел, проверяем client.user
        if not target_user and booking.client:
            if booking.client.user and booking.client.user.telegram_id:
                target_user = booking.client.user
                print(f"[DEBUG] Используем client.user: user_id={booking.client.user.id}, telegram_id={booking.client.user.telegram_id}")
            else:
                # Загружаем client.user вручную
                if booking.client.user_id:
                    client_user_result = await session.execute(
                        select(User).where(User.id == booking.client.user_id)
                    )
                    client_user = client_user_result.scalar_one_or_none()
                    if client_user and client_user.telegram_id:
                        target_user = client_user
                        print(f"[DEBUG] Загружен client.user вручную: user_id={client_user.id}, telegram_id={client_user.telegram_id}")
        
        if not target_user or not target_user.telegram_id:
            print(f"[ERROR] Не найден получатель уведомления для записи {booking_id}")
            print(f"[ERROR] created_by={booking.created_by}, client_id={booking.client_id if booking.client else None}")
            print(f"[ERROR] creator={booking.creator.id if booking.creator else None}, creator.telegram_id={booking.creator.telegram_id if booking.creator else None}")
            print(f"[ERROR] client.user={booking.client.user.id if (booking.client and booking.client.user) else None}, client.user.telegram_id={booking.client.user.telegram_id if (booking.client and booking.client.user) else None}")
            return
        
        print(f"[SUCCESS] Получатель найден: user_id={target_user.id}, telegram_id={target_user.telegram_id}")
        
        status_messages = {
            "new": "🆕 Ваша запись создана и ожидает подтверждения.",
            "confirmed": "✅ Ваша запись подтверждена!",
            "completed": "✔️ Запись завершена. Спасибо за визит!",
            "cancelled": "❌ Запись отменена",
            "no_show": "⚠️ Вы не явились на запись",
        }
        
        message = status_messages.get(new_status, f"Статус записи изменен: {new_status}")
        
        try:
            date_str = booking.service_date.strftime("%d.%m.%Y")
            time_str = booking.time.strftime("%H:%M")
            service_name = booking.service.name if booking.service else "Услуга"
            
            text = f"{message}\n\n"
            text += f"Номер записи: {booking.booking_number}\n"
            text += f"Дата: {date_str}\n"
            text += f"Время: {time_str}\n"
            text += f"Услуга: {service_name}\n"
            
            print(f"[DEBUG] Отправляем сообщение в Telegram: chat_id={target_user.telegram_id}, text_length={len(text)}")
            bot = get_bot()
            result = await bot.send_message(
                chat_id=target_user.telegram_id,
                text=text
            )
            print(f"[SUCCESS] Сообщение отправлено успешно: message_id={result.message_id}")
            
            notification = Notification(
                user_id=target_user.id,
                booking_id=booking.id,
                notification_type="status_change",
                message=text,
                is_sent=True,
                sent_at=datetime.utcnow()
            )
            session.add(notification)
            await session.commit()
            print(f"[SUCCESS] Уведомление сохранено в БД: notification_id={notification.id}")
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Ошибка отправки уведомления об изменении статуса для записи {booking.id}: {e}")
            print(f"[ERROR] Traceback: {error_trace}")
            notification = Notification(
                user_id=target_user.id,
                booking_id=booking.id,
                notification_type="status_change",
                message=text,
                is_sent=False,
                error_message=str(e)
            )
            session.add(notification)
            await session.commit()


# Функции для отправки одного напоминания (для отложенных задач)
async def send_single_reminder_day_before(company_id: int, booking_id: int):
    """Отправить напоминание за день до записи для одной записи"""
    async with async_session_maker() as session:
        try:
            # Получаем компанию и bot token
            await session.execute(text('SET search_path TO public'))
            company_result = await session.execute(
                text('SELECT id, name, telegram_bot_token FROM public.companies WHERE id = :company_id'),
                {"company_id": company_id}
            )
            company_row = company_result.fetchone()
            
            if not company_row or not company_row[2]:
                print(f"❌ Компания {company_id} не найдена или нет bot token")
                return
            
            bot_token = company_row[2]
            company_name = company_row[1]
            
            # Переключаемся на tenant схему
            schema_name = f"tenant_{company_id}"
            await session.execute(text(f'SET search_path TO "{schema_name}", public'))
            
            # Получаем данные записи
            booking_result = await session.execute(
                text(f"""
                    SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id, 
                           b.master_id, b.post_id, b.status,
                           c.user_id,
                           u.telegram_id,
                           s.name as service_name,
                           m.full_name as master_name,
                           p.number as post_number
                    FROM "{schema_name}".bookings b
                    LEFT JOIN "{schema_name}".clients c ON b.client_id = c.id
                    LEFT JOIN "{schema_name}".users u ON c.user_id = u.id
                    LEFT JOIN "{schema_name}".services s ON b.service_id = s.id
                    LEFT JOIN "{schema_name}".masters m ON b.master_id = m.id
                    LEFT JOIN "{schema_name}".posts p ON b.post_id = p.id
                    WHERE b.id = :booking_id
                      AND b.status = 'confirmed'
                      AND u.telegram_id IS NOT NULL
                """),
                {"booking_id": booking_id}
            )
            booking_row = booking_result.fetchone()
            
            if not booking_row:
                print(f"❌ Запись {booking_id} не найдена, уже отменена или напоминание уже отправлено")
                return
            
            booking_id_db = booking_row[0]
            booking_number = booking_row[1]
            booking_date = booking_row[2]
            booking_time = booking_row[3]
            user_id = booking_row[9]
            telegram_id = booking_row[10]
            service_name = booking_row[11] or "Услуга"
            master_name = booking_row[12] or "Не назначен"
            post_number = f"Пост №{booking_row[13]}" if booking_row[13] else "Не назначен"
            
            # Формируем сообщение
            date_str = booking_date.strftime("%d.%m.%Y")
            time_str = booking_time.strftime("%H:%M")
            
            message_text = "🔔 Напоминание о записи\n\n"
            message_text += f"Завтра {date_str} в {time_str}\n"
            message_text += f"Услуга: {service_name}\n"
            message_text += f"Мастер: {master_name}\n"
            message_text += f"{post_number}\n\n"
            message_text += "Ждем вас в салоне красоты!"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтверждаю", callback_data=f"confirm_attendance_{booking_id_db}")],
                [InlineKeyboardButton(text="❌ Отказ", callback_data=f"cancel_booking_{booking_id_db}")],
            ])
            
            # Отправляем сообщение
            bot = Bot(token=bot_token)
            await bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                reply_markup=keyboard
            )
            await bot.session.close()
            
            # Сохраняем в историю
            await session.execute(
                text(f"""
                    INSERT INTO "{schema_name}".notifications 
                    (user_id, booking_id, notification_type, message, is_sent, sent_at, created_at)
                    VALUES (:user_id, :booking_id, 'reminder_day', :message, true, :sent_at, :created_at)
                """),
                {
                    "user_id": user_id,
                    "booking_id": booking_id_db,
                    "message": message_text,
                    "sent_at": datetime.utcnow(),
                    "created_at": datetime.utcnow()
                }
            )
            await session.commit()
            
            print(f"✅ Напоминание за день отправлено: компания {company_name}, запись {booking_id_db}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания за день для записи {booking_id} (компания {company_id}): {e}")


async def send_single_reminder_3_hours_before(company_id: int, booking_id: int):
    """Отправить напоминание за 3 часа до записи для одной записи"""
    async with async_session_maker() as session:
        try:
            # Получаем компанию и bot token
            await session.execute(text('SET search_path TO public'))
            company_result = await session.execute(
                text('SELECT id, name, telegram_bot_token FROM public.companies WHERE id = :company_id'),
                {"company_id": company_id}
            )
            company_row = company_result.fetchone()
            
            if not company_row or not company_row[2]:
                print(f"❌ Компания {company_id} не найдена или нет bot token")
                return
            
            bot_token = company_row[2]
            company_name = company_row[1]
            
            # Переключаемся на tenant схему
            schema_name = f"tenant_{company_id}"
            await session.execute(text(f'SET search_path TO "{schema_name}", public'))
            
            # Получаем данные записи
            booking_result = await session.execute(
                text(f"""
                    SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id, 
                           b.post_id, b.status,
                           c.user_id,
                           u.telegram_id,
                           s.name as service_name,
                           p.number as post_number
                    FROM "{schema_name}".bookings b
                    LEFT JOIN "{schema_name}".clients c ON b.client_id = c.id
                    LEFT JOIN "{schema_name}".users u ON c.user_id = u.id
                    LEFT JOIN "{schema_name}".services s ON b.service_id = s.id
                    LEFT JOIN "{schema_name}".posts p ON b.post_id = p.id
                    WHERE b.id = :booking_id
                      AND b.status = 'confirmed'
                      AND u.telegram_id IS NOT NULL
                """),
                {"booking_id": booking_id}
            )
            booking_row = booking_result.fetchone()
            
            if not booking_row:
                print(f"❌ Запись {booking_id} не найдена, уже отменена или напоминание уже отправлено")
                return
            
            booking_id_db = booking_row[0]
            booking_number = booking_row[1]
            booking_date = booking_row[2]
            booking_time = booking_row[3]
            user_id = booking_row[8]
            telegram_id = booking_row[9]
            service_name = booking_row[10] or "Услуга"
            post_number = f"Пост №{booking_row[11]}" if booking_row[11] else "Не назначен"
            
            # Формируем сообщение
            time_str = booking_time.strftime("%H:%M")
            
            message_text = "🔔 Напоминание о записи\n\n"
            message_text += "Через час ваша запись!\n"
            message_text += f"⏰ Время: {time_str}\n"
            message_text += f"🛠️ Услуга: {service_name}\n"
            message_text += f"🏢 {post_number}\n\n"
            message_text += "Пожалуйста, подтвердите явку или отмените запись:"

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Подтверждаю",
                            callback_data=f"confirm_attendance_{booking_id_db}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Отказ",
                            callback_data=f"cancel_booking_{booking_id_db}",
                        )
                    ],
                ]
            )

            bot = Bot(token=bot_token)
            await bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                reply_markup=keyboard,
            )
            await bot.session.close()

            try:
                await session.execute(
                    text(
                        f"""
                        INSERT INTO "{schema_name}".notifications
                        (user_id, booking_id, notification_type, message, is_sent, sent_at, created_at)
                        VALUES (:user_id, :booking_id, 'reminder_hour', :message, true, :sent_at, :created_at)
                        """
                    ),
                    {
                        "user_id": user_id,
                        "booking_id": booking_id_db,
                        "message": message_text,
                        "sent_at": datetime.utcnow(),
                        "created_at": datetime.utcnow()
                    }
                )
                await session.commit()
            except Exception as e:
                # Если таблица не существует - просто пропускаем сохранение
                print(f"⚠️ Не удалось сохранить в notifications (таблица может не существовать): {e}")
                pass
            
            print(f"✅ Напоминание за 3 часа отправлено: компания {company_name}, запись {booking_id_db}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки напоминания за 3 часа для записи {booking_id} (компания {company_id}): {e}")


# Celery задачи для отложенных напоминаний (одна запись)
@shared_task
def send_single_reminder_day_before_task(company_id: int, booking_id: int):
    """Celery задача для отправки напоминания за день для одной записи"""
    try:
        _run_async(send_single_reminder_day_before(company_id, booking_id))
    except Exception as e:
        print(f"Ошибка в задаче send_single_reminder_day_before_task: {e}")
        raise


@shared_task
def send_single_reminder_3_hours_before_task(company_id: int, booking_id: int):
    """Celery задача для отправки напоминания за 3 часа для одной записи"""
    try:
        _run_async(send_single_reminder_3_hours_before(company_id, booking_id))
    except Exception as e:
        print(f"Ошибка в задаче send_single_reminder_3_hours_before_task: {e}")
        raise


def schedule_booking_reminders(
    company_id: int, booking_id: int, booking_date: date, booking_time: time_type
):
    """
    Запланировать напоминания при подтверждении записи.

    1. За день — в время из settings.reminder_day_before_time (по умолчанию 18:00)
    2. За час — если reminder_hour_before / reminder_hour_enabled включены
    """
    try:
        from datetime import datetime

        settings_map = _run_async(_load_reminder_settings(company_id))

        def _is_true(key: str, default: str = "true") -> bool:
            return settings_map.get(key, default).lower() in ("true", "1", "yes")

        day_enabled = _is_true("reminder_day_enabled")
        # UI-ключ reminder_hour_before + legacy reminder_hour_enabled
        hour_enabled = _is_true("reminder_hour_before") and _is_true("reminder_hour_enabled")

        day_time = _parse_hhmm(settings_map.get("reminder_day_before_time", "18:00"), time_type(18, 0))
        reminder_day_datetime = datetime.combine(booking_date - timedelta(days=1), day_time)
        booking_datetime = datetime.combine(booking_date, booking_time)
        reminder_hour_datetime = booking_datetime - timedelta(hours=1)
        now = datetime.now()

        if day_enabled and reminder_day_datetime > now:
            send_single_reminder_day_before_task.apply_async(
                args=[company_id, booking_id],
                eta=reminder_day_datetime,
            )
            print(
                f"Запланировано напоминание за день: booking={booking_id}, eta={reminder_day_datetime}"
            )
        elif not day_enabled:
            print(f"Напоминание за день отключено в настройках компании {company_id}")
        else:
            print(
                f"Напоминание за день пропущено (уже прошло): booking={booking_id}, "
                f"было бы {reminder_day_datetime}"
            )

        if hour_enabled and reminder_hour_datetime > now:
            # Используем существующую Celery-задачу (имя историческое «3 hours»)
            send_single_reminder_3_hours_before_task.apply_async(
                args=[company_id, booking_id],
                eta=reminder_hour_datetime,
            )
            print(
                f"Запланировано напоминание за час: booking={booking_id}, eta={reminder_hour_datetime}"
            )
        elif not hour_enabled:
            print(f"Напоминание за час отключено в настройках компании {company_id}")
        else:
            print(
                f"Напоминание за час пропущено (уже прошло): booking={booking_id}, "
                f"было бы {reminder_hour_datetime}"
            )

    except Exception as e:
        print(f"Ошибка планирования напоминаний для записи {booking_id}: {e}")
        import traceback

        traceback.print_exc()


# Старые массовые задачи (оставляем для обратной совместимости, но не используем в расписании)
@shared_task
def send_reminder_day_before_task():
    """Celery задача для отправки напоминаний за день (массовая)"""
    try:
        _run_async(send_reminder_day_before())
    except Exception as e:
        print(f"Ошибка в задаче send_reminder_day_before_task: {e}")
        raise


@shared_task
def send_reminder_3_hours_before_task():
    """Celery задача для отправки напоминаний за час (массовая, имя историческое)"""
    try:
        _run_async(send_reminder_3_hours_before())
    except Exception as e:
        print(f"Ошибка в задаче send_reminder_3_hours_before_task: {e}")
        raise


async def send_status_change_notification_tenant(company_id: int, booking_id: int, new_status: str):
    """Отправить уведомление об изменении статуса записи клиенту (для tenant схем)"""
    from app.models.public_models import Company
    from aiogram import Bot
    
    async with async_session_maker() as session:
        # Получаем компанию и bot token из public схемы
        company_result = await session.execute(
            text('SELECT id, name, telegram_bot_token FROM public.companies WHERE id = :company_id'),
            {"company_id": company_id}
        )
        company_row = company_result.fetchone()
        
        if not company_row or not company_row[2]:
            print(f"[ERROR] Компания {company_id} не найдена или нет bot token")
            return
        
        bot_token = company_row[2]
        
        # Устанавливаем search_path для tenant схемы
        await session.execute(text(f'SET search_path TO "tenant_{company_id}", public'))
        
        # Получаем запись с клиентом
        booking_result = await session.execute(
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.client),
                selectinload(Booking.service),
            )
        )
        booking = booking_result.scalar_one_or_none()
        
        if not booking:
            print(f"[ERROR] Запись {booking_id} не найдена в tenant_{company_id}")
            return
        
        # Получаем telegram_id клиента
        telegram_id = None
        if booking.client and booking.client.user_id:
            # Получаем User из tenant схемы
            user_result = await session.execute(
                text(f'SELECT telegram_id FROM "tenant_{company_id}".users WHERE id = :user_id'),
                {"user_id": booking.client.user_id}
            )
            user_row = user_result.fetchone()
            if user_row and user_row[0]:
                telegram_id = user_row[0]
        
        if not telegram_id:
            print(f"[ERROR] Не найден telegram_id для клиента записи {booking_id}")
            return
        
        # Формируем сообщение
        status_messages = {
            "new": "🆕 Ваша запись создана и ожидает подтверждения.",
            "confirmed": "✅ Ваша запись подтверждена!",
            "completed": "✔️ Запись завершена. Спасибо за визит!",
            "cancelled": "❌ Запись отменена",
            "no_show": "⚠️ Вы не явились на запись",
        }
        
        message = status_messages.get(new_status, f"Статус записи изменен: {new_status}")
        
        try:
            date_str = booking.service_date.strftime("%d.%m.%Y")
            time_str = booking.time.strftime("%H:%M")
            service_name = booking.service.name if booking.service else "Услуга"
            
            text = f"{message}\n\n"
            text += f"Номер записи: {booking.booking_number}\n"
            text += f"Дата: {date_str}\n"
            text += f"Время: {time_str}\n"
            text += f"Услуга: {service_name}\n"
            
            print(f"[DEBUG] Отправляем сообщение в Telegram: company_id={company_id}, chat_id={telegram_id}, text_length={len(text)}")
            
            # Создаем бота с токеном компании
            bot = Bot(token=bot_token)
            result = await bot.send_message(
                chat_id=telegram_id,
                text=text
            )
            await bot.session.close()
            
            print(f"[SUCCESS] Сообщение отправлено успешно: message_id={result.message_id}")
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Ошибка отправки уведомления об изменении статуса для записи {booking_id}: {e}")
            print(f"[ERROR] Traceback: {error_trace}")


@shared_task
def send_status_change_notification_task(company_id: int, booking_id: int, new_status: str):
    """Celery задача для отправки уведомления об изменении статуса (для tenant схем)"""
    print(f"[CELERY TASK] Начало выполнения send_status_change_notification_task: company_id={company_id}, booking_id={booking_id}, status={new_status}")
    try:
        _run_async(send_status_change_notification_tenant(company_id, booking_id, new_status))
        print(f"[CELERY TASK] Успешно выполнена send_status_change_notification_task: booking_id={booking_id}")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[CELERY TASK ERROR] Ошибка в задаче send_status_change_notification_task: {e}")
        print(f"[CELERY TASK ERROR] Traceback: {error_trace}")
        raise


async def send_work_orders_to_masters():
    """Отправить лист-наряды всем мастерам на сегодня"""
    today = date.today()
    
    async with async_session_maker() as session:
        # Получаем всех мастеров (в модели Master нет поля is_active)
        result = await session.execute(
            select(Master)
            .options(selectinload(Master.user))
        )
        masters = result.scalars().all()
        
        bot = get_bot()
        
        for master in masters:
            if not master.user or not master.user.telegram_id:
                continue
            
            try:
                # Получаем записи мастера на сегодня
                bookings_result = await session.execute(
                    select(Booking)
                    .where(
                        and_(
                            Booking.master_id == master.id,
                            Booking.service_date == today,
                            Booking.status.in_(["confirmed", "new"])
                        )
                    )
                    .order_by(Booking.time.asc())
                    .options(
                        selectinload(Booking.client).selectinload(Client.user),
                        selectinload(Booking.service),
                        selectinload(Booking.post),
                    )
                )
                bookings = list(bookings_result.scalars().all())
                
                # Формируем текст лист-наряда
                text = f"📋 Лист-наряд на {today.strftime('%d.%m.%Y')}\n\n"
                
                if not bookings:
                    text += "✅ На сегодня записей нет"
                else:
                    for i, booking in enumerate(bookings, 1):
                        client = booking.client
                        service = booking.service
                        post = booking.post
                        
                        text += f"{i}. ⏰ {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                        text += f"   🛠️ {service.name if service else 'Не указана'}\n"
                        text += f"   👤 {client.full_name if client else 'Неизвестно'}\n"
                        if client and client.phone:
                            text += f"   📞 {client.phone}\n"
                        if client and client.car_number:
                            text += f"   🚗 {client.car_number}\n"
                        if post:
                            text += f"   🏢 Пост №{post.number} {post.name or ''}\n"
                        text += f"   📊 Статус: {booking.status}\n"
                        if booking.comment:
                            text += f"   💬 {booking.comment}\n"
                        text += "\n"
                
                # Отправляем лист-наряд мастеру
                await bot.send_message(
                    chat_id=master.user.telegram_id,
                    text=text
                )
                
                print(f"Лист-наряд отправлен мастеру {master.id} ({master.full_name})")
                
            except Exception as e:
                print(f"Ошибка отправки лист-наряда мастеру {master.id}: {e}")


async def notify_admin_new_bookings():
    """Уведомить администраторов о новых записях"""
    from datetime import timedelta
    
    # Записи со статусом "new", созданные не более 10 минут назад (чтобы не пропустить новые)
    cutoff_time = datetime.utcnow() - timedelta(minutes=10)
    
    async with async_session_maker() as session:
        # Находим новые записи, которые еще не были уведомлены
        result = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.status == "new",
                    Booking.created_at >= cutoff_time,  # Изменено: >= вместо <=
                    # Проверяем, что нет уведомления об этой записи
                    ~Booking.id.in_(
                        select(Notification.booking_id)
                        .where(Notification.notification_type == "admin_new_booking")
                    )
                )
            )
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
            )
            .order_by(Booking.created_at.desc())
        )
        new_bookings = result.scalars().all()
        
        if not new_bookings:
            return
        
        # Получаем всех администраторов
        admins_result = await session.execute(
            select(User).where(
                and_(
                    User.is_admin == True,
                    User.telegram_id.isnot(None)
                )
            )
        )
        admins = admins_result.scalars().all()
        
        if not admins:
            return
        
        bot = get_bot()
        
        # Формируем сообщение
        text = f"🔔 Новые записи ({len(new_bookings)})\n\n"
        
        for booking in new_bookings[:10]:  # Показываем максимум 10 последних
            date_str = booking.service_date.strftime("%d.%m.%Y")
            time_str = booking.time.strftime("%H:%M")
            client_name = booking.client.full_name if booking.client else "Неизвестно"
            service_name = booking.service.name if booking.service else "Не указана"
            
            text += f"📋 {booking.booking_number}\n"
            text += f"   👤 {client_name}\n"
            text += f"   📅 {date_str} в {time_str}\n"
            text += f"   🛠️ {service_name}\n\n"
        
        if len(new_bookings) > 10:
            text += f"... и еще {len(new_bookings) - 10} записей"
        
        # Отправляем уведомление всем администраторам
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin.telegram_id,
                    text=text
                )
                
                # Сохраняем уведомления в БД
                for booking in new_bookings:
                    notification = Notification(
                        user_id=admin.id,
                        booking_id=booking.id,
                        notification_type="admin_new_booking",
                        message=text,
                        is_sent=True,
                        sent_at=datetime.utcnow()
                    )
                    session.add(notification)
                
            except Exception as e:
                print(f"Ошибка отправки уведомления администратору {admin.id}: {e}")
                # Сохраняем ошибку
                for booking in new_bookings:
                    notification = Notification(
                        user_id=admin.id,
                        booking_id=booking.id,
                        notification_type="admin_new_booking",
                        message=text,
                        is_sent=False,
                        error_message=str(e)
                    )
                    session.add(notification)
        
        await session.commit()


# Celery задачи для новых функций
@shared_task
def send_work_orders_to_masters_task():
    """Celery задача для отправки лист-нарядов мастерам"""
    try:
        _run_async(send_work_orders_to_masters())
    except Exception as e:
        print(f"Ошибка в задаче send_work_orders_to_masters_task: {e}")
        raise


@shared_task
def notify_admin_new_bookings_task():
    """Celery задача для уведомления администраторов о новых записях.

    Заглушка Notification без ORM-полей ломает select — пока no-op,
    чтобы beat не сыпал ошибками каждые 10 минут. Напоминания клиентам
    работают через send_reminder_* / send_single_reminder_*.
    """
    print(
        "notify_admin_new_bookings_task: пропущено "
        "(модель Notification — заглушка, нужен multi-tenant SQL)"
    )
    return None

