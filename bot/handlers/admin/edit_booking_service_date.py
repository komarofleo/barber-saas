"""Обработчик редактирования даты услуги записи."""

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
)
from bot.handlers.admin.bookings import show_booking_details
from bot.handlers.admin.bookings_edit import get_company_context_from_bot
from bot.keyboards.admin import get_edit_service_date_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("edit_service_date_"))
async def edit_service_date_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование даты услуги."""
    try:
        # edit_service_date_<booking_id>
        booking_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    try:
        ctx = get_company_context_from_bot(callback.bot)
        company_id = ctx.get("company_id")
        if not company_id:
            await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
            return

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
            current_service_date = (
                booking.service_date.strftime("%d.%m.%Y") if booking.service_date else "Не задана"
            )
            await callback.message.edit_text(
                f"📋 Редактирование записи #{booking.booking_number}\n\n"
                f"📅 Текущая дата услуги: {current_service_date}\n\n"
                f"📝 Дата заявки: {booking.request_date.strftime('%d.%m.%Y') if booking.request_date else 'Не задана'}\n\n"
                f"─────────────────────────────\n\n"
                f"📅 Выберите новую дату услуги:",
                reply_markup=get_edit_service_date_keyboard(booking_id, current_service_date),
            )
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании даты: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("change_service_date_"))
async def change_service_date(callback: CallbackQuery, state: FSMContext):
    """Изменить дату услуги."""
    try:
        # change_service_date_<delta>_<booking_id>
        parts = callback.data.split("_")
        days_delta = int(parts[3])
        booking_id = int(parts[4])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    try:
        ctx = get_company_context_from_bot(callback.bot)
        company_id = ctx.get("company_id")
        if not company_id:
            await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
            return

        async for session in get_session():
            booking = await get_booking_by_id(session, booking_id, company_id=company_id)
            if not booking:
                await callback.answer("❌ Запись не найдена", show_alert=True)
                return

            new_service_date = booking.service_date + timedelta(days=days_delta)
            if new_service_date < date.today():
                await callback.answer("❌ Нельзя выбрать дату в прошлом", show_alert=True)
                return

            await state.update_data(booking_id=booking_id, new_service_date=new_service_date.isoformat())
            await callback.message.edit_text(
                f"📋 Выбрана новая дата услуги: {new_service_date.strftime('%d.%m.%Y')}\n\n"
                f"─────────────────────────────\n\n"
                f"📅 Выберите действие:"
            )
            await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при изменении даты: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("confirm_service_date_"))
async def confirm_service_date(callback: CallbackQuery, state: FSMContext):
    """Подтвердить изменение даты услуги."""
    try:
        # confirm_service_date_<booking_id>
        booking_id = int(callback.data.split("_")[-1])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    try:
        ctx = get_company_context_from_bot(callback.bot)
        company_id = ctx.get("company_id")
        if not company_id:
            await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
            return

        async for session in get_session():
            booking = await get_booking_by_id(session, booking_id, company_id=company_id)
            if not booking:
                await callback.answer("❌ Запись не найдена", show_alert=True)
                return

            user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
            if not user or not user.is_admin:
                await callback.answer("❌ У вас нет прав", show_alert=True)
                return

            callback_copy = callback.model_copy(update={"data": f"booking_{booking_id}"})
            await show_booking_details(callback_copy, state)
            await callback.answer("✅ Дата услуги обновлена!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении даты: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка", show_alert=True)


@router.callback_query(F.data.startswith("cancel_edit_service_date"))
async def cancel_edit_service_date(callback: CallbackQuery):
    """Отменить редактирование даты услуги."""
    try:
        await callback.message.edit_text(
            "❌ Редактирование даты услуги отменено\n\n📋 Детали записи:"
        )
        await callback.answer("❌ Отменено")
    except Exception as e:
        logger.error(f"Ошибка отмены редактирования даты услуги: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)
