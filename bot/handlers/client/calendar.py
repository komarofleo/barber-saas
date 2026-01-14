"""Обработчики календаря для выбора даты"""
import logging
from typing import Optional
from datetime import date, timedelta, time, datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database.connection import get_session
from bot.database.crud import get_available_dates, get_service_by_id
from bot.states.client_states import BookingStates
from bot.utils.calendar import generate_calendar

logger = logging.getLogger(__name__)
router = Router()


async def get_company_id_from_callback(callback: CallbackQuery) -> Optional[int]:
    """Получить company_id из токена бота"""
    try:
        from sqlalchemy import text
        from bot.database.connection import get_session
        bot_token = callback.bot.token
        async for session in get_session():
            result = await session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                return row[0]
            break
    except:
        pass
    return None


@router.callback_query(F.data.startswith("calendar_date_"), BookingStates.choosing_date)
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    try:
        parts = callback.data.split("_")
        year = int(parts[2])
        month = int(parts[3])
        day = int(parts[4])
        selected_date = date(year, month, day)
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга даты: {e}")
        await callback.answer("❌ Ошибка выбора даты", show_alert=True)
        return

    # Сохраняем выбранную дату
    await state.update_data(booking_date=selected_date)
    await state.set_state(BookingStates.choosing_time)

    # Получаем данные услуги из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    service_duration = data.get("service_duration", 60)

    # Получаем company_id из токена бота
    company_id = await get_company_id_from_callback(callback)
    
    async for session in get_session():
        service = await get_service_by_id(session, service_id, company_id=company_id)
        if not service:
            await callback.answer("❌ Услуга не найдена", show_alert=True)
            return

        # Генерируем доступные временные слоты
        from bot.utils.time_slots import generate_time_slots
        time_slots = await generate_time_slots(session, selected_date, service_duration)

        if not time_slots:
            await callback.message.edit_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет свободного времени.\n\n"
                f"Выберите другую дату."
            )
            # Показываем календарь снова
            today = date.today()
            end_date = today + timedelta(days=60)
            available_dates = await get_available_dates(session, today, end_date)
            calendar = generate_calendar(today.year, today.month, available_dates, today)
            await callback.message.edit_text(
                f"🛠️ Услуга: {service.name}\n"
                f"⏱️ Длительность: {service.duration} мин\n\n"
                f"📅 Выберите дату:",
                reply_markup=calendar
            )
            await callback.answer("❌ Нет свободного времени")
            return

        from bot.keyboards.client import get_time_slots_keyboard
        await callback.message.edit_text(
            f"🛠️ Услуга: {service.name}\n"
            f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
            f"⏰ Выберите время:",
            reply_markup=get_time_slots_keyboard(time_slots)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("calendar_month_"))
async def change_month(callback: CallbackQuery, state: FSMContext):
    """Смена месяца в календаре"""
    try:
        parts = callback.data.split("_")
        year = int(parts[2])
        month = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        # Получаем доступные даты
        today = date.today()
        start_date = date(year, month, 1)
        end_date = date(year, month, 28) + timedelta(days=4)  # До конца месяца
        available_dates = await get_available_dates(session, start_date, end_date)

        calendar = generate_calendar(year, month, available_dates, today)

        # Получаем данные услуги из состояния
        data = await state.get_data()
        service_id = data.get("service_id")

        # Получаем company_id из токена бота
        company_id = await get_company_id_from_callback(callback)
        
        if service_id:
            service = await get_service_by_id(session, service_id, company_id=company_id)
            if service:
                await callback.message.edit_text(
                    f"🛠️ Услуга: {service.name}\n"
                    f"⏱️ Длительность: {service.duration} мин\n\n"
                    f"📅 Выберите дату:",
                    reply_markup=calendar
                )
                await callback.answer()
                return

        await callback.message.edit_text(
            "📅 Выберите дату:",
            reply_markup=calendar
        )
        await callback.answer()


@router.callback_query(F.data == "calendar_empty")
async def handle_empty_calendar(callback: CallbackQuery):
    """Обработка пустых ячеек календаря"""
    await callback.answer("Эта дата недоступна", show_alert=False)


@router.callback_query(F.data == "calendar_header")
async def handle_calendar_header(callback: CallbackQuery):
    """Обработка заголовка календаря"""
    await callback.answer()


@router.callback_query(F.data == "calendar_weekday")
async def handle_calendar_weekday(callback: CallbackQuery):
    """Обработка дней недели"""
    await callback.answer()









