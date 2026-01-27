"""Обработчики лист-наряда для мастеров"""
import logging
from calendar import monthrange
from datetime import date, datetime
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select, and_, text, or_
from sqlalchemy.orm import selectinload, load_only

from bot.database.connection import get_session, async_session_maker, AsyncSession
from bot.database.crud import get_user_by_telegram_id
from shared.database.models import Master, Booking, Client, User
from bot.keyboards.master import get_work_order_keyboard, get_booking_actions_keyboard, get_master_main_keyboard
from bot.utils.calendar import generate_calendar

logger = logging.getLogger(__name__)
router = Router()


async def get_company_id_by_bot_token(bot_token: str) -> Optional[int]:
    """Получить company_id по токену бота."""
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
            {"token": bot_token},
        )
        row = result.fetchone()
        if row:
            return row[0]
    return None


async def get_master_for_telegram(
    session: AsyncSession,
    telegram_id: int,
    company_id: int,
) -> Optional[Master]:
    """Получить мастера по telegram_id или user_id в tenant схеме."""
    schema_name = f"tenant_{company_id}"
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))

    # Сначала пытаемся найти мастера по telegram_id
    result = await session.execute(
        text(
            """
            SELECT id, user_id, full_name, phone, telegram_id, specialization, is_universal
            FROM masters
            WHERE telegram_id = :telegram_id
            LIMIT 1
            """
        ),
        {"telegram_id": telegram_id},
    )
    row = result.fetchone()
    
    if row:
        master = type('Master', (), {})()
        master.id = row[0]
        master.user_id = row[1]
        master.full_name = row[2]
        master.phone = row[3]
        master.telegram_id = row[4]
        master.specialization = row[5]
        master.is_universal = row[6] if row[6] is not None else True
        logger.info(f"✅ Мастер найден по telegram_id: id={master.id}, user_id={master.user_id}")
        return master
    
    # Если не нашли по telegram_id, ищем по user_id
    user = await get_user_by_telegram_id(session, telegram_id, company_id=company_id)
    if user:
        result = await session.execute(
            text(
                """
                SELECT id, user_id, full_name, phone, telegram_id, specialization, is_universal
                FROM masters
                WHERE user_id = :user_id
                LIMIT 1
                """
            ),
            {"user_id": user.id},
        )
        row = result.fetchone()
        if row:
            master = type('Master', (), {})()
            master.id = row[0]
            master.user_id = row[1]
            master.full_name = row[2]
            master.phone = row[3]
            master.telegram_id = row[4]
            master.specialization = row[5]
            master.is_universal = row[6] if row[6] is not None else True
            logger.info(f"✅ Мастер найден по user_id: id={master.id}, user_id={master.user_id}")
            return master
    
    logger.warning(f"⚠️ Мастер не найден для telegram_id={telegram_id}, company_id={company_id}")
    return None


@router.message(Command("master"))
async def cmd_master(message: Message):
    """Команда /master"""
    company_id = await get_company_id_by_bot_token(message.bot.token)
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота. Обратитесь к администратору.")
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, message.from_user.id, company_id)

        if not master:
            await message.answer(
                "❌ Вы не зарегистрированы как мастер.\n"
                "Обратитесь к администратору для добавления в систему."
            )
            return

        # Показываем меню мастера
        await message.answer(
            "👨‍🔧 Панель мастера\n\n"
            "Выберите действие:",
            reply_markup=get_master_main_keyboard()
        )


@router.message(F.text == "📋 Лист-наряд")
async def show_work_order_today(message: Message):
    """Показать лист-наряд на сегодня"""
    company_id = await get_company_id_by_bot_token(message.bot.token)
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота. Обратитесь к администратору.")
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, message.from_user.id, company_id)

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер")
            return

        logger.info(f"Мастер найден: id={master.id}, user_id={master.user_id}, telegram_id={message.from_user.id}, company_id={company_id}")
        await show_work_order(message, master.id, date.today(), company_id, master.user_id)


async def _get_master_work_orders(
    session: AsyncSession,
    company_id: int,
    master_id: int,
    work_date: date,
    master_user_id: Optional[int] = None,
) -> list[dict]:
    """Получить лист-наряд мастера на дату (без ORM-связей)."""
    schema_name = f"tenant_{company_id}"
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    
    logger.info(f"Поиск записей: schema={schema_name}, master_id={master_id}, master_user_id={master_user_id}, date={work_date}")
    
    params = {"master_id": master_id, "work_date": work_date}
    
    # Если есть user_id мастера, логируем для отладки
    if master_user_id:
        logger.info(f"Мастер имеет user_id={master_user_id}, поиск идет по master_id={master_id}")
    
    result = await session.execute(
        text(
            """
            SELECT
                b.id,
                b.booking_number,
                b.service_date,
                b.time,
                b.end_time,
                b.status,
                b.comment,
                b.confirmed_at,
                b.completed_at,
                c.full_name AS client_name,
                c.phone AS client_phone,
                s.name AS service_name,
                p.name AS post_name
            FROM bookings b
            LEFT JOIN clients c ON c.id = b.client_id
            LEFT JOIN services s ON s.id = b.service_id
            LEFT JOIN posts p ON p.id = b.post_id
            WHERE b.master_id = :master_id
              AND b.service_date = :work_date
              AND b.status IN ('confirmed', 'new', 'completed')
            ORDER BY b.time ASC
            """
        ),
        params,
    )
    rows = result.fetchall()
    logger.info(f"Найдено записей: {len(rows)} для master_id={master_id}, date={work_date}")
    bookings: list[dict] = []
    for row in rows:
        bookings.append(
            {
                "id": row[0],
                "booking_number": row[1],
                "service_date": row[2],
                "time": row[3],
                "end_time": row[4],
                "status": row[5],
                "comment": row[6],
                "confirmed_at": row[7],
                "completed_at": row[8],
                "client_name": row[9],
                "client_phone": row[10],
                "service_name": row[11],
                "post_name": row[12],
            }
        )
    return bookings


async def show_work_order(message: Message, master_id: int, work_date: date, company_id: int, master_user_id: Optional[int] = None):
    """Показать лист-наряд мастера на дату"""
    async for session in get_session():
        bookings = await _get_master_work_orders(session, company_id, master_id, work_date, master_user_id)
        
        logger.info(f"Записи для мастера: master_id={master_id}, date={work_date}, company_id={company_id}, найдено={len(bookings)}")

        if not bookings:
            await message.answer(
                f"📋 Лист-наряд на {work_date.strftime('%d.%m.%Y')}\n\n"
                f"✅ На этот день записей нет",
                reply_markup=get_work_order_keyboard([], work_date)
            )
            return

        # Формируем текст лист-наряда
        message_text = f"📋 Лист-наряд на {work_date.strftime('%d.%m.%Y')}\n\n"
        
        for i, booking in enumerate(bookings, 1):
            message_text += (
                f"{i}. ⏰ {booking['time'].strftime('%H:%M')} - {booking['end_time'].strftime('%H:%M')}\n"
            )
            message_text += f"   🛠️ {booking['service_name'] or 'Не указана'}\n"
            message_text += f"   👤 {booking['client_name'] or 'Неизвестно'}\n"
            if booking["client_phone"]:
                message_text += f"   📞 {booking['client_phone']}\n"
            if booking["post_name"]:
                message_text += f"   🏢 {booking['post_name']}\n"
            
            # Статус с информацией о явке
            status_text = booking['status']
            if booking.get("confirmed_at"):
                confirmed_dt = booking["confirmed_at"]
                if isinstance(confirmed_dt, datetime):
                    status_text += f" ✅ Явка: {confirmed_dt.strftime('%H:%M')}"
            if booking.get("completed_at"):
                completed_dt = booking["completed_at"]
                if isinstance(completed_dt, datetime):
                    status_text += f" 🏁 Завершено: {completed_dt.strftime('%H:%M')}"
            
            message_text += f"   📊 Статус: {status_text}\n"
            if booking["comment"]:
                message_text += f"   💬 {booking['comment']}\n"
            message_text += "\n"

        await message.answer(
            message_text,
            reply_markup=get_work_order_keyboard(bookings, work_date)
        )


async def get_master_busy_dates(
    session: AsyncSession,
    company_id: int,
    master_id: int,
    start_date: date,
    end_date: date,
) -> set[date]:
    """Получить даты с записями для мастера в заданном диапазоне."""
    schema_name = f"tenant_{company_id}"
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
    result = await session.execute(
        text(
            """
            SELECT DISTINCT b.service_date
            FROM bookings b
            WHERE b.master_id = :master_id
              AND b.service_date >= :start_date
              AND b.service_date <= :end_date
              AND b.status IN ('confirmed', 'new', 'completed')
            ORDER BY b.service_date ASC
            """
        ),
        {
            "master_id": master_id,
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    rows = result.fetchall()
    return {row[0] for row in rows if row[0]}


async def build_master_calendar(
    session: AsyncSession,
    master_id: int,
    company_id: int,
    year: int,
    month: int,
):
    """Собрать календарь занятых дат для мастера."""
    schema_name = f"tenant_{company_id}"
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))

    today = date.today()
    start_date = date(year, month, 1)
    if start_date < today:
        start_date = today
    last_day = monthrange(year, month)[1]
    end_date = date(year, month, last_day)

    available_dates = await get_master_busy_dates(session, company_id, master_id, start_date, end_date)
    calendar = generate_calendar(
        year,
        month,
        available_dates,
        today,
        date_callback_prefix="master_calendar_date",
        month_callback_prefix="master_calendar_month",
        cancel_callback="master_calendar_close",
    )
    calendar.inline_keyboard.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_work_order")]
    )
    return calendar, available_dates


@router.callback_query(F.data == "master_calendar_open")
async def open_master_calendar(callback: CallbackQuery):
    """Открыть календарь лист-нарядов мастера."""
    company_id = await get_company_id_by_bot_token(callback.bot.token)
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, callback.from_user.id, company_id)
        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        today = date.today()
        calendar, available_dates = await build_master_calendar(
            session,
            master.id,
            company_id,
            today.year,
            today.month,
        )
        text_message = (
            "📅 Выберите дату с записями:"
            if available_dates
            else "📅 В этом месяце нет записей. Переключите месяц."
        )
        await callback.message.edit_text(text_message, reply_markup=calendar)
        await callback.answer()


@router.callback_query(F.data.startswith("master_calendar_month_"))
async def change_master_calendar_month(callback: CallbackQuery):
    """Смена месяца в календаре мастера."""
    try:
        parts = callback.data.split("_")
        year = int(parts[3])
        month = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    company_id = await get_company_id_by_bot_token(callback.bot.token)
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, callback.from_user.id, company_id)
        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        calendar, available_dates = await build_master_calendar(
            session,
            master.id,
            company_id,
            year,
            month,
        )
        text_message = (
            "📅 Выберите дату с записями:"
            if available_dates
            else "📅 В этом месяце нет записей. Переключите месяц."
        )
        await callback.message.edit_text(text_message, reply_markup=calendar)
        await callback.answer()


@router.callback_query(F.data.startswith("master_calendar_date_"))
async def select_master_calendar_date(callback: CallbackQuery):
    """Выбор даты из календаря мастера."""
    try:
        parts = callback.data.split("_")
        year = int(parts[3])
        month = int(parts[4])
        day = int(parts[5])
        selected_date = date(year, month, day)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора даты", show_alert=True)
        return

    company_id = await get_company_id_by_bot_token(callback.bot.token)
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, callback.from_user.id, company_id)
        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        await show_work_order(callback.message, master.id, selected_date, company_id, master.user_id)
        await callback.answer()


@router.callback_query(F.data == "master_calendar_close")
async def close_master_calendar(callback: CallbackQuery):
    """Закрыть календарь мастера и вернуться к лист-наряду."""
    await back_to_work_order(callback)


@router.callback_query(F.data.startswith("master_booking_"))
async def show_booking_for_master(callback: CallbackQuery):
    """Показать детали записи для мастера"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        company_id = await get_company_id_by_bot_token(callback.bot.token)
        if not company_id:
            await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
            return

        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        result = await session.execute(
            text(
                """
                SELECT
                    b.id,
                    b.booking_number,
                    b.time,
                    b.end_time,
                    b.status,
                    b.comment,
                    b.confirmed_at,
                    b.completed_at,
                    c.full_name AS client_name,
                    c.phone AS client_phone,
                    s.name AS service_name,
                    p.name AS post_name
                FROM bookings b
                LEFT JOIN clients c ON c.id = b.client_id
                LEFT JOIN services s ON s.id = b.service_id
                LEFT JOIN posts p ON p.id = b.post_id
                WHERE b.id = :booking_id
                """
            ),
            {"booking_id": booking_id},
        )
        row = result.fetchone()
        if not row:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return

        text = f"📋 Запись #{row[1]}\n\n"
        text += f"⏰ Время: {row[2].strftime('%H:%M')} - {row[3].strftime('%H:%M')}\n"
        text += f"🛠️ Услуга: {row[10] or 'Не указана'}\n"
        text += f"👤 Клиент: {row[8] or 'Неизвестно'}\n"
        if row[9]:
            text += f"📞 Телефон: {row[9]}\n"
        if row[11]:
            text += f"🏢 Рабочее место: {row[11]}\n"
        text += f"📊 Статус: {row[4]}\n"
        
        # Информация о явке
        if row[6]:  # confirmed_at
            confirmed_dt = row[6] if isinstance(row[6], datetime) else None
            if confirmed_dt:
                text += f"✅ Явка подтверждена: {confirmed_dt.strftime('%d.%m.%Y %H:%M')}\n"
        
        # Информация о завершении
        if row[7]:  # completed_at
            completed_dt = row[7] if isinstance(row[7], datetime) else None
            if completed_dt:
                text += f"🏁 Завершено: {completed_dt.strftime('%d.%m.%Y %H:%M')}\n"
        
        if row[5]:
            text += f"\n💬 Комментарий: {row[5]}\n"

        # Показываем кнопки действий только для подтвержденных записей (не завершенных)
        if row[4] == "confirmed":
            await callback.message.edit_text(
                text,
                reply_markup=get_booking_actions_keyboard(booking_id)
            )
        else:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_work_order")],
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
        
        await callback.answer()


@router.callback_query(F.data.startswith("complete_booking_"))
async def complete_booking(callback: CallbackQuery):
    """Завершить запись"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        from bot.database.crud import update_booking_status
        booking = await update_booking_status(session, booking_id, "completed")
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return

        await callback.message.edit_text(
            f"✅ Запись #{booking.booking_number} завершена!\n\n"
            f"Работа выполнена."
        )
        await callback.answer("✅ Запись завершена")


@router.callback_query(F.data == "refresh_work_order")
async def refresh_work_order(callback: CallbackQuery):
    """Обновить лист-наряд"""
    company_id = await get_company_id_by_bot_token(callback.bot.token)
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, callback.from_user.id, company_id)

        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        await show_work_order(callback.message, master.id, date.today(), company_id, master.user_id)
        await callback.answer("🔄 Лист-наряд обновлен")


@router.callback_query(F.data == "back_to_work_order")
async def back_to_work_order(callback: CallbackQuery):
    """Вернуться к лист-наряду"""
    company_id = await get_company_id_by_bot_token(callback.bot.token)
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, callback.from_user.id, company_id)

        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        # Используем ту же функцию, что и для обычного лист-наряда
        work_date = date.today()
        bookings = await _get_master_work_orders(session, company_id, master.id, work_date)

        if not bookings:
            await callback.message.edit_text(
                f"📋 Лист-наряд на {work_date.strftime('%d.%m.%Y')}\n\n"
                f"✅ На этот день записей нет",
                reply_markup=get_work_order_keyboard([], work_date)
            )
        else:
            # Формируем текст лист-наряда
            message_text = f"📋 Лист-наряд на {work_date.strftime('%d.%m.%Y')}\n\n"
            
            for i, booking in enumerate(bookings, 1):
                message_text += (
                    f"{i}. ⏰ {booking['time'].strftime('%H:%M')} - {booking['end_time'].strftime('%H:%M')}\n"
                )
                message_text += f"   🛠️ {booking['service_name'] or 'Не указана'}\n"
                message_text += f"   👤 {booking['client_name'] or 'Неизвестно'}\n"
                if booking["client_phone"]:
                    message_text += f"   📞 {booking['client_phone']}\n"
                if booking["post_name"]:
                    message_text += f"   🏢 {booking['post_name']}\n"
                
                # Статус с информацией о явке
                status_text = booking['status']
                if booking.get("confirmed_at"):
                    confirmed_dt = booking["confirmed_at"]
                    if isinstance(confirmed_dt, datetime):
                        status_text += f" ✅ Явка: {confirmed_dt.strftime('%H:%M')}"
                if booking.get("completed_at"):
                    completed_dt = booking["completed_at"]
                    if isinstance(completed_dt, datetime):
                        status_text += f" 🏁 Завершено: {completed_dt.strftime('%H:%M')}"
                
                message_text += f"   📊 Статус: {status_text}\n"
                if booking["comment"]:
                    message_text += f"   💬 {booking['comment']}\n"
                message_text += "\n"

            await callback.message.edit_text(
                message_text,
                reply_markup=get_work_order_keyboard(bookings, work_date)
            )
        
        await callback.answer()


@router.message(F.text == "🚪 Выход из панели мастера")
async def exit_master_panel(message: Message):
    """Выход из панели мастера"""
    company_id = await get_company_id_by_bot_token(message.bot.token)
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота. Обратитесь к администратору.")
        return

    async for session in get_session():
        master = await get_master_for_telegram(session, message.from_user.id, company_id)

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер")
            return

        # Убираем мастер-клавиатуру и показываем обычную
        from bot.keyboards.client import get_client_main_keyboard
        await message.answer(
            "✅ Вы вышли из панели мастера",
            reply_markup=get_client_main_keyboard()
        )

