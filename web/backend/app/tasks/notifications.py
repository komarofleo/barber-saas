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


async def send_reminder_day_before():
    """Отправить напоминания за день до записи"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    async with async_session_maker() as session:
        # Находим подтвержденные записи на завтра
        result = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.date == tomorrow,
                    Booking.status == "confirmed"
                )
            )
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
                selectinload(Booking.master),
                selectinload(Booking.post),
            )
        )
        bookings = result.scalars().all()
        
        for booking in bookings:
            if not booking.client or not booking.client.user or not booking.client.user.telegram_id:
                continue
            
            try:
                # Формируем сообщение
                date_str = booking.date.strftime("%d.%m.%Y")
                time_str = booking.time.strftime("%H:%M")
                service_name = booking.service.name if booking.service else "Услуга"
                master_name = booking.master.full_name if booking.master else "Не назначен"
                post_number = f"Пост №{booking.post.number}" if booking.post else "Не назначен"
                
                text = "🔔 Напоминание о записи\n\n"
                text += f"Завтра {date_str} в {time_str}\n"
                text += f"Услуга: {service_name}\n"
                text += f"Мастер: {master_name}\n"
                text += f"{post_number}\n\n"
                text += "Ждем вас в автосервисе!"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Подтвердить явку", callback_data=f"confirm_attendance_{booking.id}")],
                    [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_booking_{booking.id}")],
                ])
                
                bot = get_bot()
                await bot.send_message(
                    chat_id=booking.client.user.telegram_id,
                    text=text,
                    reply_markup=keyboard
                )
                
                # Сохраняем в историю уведомлений
                notification = Notification(
                    user_id=booking.client.user.id,
                    booking_id=booking.id,
                    notification_type="reminder_day",
                    message=text,
                    is_sent=True,
                    sent_at=datetime.utcnow()
                )
                session.add(notification)
                
            except Exception as e:
                print(f"Ошибка отправки напоминания за день для записи {booking.id}: {e}")
                # Сохраняем ошибку
                notification = Notification(
                    user_id=booking.client.user.id,
                    booking_id=booking.id,
                    notification_type="reminder_day",
                    message=text,
                    is_sent=False,
                    error_message=str(e)
                )
                session.add(notification)
        
        await session.commit()


async def send_reminder_hour_before():
    """Отправить напоминания за час до записи"""
    now = datetime.now()
    target_time_start = (now + timedelta(hours=1, minutes=-10)).time()
    target_time_end = (now + timedelta(hours=1, minutes=10)).time()
    today = date.today()
    
    async with async_session_maker() as session:
        # Находим подтвержденные записи на сегодня в нужном временном диапазоне
        result = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.date == today,
                    Booking.status == "confirmed",
                    Booking.time >= target_time_start,
                    Booking.time <= target_time_end
                )
            )
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
                selectinload(Booking.post),
            )
        )
        bookings = result.scalars().all()
        
        for booking in bookings:
            if not booking.client or not booking.client.user or not booking.client.user.telegram_id:
                continue
            
            try:
                time_str = booking.time.strftime("%H:%M")
                service_name = booking.service.name if booking.service else "Услуга"
                post_number = f"Пост №{booking.post.number}" if booking.post else "Не назначен"
                
                text = "🔔 Напоминание\n\n"
                text += f"Через час ваша запись!\n"
                text += f"Время: {time_str}\n"
                text += f"Услуга: {service_name}\n"
                text += f"{post_number}\n\n"
                text += "Адрес: пр.Октября\n"
                text += "До встречи! 👋"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_attendance_{booking.id}")],
                    [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_booking_{booking.id}")],
                ])
                
                bot = get_bot()
                await bot.send_message(
                    chat_id=booking.client.user.telegram_id,
                    text=text,
                    reply_markup=keyboard
                )
                
                # Сохраняем в историю
                notification = Notification(
                    user_id=booking.client.user.id,
                    booking_id=booking.id,
                    notification_type="reminder_hour",
                    message=text,
                    is_sent=True,
                    sent_at=datetime.utcnow()
                )
                session.add(notification)
                
            except Exception as e:
                print(f"Ошибка отправки напоминания за час для записи {booking.id}: {e}")
                notification = Notification(
                    user_id=booking.client.user.id,
                    booking_id=booking.id,
                    notification_type="reminder_hour",
                    message=text,
                    is_sent=False,
                    error_message=str(e)
                )
                session.add(notification)
        
        await session.commit()


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
            date_str = booking.date.strftime("%d.%m.%Y")
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


# Celery задачи (синхронные обертки для асинхронных функций)
@shared_task
def send_reminder_day_before_task():
    """Celery задача для отправки напоминаний за день"""
    try:
        asyncio.run(send_reminder_day_before())
    except Exception as e:
        print(f"Ошибка в задаче send_reminder_day_before_task: {e}")
        raise


@shared_task
def send_reminder_hour_before_task():
    """Celery задача для отправки напоминаний за час"""
    try:
        asyncio.run(send_reminder_hour_before())
    except Exception as e:
        print(f"Ошибка в задаче send_reminder_hour_before_task: {e}")
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
            date_str = booking.date.strftime("%d.%m.%Y")
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
        asyncio.run(send_status_change_notification_tenant(company_id, booking_id, new_status))
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
                            Booking.date == today,
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
            date_str = booking.date.strftime("%d.%m.%Y")
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
        asyncio.run(send_work_orders_to_masters())
    except Exception as e:
        print(f"Ошибка в задаче send_work_orders_to_masters_task: {e}")
        raise


@shared_task
def notify_admin_new_bookings_task():
    """Celery задача для уведомления администраторов о новых записях"""
    try:
        asyncio.run(notify_admin_new_bookings())
    except Exception as e:
        print(f"Ошибка в задаче notify_admin_new_bookings_task: {e}")
        raise

