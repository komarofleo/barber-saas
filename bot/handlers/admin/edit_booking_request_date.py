"""Обработчик редактирования даты заявки записи."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.connection import get_session
from bot.database.crud import (
    get_available_dates,
    get_booking_by_id,
    get_user_by_telegram_id,
    update_booking_request_date,
)
from bot.handlers.admin.bookings_edit import get_company_context_from_bot, is_company_admin_from_bot
from bot.keyboards.admin import get_edit_request_date_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("edit_request_date_"))
async def edit_request_date_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование даты заявки."""
    try:
        # edit_request_date_<booking_id>
        booking_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get("company_id")
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    try:
        async for session in get_session():
            booking = await get_booking_by_id(session, booking_id, company_id=company_id)
            if not booking:
                await callback.answer("❌ Запись не найдена", show_alert=True)
                return

            user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет прав", show_alert=True)
                return

            today = date.today()
            available_dates = await get_available_dates(session, today, today + timedelta(days=60))
            current_request_date = (
                booking.request_date.strftime("%d.%m.%Y") if booking.request_date else "Не задана"
            )
            await callback.message.edit_text(
                f"📋 Редактирование записи #{booking.booking_number}\n\n"
                f"📝 Текущая дата заявки: {current_request_date}\n\n"
                f"─────────────────────────────\n\n"
                f"📅 Выберите новую дату заявки:",
                reply_markup=get_edit_request_date_keyboard(booking_id, current_request_date),
            )
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании даты заявки: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("change_request_date_"))
async def change_request_date(callback: CallbackQuery, state: FSMContext):
    """Изменить дату заявки."""
    try:
        # change_request_date_<delta>_<booking_id>
        parts = callback.data.split("_")
        days_delta = int(parts[3])
        booking_id = int(parts[4])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get("company_id")
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    try:
        async for session in get_session():
            booking = await get_booking_by_id(session, booking_id, company_id=company_id)
            if not booking:
                await callback.answer("❌ Запись не найдена", show_alert=True)
                return

            user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет прав", show_alert=True)
                return

            if booking.request_date:
                new_request_date = booking.request_date + timedelta(days=days_delta)
            else:
                new_request_date = date.today() + timedelta(days=days_delta)

            if new_request_date < date.today():
                await callback.answer("❌ Нельзя выбрать дату в прошлом", show_alert=True)
                return

            await state.update_data(booking_id=booking_id, new_request_date=new_request_date)
            await callback.message.edit_text(
                f"📋 Выбрана новая дата заявки: {new_request_date.strftime('%d.%m.%Y')}\n\n"
                f"─────────────────────────────\n\n"
                f"📅 Выберите действие:"
            )
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при изменении даты заявки: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("confirm_request_date_"))
async def confirm_request_date(callback: CallbackQuery, state: FSMContext):
    """Подтвердить изменение даты заявки."""
    try:
        # confirm_request_date_<booking_id>
        booking_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get("company_id")
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    data = await state.get_data()
    new_request_date = data.get("new_request_date")
    if not new_request_date:
        await callback.answer("❌ Новая дата не выбрана", show_alert=True)
        return

    try:
        async for session in get_session():
            booking = await get_booking_by_id(session, booking_id, company_id=company_id)
            if not booking:
                await callback.answer("❌ Запись не найдена", show_alert=True)
                return

            user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет прав", show_alert=True)
                return

            updated_booking = await update_booking_request_date(
                session,
                booking_id,
                new_request_date=new_request_date,
                company_id=company_id,
            )
            await state.clear()
            await callback.message.edit_text(
                f"✅ Дата заявки обновлена!\n\n"
                f"📝 Новая дата заявки: "
                f"{updated_booking.request_date.strftime('%d.%m.%Y') if updated_booking and updated_booking.request_date else new_request_date.strftime('%d.%m.%Y')}\n\n"
                f"Запись #{updated_booking.booking_number if updated_booking else booking_id}"
            )
            await callback.answer("✅ Дата заявки обновлена!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении даты заявки: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("cancel_edit_request_date"))
async def cancel_edit_request_date(callback: CallbackQuery, state: FSMContext):
    """Отменить редактирование даты заявки."""
    try:
        await state.clear()
        await callback.message.edit_text("❌ Редактирование даты заявки отменено")
        await callback.answer("❌ Отменено")
    except Exception as e:
        logger.error(f"Ошибка отмены редактирования даты заявки: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)
