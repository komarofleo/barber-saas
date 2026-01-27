"""Обработчик редактирования даты заявки записи"""
import logging
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, and_

from bot.database.connection import get_session
from bot.database.crud import (
    get_user_by_telegram_id,
    get_booking_by_id,
    get_available_dates,
    update_booking_request_date,
)
from bot.keyboards.admin.booking_actions import get_edit_request_date_keyboard
from bot.states.admin_states import AdminEditBookingStates
from bot.handlers.admin.bookings_edit import get_company_context_from_bot, is_company_admin_from_bot

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("edit_request_date_"))
async def edit_request_date_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование даты заявки"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    # Получаем company_id
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return
    
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    async for session in get_session():
        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        # Проверяем права админа
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return
        
        # Получаем доступные даты (на 2 месяца вперед)
        today = date.today()
        end_date = today + timedelta(days=60)
        available_dates = await get_available_dates(session, today, end_date, company_id=company_id)
        
        # Показываем клавиатуру для редактирования
        current_request_date = booking.request_date.strftime('%d.%m.%Y') if booking.request_date else 'Не задана'
        await callback.message.edit_text(
            f"📋 Редактирование записи #{booking.booking_number}\n\n"
            f"📝 Текущая дата заявки: {current_request_date}\n\n"
            f"─────────────────────────────\n\n"
            f"📅 Выберите новую дату заявки:",
            reply_markup=get_edit_request_date_keyboard(booking_id, current_request_date, available_dates)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при редактировании даты заявки: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("change_request_date_"))
async def change_request_date(callback: CallbackQuery, state: FSMContext):
    """Изменить дату заявки"""
    try:
        parts = callback.data.split("_")
        booking_id = int(parts[1])
        days_delta = int(parts[3])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return
    
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    async for session in get_session():
        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        # Проверяем права админа
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return
        
        # Вычисляем новую дату
        if booking.request_date:
            new_request_date = booking.request_date + timedelta(days=days_delta)
        else:
            new_request_date = date.today() + timedelta(days=days_delta)
        
        # Проверяем, что дата не в прошлом
        if new_request_date < date.today():
            await callback.answer("❌ Нельзя выбрать дату в прошлом", show_alert=True)
            return
        
        # Сохраняем новую дату в состоянии
        await state.update_data(booking_id=booking_id, new_request_date=new_request_date)
        
        # Показываем сообщение с новой датой
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
    """Подтвердить изменение даты заявки"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return
    
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    # Получаем сохраненную новую дату из состояния
    data = await state.get_data()
    new_request_date = data.get('new_request_date')
    
    if not new_request_date:
        await callback.answer("❌ Новая дата не выбрана", show_alert=True)
        return
    
    async for session in get_session():
        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        # Проверяем права админа
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return
        
        # Обновляем дату заявки в БД
        updated_booking = await update_booking_request_date(session, booking_id, new_request_date=new_request_date, company_id=company_id)
        
        # Очищаем состояние
        await state.clear()
        
        # Показываем сообщение об успехе
        await callback.message.edit_text(
            f"✅ Дата заявки обновлена!\n\n"
            f"📝 Новая дата заявки: {updated_booking.request_date.strftime('%d.%m.%Y') if updated_booking and updated_booking.request_date else new_request_date.strftime('%d.%m.%Y')}\n\n"
            f"Запись #{updated_booking.booking_number if updated_booking else booking_id}"
        )
        await callback.answer("✅ Дата заявки обновлена!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении даты заявки: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("cancel_edit_request_date"))
async def cancel_edit_request_date(callback: CallbackQuery, state: FSMContext):
    """Отменить редактирование даты заявки"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга booking_id: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    # Очищаем состояние
    await state.clear()
    
    # Восстанавливаем предыдущее сообщение
    await callback.message.edit_text(
        "❌ Редактирование даты заявки отменено"
    )
    await callback.answer("❌ Отменено")
