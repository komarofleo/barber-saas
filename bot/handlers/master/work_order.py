"""Обработчики лист-наряда для мастеров"""
import logging
from calendar import monthrange
from datetime import date
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from sqlalchemy import select, and_, text, or_

from bot.database.connection import get_session, async_session_maker, AsyncSession
from bot.database.crud import get_user_by_telegram_id
from shared.database.models import Master, Booking
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

    user = await get_user_by_telegram_id(session, telegram_id, company_id=company_id)

    conditions = [Master.telegram_id == telegram_id]
    if user:
        conditions.append(Master.user_id == user.id)

    result = await session.execute(
        select(Master).where(or_(*conditions))
    )
    return result.scalar_one_or_none()


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

        await show_work_order(message, master.id, date.today(), company_id)


async def _get_master_work_orders(
    session: AsyncSession,
    company_id: int,
    master_id: int,
    work_date: date,
) -> list[dict]:
    """Получить лист-наряд мастера на дату (без ORM-связей)."""
    schema_name = f"tenant_{company_id}"
    await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
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
              AND b.status IN ('confirmed', 'new')
            ORDER BY b.time ASC
            """
        ),
        {"master_id": master_id, "work_date": work_date},
    )
    rows = result.fetchall()
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
                "client_name": row[7],
                "client_phone": row[8],
                "service_name": row[9],
                "post_name": row[10],
            }
        )
    return bookings


async def show_work_order(message: Message, master_id: int, work_date: date, company_id: int):
    """Показать лист-наряд мастера на дату"""
    async for session in get_session():
        bookings = await _get_master_work_orders(session, company_id, master_id, work_date)

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
            message_text += f"   📊 Статус: {booking['status']}\n"
            if booking["comment"]:
                message_text += f"   💬 {booking['comment']}\n"
            message_text += "\n"

        await message.answer(
            message_text,
            reply_markup=get_work_order_keyboard(bookings, work_date)
        )


async def get_master_busy_dates(
    session: AsyncSession,
    master_id: int,
    start_date: date,
    end_date: date,
) -> set[date]:
    """Получить даты с записями для мастера в заданном диапазоне."""
    result = await session.execute(
        select(Booking.service_date)
        .where(
            and_(
                Booking.master_id == master_id,
                Booking.service_date >= start_date,
                Booking.service_date <= end_date,
                Booking.status.in_(["confirmed", "new"]),
            )
        )
        .distinct()
    )
    return {row[0] for row in result.fetchall() if row[0]}


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

    available_dates = await get_master_busy_dates(session, master_id, start_date, end_date)
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

        await show_work_order(callback.message, master.id, selected_date, company_id)
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
        text += f"🛠️ Услуга: {row[8] or 'Не указана'}\n"
        text += f"👤 Клиент: {row[6] or 'Неизвестно'}\n"
        if row[7]:
            text += f"📞 Телефон: {row[7]}\n"
        if row[9]:
            text += f"🏢 Рабочее место: {row[9]}\n"
        text += f"📊 Статус: {row[4]}\n"
        if row[5]:
            text += f"\n💬 Комментарий: {row[5]}\n"

        # Показываем кнопки действий только для подтвержденных записей
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

        await show_work_order(callback.message, master.id, date.today(), company_id)
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

        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))

        # Получаем записи на сегодня
        result = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.master_id == master.id,
                    Booking.service_date == date.today(),
                    Booking.status.in_(["confirmed", "new"])
                )
            )
            .order_by(Booking.time.asc())
            .options(
                selectinload(Booking.client)
                .options(load_only(Client.id, Client.full_name, Client.phone, Client.user_id))
                .selectinload(Client.user)
                .options(
                    load_only(
                        User.id,
                        User.telegram_id,
                        User.username,
                        User.phone,
                        User.is_admin,
                        User.is_master,
                        User.is_blocked,
                    )
                ),
                selectinload(Booking.service),
                selectinload(Booking.post),
            )
        )
        bookings = list(result.scalars().all())

        if not bookings:
            await callback.message.edit_text(
                f"📋 Лист-наряд на {date.today().strftime('%d.%m.%Y')}\n\n"
                f"✅ На сегодня записей нет"
            )
        else:
            message_text = f"📋 Лист-наряд на {date.today().strftime('%d.%m.%Y')}\n\n"
            for i, booking in enumerate(bookings, 1):
                client = booking.client
                service = booking.service
                post = booking.post
                
                message_text += f"{i}. ⏰ {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                message_text += f"   🛠️ {service.name if service else 'Не указана'}\n"
                message_text += f"   👤 {client.full_name if client else 'Неизвестно'}\n"
                if post:
                    message_text += f"   🏢 {post.name}\n"
                message_text += "\n"

            await callback.message.edit_text(
                message_text,
                reply_markup=get_work_order_keyboard(bookings, date.today())
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

