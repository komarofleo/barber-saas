"""Обработчики для редактирования заказов в админ-панели"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import date, time, timedelta, datetime

from bot.database.connection import get_session
from bot.database.crud import (
    get_user_by_telegram_id,
    get_booking_by_id,
    update_booking_status,
    update_booking_service_date,
    update_booking_request_date,
    get_masters,
    get_posts,
    get_all_clients,
    get_services,
    create_booking,
    get_available_dates,
)
from bot.keyboards.admin import (
    get_booking_actions_keyboard,
    get_edit_booking_keyboard,
    get_masters_keyboard,
    get_posts_keyboard,
)
from bot.states.admin_states import AdminBookingStates, AdminEditBookingStates
from bot.utils.calendar import generate_calendar
from bot.utils.time_slots import generate_time_slots
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = Router()


def get_company_context_from_bot(bot):
    """Получить контекст компании из диспетчера бота"""
    try:
        dp = getattr(bot, '_dispatcher', None)
        if dp:
            return {
                'company_id': dp.get('company_id'),
                'admin_telegram_id': dp.get('admin_telegram_id'),
                'admin_telegram_ids': dp.get('admin_telegram_ids', []),
            }
    except Exception as e:
        logger.error(f"❌ Ошибка получения контекста компании: {e}")
    return {}


def is_company_admin_from_bot(telegram_id: int, bot) -> bool:
    """Проверить, является ли пользователь админом компании"""
    ctx = get_company_context_from_bot(bot)
    admin_telegram_id = ctx.get('admin_telegram_id')
    admin_telegram_ids = ctx.get('admin_telegram_ids', [])
    
    if admin_telegram_id and admin_telegram_id == telegram_id:
        return True
    if telegram_id in admin_telegram_ids:
        return True
    return False


@router.callback_query(F.data.startswith("status_"))
async def change_booking_status(callback: CallbackQuery, state: FSMContext):
    """Изменить статус заказа"""
    try:
        parts = callback.data.split("_")
        booking_id = int(parts[1])
        new_status = parts[2]  # confirmed, cancelled, completed
    except (ValueError, IndexError):
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
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Обновляем статус
        booking = await update_booking_status(session, booking_id, new_status, company_id=company_id)
        
        if not booking:
            await callback.answer("❌ Ошибка при изменении статуса", show_alert=True)
            return

        # Получаем данные заказа для отображения
        # Используем данные из booking (уже обновленный объект)
        booking_number = getattr(booking, "booking_number", f"#{booking_id}")
        
        status_names = {
            "new": "Новый",
            "confirmed": "Подтвержден",
            "completed": "Завершен",
            "cancelled": "Отменен"
        }
        
        await callback.message.edit_text(
            f"✅ Статус заказа {booking_number} изменен на: {status_names.get(new_status, new_status)}"
        )
        await callback.answer("✅ Статус изменен")
        
        # Отправляем уведомление клиенту
        try:
            # Получаем данные клиента для уведомления
            client_result = await session.execute(
                text('''
                    SELECT c.user_id, u.telegram_id 
                    FROM bookings b
                    JOIN clients c ON b.client_id = c.id
                    LEFT JOIN users u ON c.user_id = u.id
                    WHERE b.id = :booking_id
                '''),
                {"booking_id": booking_id}
            )
            client_row = client_result.fetchone()
            
            if client_row and client_row[1]:  # client_row[1] = telegram_id
                client_telegram_id = client_row[1]
                
                # Получаем данные заказа для уведомления
                booking_data_result = await session.execute(
                    text('''
                        SELECT b.booking_number, b.service_date, b.time, s.name as service_name
                        FROM bookings b
                        LEFT JOIN services s ON b.service_id = s.id
                        WHERE b.id = :booking_id
                    '''),
                    {"booking_id": booking_id}
                )
                booking_data_row = booking_data_result.fetchone()
                
                if booking_data_row:
                    booking_number = booking_data_row[0]
                    booking_date = booking_data_row[1]
                    booking_time = booking_data_row[2]
                    service_name = booking_data_row[3] or "Не указана"
                    
                    # Формируем сообщение в зависимости от статуса
                    status_messages = {
                        "new": "🆕 Ваша запись создана и ожидает подтверждения.",
                        "confirmed": "✅ Ваша запись подтверждена!",
                        "completed": "✔️ Запись завершена. Спасибо за визит!",
                        "cancelled": "❌ Запись отменена",
                        "no_show": "⚠️ Вы не явились на запись",
                    }
                    
                    message = status_messages.get(new_status, f"Статус записи изменен: {new_status}")
                    
                    client_message = (
                        f"{message}\n\n"
                        f"📋 Номер записи: {booking_number}\n"
                        f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                        f"⏰ Время: {booking_time.strftime('%H:%M')}\n"
                        f"🛠️ Услуга: {service_name}"
                    )
                    
                    await callback.bot.send_message(
                        chat_id=client_telegram_id,
                        text=client_message
                    )
                    logger.info(f"✅ [HANDLER] Уведомление отправлено клиенту {client_telegram_id} о смене статуса на {new_status}")
                else:
                    logger.warning(
                        f"⚠️ [HANDLER] Не найдены данные записи для уведомления: booking_id={booking_id}"
                    )
            else:
                logger.warning(
                    f"⚠️ [HANDLER] У клиента нет telegram_id или запись не найдена: booking_id={booking_id}"
                )
        except Exception as e:
            logger.error(f"❌ [HANDLER] Ошибка отправки уведомления клиенту: {e}", exc_info=True)
        
        # Обновляем сообщение с деталями заказа
        from bot.handlers.admin.bookings import show_booking_details
        # Вызываем обработчик показа деталей заказа без изменения callback.data (frozen)
        callback_copy = callback.model_copy(update={"data": f"booking_{booking_id}"})
        await show_booking_details(callback_copy, state)


@router.callback_query(F.data.startswith("edit_payment_"))
async def edit_booking_payment(callback: CallbackQuery, state: FSMContext):
    """Изменить оплату заказа"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    logger.info(f"🟢 [ADMIN] Запрос изменения даты/времени: booking_id={booking_id}")

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    # Сохраняем booking_id в состояние
    await state.update_data(booking_id=booking_id)
    await state.set_state(AdminEditBookingStates.editing_payment)
    
    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем текущую информацию об оплате
        payment_result = await session.execute(
            text('SELECT is_paid, amount FROM bookings WHERE id = :booking_id'),
            {"booking_id": booking_id}
        )
        payment_data = payment_result.fetchone()
        
        is_paid = payment_data[0] if payment_data else False
        amount = payment_data[1] if payment_data else 0
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Оплачено" if not is_paid else "❌ Не оплачено",
                    callback_data=f"toggle_payment_{booking_id}"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_{booking_id}")],
        ])
        
        await callback.message.edit_text(
            f"💰 Изменение оплаты заказа #{booking_id}\n\n"
            f"Текущий статус: {'✅ Оплачено' if is_paid else '❌ Не оплачено'}\n"
            f"Сумма: {amount}₽\n\n"
            f"Нажмите кнопку для изменения статуса оплаты:",
            reply_markup=keyboard
        )
        await callback.answer()


@router.callback_query(F.data.startswith("toggle_payment_"))
async def toggle_booking_payment(callback: CallbackQuery, state: FSMContext):
    """Переключить статус оплаты заказа"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
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
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем текущий статус оплаты
        payment_result = await session.execute(
            text('SELECT is_paid FROM bookings WHERE id = :booking_id'),
            {"booking_id": booking_id}
        )
        payment_data = payment_result.fetchone()
        current_is_paid = payment_data[0] if payment_data else False
        
        # Переключаем статус
        new_is_paid = not current_is_paid
        
        await session.execute(
            text('UPDATE bookings SET is_paid = :is_paid WHERE id = :booking_id'),
            {"is_paid": new_is_paid, "booking_id": booking_id}
        )
        await session.commit()
        
        await callback.answer(f"✅ Статус оплаты изменен на: {'Оплачено' if new_is_paid else 'Не оплачено'}")
        
        # Возвращаемся к редактированию оплаты
        callback_copy = callback.model_copy(update={"data": f"edit_payment_{booking_id}"})
        await edit_booking_payment(callback_copy, state)


@router.callback_query(F.data.startswith("edit_datetime_"))
async def edit_booking_datetime(callback: CallbackQuery, state: FSMContext):
    """Изменить дату и время заказа"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
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

    # Сохраняем booking_id в состояние
    await state.update_data(booking_id=booking_id)
    await state.set_state(AdminEditBookingStates.editing_datetime)
    
    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем текущую дату и длительность заказа
        booking_result = await session.execute(
            text('SELECT service_date, duration, service_id FROM bookings WHERE id = :booking_id'),
            {"booking_id": booking_id}
        )
        booking_data = booking_result.fetchone()
        
        if not booking_data:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        current_date = booking_data[0]
        duration = booking_data[1] or 60
        service_id = booking_data[2]

        logger.info(
            f"🟢 [ADMIN] Текущие параметры заказа: booking_id={booking_id}, "
            f"service_date={current_date}, duration={duration}, service_id={service_id}"
        )
        
        # Сохраняем duration и service_id в состояние
        await state.update_data(duration=duration, service_id=service_id)
        
        # Показываем календарь
        today = date.today()
        end_date = today + timedelta(days=60)
        available_dates = await get_available_dates(session, today, end_date, company_id=company_id)
        calendar = generate_calendar(today.year, today.month, available_dates, today)
        
        await callback.message.edit_text(
            f"📅 Изменение даты и времени заказа #{booking_id}\n\n"
            f"Текущая дата: {current_date.strftime('%d.%m.%Y')}\n\n"
            f"Выберите новую дату:",
            reply_markup=calendar
        )
        await callback.answer()


@router.callback_query(F.data.startswith("calendar_date_"), AdminEditBookingStates.editing_datetime)
async def process_datetime_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора даты при изменении даты/времени заказа"""
    try:
        parts = callback.data.split("_")
        year = int(parts[2])
        month = int(parts[3])
        day = int(parts[4])
        selected_date = date(year, month, day)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора даты", show_alert=True)
        return

    logger.info(f"🟢 [ADMIN] Выбрана дата для изменения: {selected_date}")

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Сохраняем выбранную дату
    data = await state.get_data()
    booking_id = data.get("booking_id")
    duration = data.get("duration", 60)
    
    await state.update_data(booking_date=selected_date)
    await state.set_state(AdminEditBookingStates.editing_datetime)

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Генерируем доступные временные слоты
        time_slots = await generate_time_slots(session, selected_date, duration, master_id=None, company_id=company_id)
        logger.info(f"🟢 [ADMIN] Свободные слоты: {len(time_slots)}")

        if not time_slots:
            await callback.message.edit_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет свободного времени.\n\n"
                f"Выберите другую дату."
            )
            # Показываем календарь снова
            today = date.today()
            end_date = today + timedelta(days=60)
            available_dates = await get_available_dates(session, today, end_date, company_id=company_id)
            calendar = generate_calendar(today.year, today.month, available_dates, today)
            await callback.message.edit_text(
                f"📅 Изменение даты и времени заказа #{booking_id}\n\n"
                f"Выберите дату:",
                reply_markup=calendar
            )
            await callback.answer("❌ Нет свободного времени")
            return

        from bot.keyboards.client import get_time_slots_keyboard
        await callback.message.edit_text(
            f"📅 Изменение даты и времени заказа #{booking_id}\n"
            f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
            f"⏰ Выберите время:",
            reply_markup=get_time_slots_keyboard(time_slots)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("time_slot_"), AdminEditBookingStates.editing_datetime)
async def process_datetime_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени при изменении даты/времени заказа"""
    try:
        parts = callback.data.split("_")
        start_time_str = parts[2]
        end_time_str = parts[3]
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора времени", show_alert=True)
        return

    logger.info(f"🟢 [ADMIN] Выбрано время: {start_time} - {end_time}")

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    data = await state.get_data()
    booking_id = data.get("booking_id")
    booking_date = data.get("booking_date")
    
    if not booking_date:
        await callback.answer("❌ Ошибка: дата не выбрана", show_alert=True)
        return

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Вычисляем длительность
        start_datetime = datetime.combine(booking_date, start_time)
        end_datetime = datetime.combine(booking_date, end_time)
        duration = int((end_datetime - start_datetime).total_seconds() / 60)
        
        # Обновляем дату и время заказа
        await session.execute(
            text(
                """
                UPDATE bookings
                SET service_date = :date, time = :time, end_time = :end_time, duration = :duration
                WHERE id = :booking_id
                """
            ),
            {
                "date": booking_date,
                "time": start_time,
                "end_time": end_time,
                "duration": duration,
                "booking_id": booking_id,
            },
        )
        await session.commit()
        
        await callback.message.edit_text(
            f"✅ Дата и время заказа #{booking_id} изменены:\n\n"
            f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )
        await callback.answer("✅ Дата и время изменены")
        
        # Очищаем состояние
        await state.clear()
        
        # Возвращаемся к деталям заказа
        from bot.handlers.admin.bookings import show_booking_details
        callback_copy = callback.model_copy(update={"data": f"booking_{booking_id}"})
        await show_booking_details(callback_copy, state)


@router.callback_query(F.data.startswith("time_"), AdminEditBookingStates.editing_datetime)
async def process_datetime_time_selection_simple(callback: CallbackQuery, state: FSMContext):
    """
    Обработка выбора времени вида time_{hour}_{minute} при изменении даты/времени заказа.
    Используется теми клавиатурами, что отдают только стартовое время.
    """
    try:
        parts = callback.data.split("_")
        hour = int(parts[1])
        minute = int(parts[2])
        start_time = time(hour, minute)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора времени", show_alert=True)
        return

    logger.info(f"🟢 [ADMIN] Выбрано время (simple): {start_time}")

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get("company_id")
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    data = await state.get_data()
    booking_id = data.get("booking_id")
    booking_date = data.get("booking_date")
    duration = data.get("duration", 60)

    if not booking_date:
        await callback.answer("❌ Ошибка: дата не выбрана", show_alert=True)
        return

    # Вычисляем end_time по длительности
    start_dt = datetime.combine(booking_date, start_time)
    end_dt = start_dt + timedelta(minutes=duration)
    end_time = end_dt.time()

    async for session in get_session():
        schema_name = f'tenant_{company_id}'
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))

        await session.execute(
            text(
                """
                UPDATE bookings
                SET service_date = :date, time = :time, end_time = :end_time, duration = :duration
                WHERE id = :booking_id
                """
            ),
            {
                "date": booking_date,
                "time": start_time,
                "end_time": end_time,
                "duration": duration,
                "booking_id": booking_id,
            },
        )
        await session.commit()

        await callback.message.edit_text(
            f"✅ Дата и время заказа #{booking_id} изменены:\n\n"
            f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )
        await callback.answer("✅ Дата и время изменены")

        await state.clear()

        from bot.handlers.admin.bookings import show_booking_details
        callback_copy = callback.model_copy(update={"data": f"booking_{booking_id}"})
        await show_booking_details(callback_copy, state)


@router.callback_query(F.data.startswith("edit_master_"))
async def edit_booking_master(callback: CallbackQuery, state: FSMContext):
    """Изменить мастера заказа"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
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
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        masters = await get_masters(session)
        if not masters:
            await callback.answer("❌ Нет доступных мастеров", show_alert=True)
            return

        await callback.message.edit_text(
            f"👨‍🔧 Изменение мастера заказа #{booking_id}\n\n"
            f"Выберите мастера:",
            reply_markup=get_masters_keyboard(masters, booking_id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("edit_post_"))
async def edit_booking_post(callback: CallbackQuery, state: FSMContext):
    """Изменить пост заказа"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
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
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем текущего мастера
        master_result = await session.execute(
            text('SELECT master_id FROM bookings WHERE id = :booking_id'),
            {"booking_id": booking_id}
        )
        master_data = master_result.fetchone()
        master_id = master_data[0] if master_data else None
        
        posts = await get_posts(session)
        if not posts:
            await callback.answer("❌ Нет доступных постов", show_alert=True)
            return

        await callback.message.edit_text(
            f"🏢 Изменение рабочего места заказа #{booking_id}\n\n"
            f"Выберите рабочее место:",
            reply_markup=get_posts_keyboard(posts, booking_id, master_id or 0)
        )
        await callback.answer()


# ==================== Обработчики создания нового заказа ====================

@router.callback_query(F.data.startswith("admin_client_"))
async def admin_select_client(callback: CallbackQuery, state: FSMContext):
    """Выбор клиента при создании заказа"""
    try:
        client_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
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

    # Сохраняем client_id в состояние
    await state.update_data(client_id=client_id)
    await state.set_state(AdminBookingStates.choosing_service)

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем имя клиента
        client_result = await session.execute(
            text('SELECT full_name, phone FROM clients WHERE id = :client_id'),
            {"client_id": client_id}
        )
        client_data = client_result.fetchone()
        client_name = f"{client_data[0]} ({client_data[1]})" if client_data else f"Клиент #{client_id}"
        
        # Получаем список услуг
        services = await get_services(session, active_only=True, company_id=company_id)
        
        if not services:
            await callback.answer("❌ Нет доступных услуг", show_alert=True)
            return

        from bot.keyboards.client import get_services_keyboard
        # Создаем клавиатуру с префиксом admin_service_
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for service in services:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{service.name} ({service.duration} мин)",
                    callback_data=f"admin_service_{service.id}"
                )
            ])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_booking")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"➕ Создание нового заказа\n\n"
            f"👤 Клиент: {client_name}\n\n"
            f"🛠️ Выберите услугу:",
            reply_markup=keyboard
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_service_"), AdminBookingStates.choosing_service)
async def admin_select_service(callback: CallbackQuery, state: FSMContext):
    """Выбор услуги при создании заказа"""
    try:
        service_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Сохраняем service_id в состояние
    await state.update_data(service_id=service_id)
    await state.set_state(AdminBookingStates.choosing_date)

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем данные услуги
        service_result = await session.execute(
            text('SELECT name, duration, price FROM services WHERE id = :service_id'),
            {"service_id": service_id}
        )
        service_data = service_result.fetchone()
        
        if not service_data:
            await callback.answer("❌ Услуга не найдена", show_alert=True)
            return
        
        service_name = service_data[0]
        service_duration = service_data[1] or 60
        service_price = service_data[2] or 0
        
        # Сохраняем duration в состояние
        await state.update_data(service_duration=service_duration)
        
        # Показываем календарь
        today = date.today()
        end_date = today + timedelta(days=60)
        available_dates = await get_available_dates(session, today, end_date, company_id=company_id)
        calendar = generate_calendar(today.year, today.month, available_dates, today)
        
        await callback.message.edit_text(
            f"➕ Создание нового заказа\n\n"
            f"🛠️ Услуга: {service_name}\n"
            f"⏱️ Длительность: {service_duration} мин\n"
            f"💰 Цена: {service_price}₽\n\n"
            f"📅 Выберите дату:",
            reply_markup=calendar
        )
        await callback.answer()


@router.callback_query(F.data.startswith("calendar_date_"), AdminBookingStates.choosing_date)
async def admin_select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты при создании заказа"""
    try:
        parts = callback.data.split("_")
        year = int(parts[2])
        month = int(parts[3])
        day = int(parts[4])
        selected_date = date(year, month, day)
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка выбора даты", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Сохраняем дату в состояние
    data = await state.get_data()
    service_duration = data.get("service_duration", 60)
    
    await state.update_data(booking_date=selected_date)
    await state.set_state(AdminBookingStates.choosing_time)

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Генерируем доступные временные слоты
        time_slots = await generate_time_slots(session, selected_date, service_duration, master_id=None, company_id=company_id)

        if not time_slots:
            await callback.message.edit_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет свободного времени.\n\n"
                f"Выберите другую дату."
            )
            # Показываем календарь снова
            today = date.today()
            end_date = today + timedelta(days=60)
            available_dates = await get_available_dates(session, today, end_date, company_id=company_id)
            calendar = generate_calendar(today.year, today.month, available_dates, today)
            data = await state.get_data()
            service_id = data.get("service_id")
            service_result = await session.execute(
                text('SELECT name, duration, price FROM services WHERE id = :service_id'),
                {"service_id": service_id}
            )
            service_data = service_result.fetchone()
            service_name = service_data[0] if service_data else "Услуга"
            service_duration = service_data[1] if service_data else 60
            
            await callback.message.edit_text(
                f"➕ Создание нового заказа\n\n"
                f"🛠️ Услуга: {service_name}\n"
                f"⏱️ Длительность: {service_duration} мин\n\n"
                f"📅 Выберите дату:",
                reply_markup=calendar
            )
            await callback.answer("❌ Нет свободного времени")
            return

        from bot.keyboards.client import get_time_slots_keyboard
        data = await state.get_data()
        service_id = data.get("service_id")
        service_result = await session.execute(
            text('SELECT name FROM services WHERE id = :service_id'),
            {"service_id": service_id}
        )
        service_data = service_result.fetchone()
        service_name = service_data[0] if service_data else "Услуга"
        
        await callback.message.edit_text(
            f"➕ Создание нового заказа\n"
            f"🛠️ Услуга: {service_name}\n"
            f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n\n"
            f"⏰ Выберите время:",
            reply_markup=get_time_slots_keyboard(time_slots)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("time_"), AdminBookingStates.choosing_time)
async def admin_select_time(callback: CallbackQuery, state: FSMContext):
    """Выбор времени при создании заказа"""
    try:
        parts = callback.data.split("_")
        # Формат: time_{hour}_{minute}
        hour = int(parts[1])
        minute = int(parts[2])
        start_time = time(hour, minute)
        
        # Получаем длительность услуги для вычисления end_time
        data = await state.get_data()
        service_duration = data.get("service_duration", 60)
        
        # Вычисляем end_time
        from datetime import datetime, timedelta
        start_datetime = datetime.combine(date.today(), start_time)
        end_datetime = start_datetime + timedelta(minutes=service_duration)
        end_time = end_datetime.time()
    except (ValueError, IndexError) as e:
        logger.error(f"❌ Ошибка парсинга времени: {e}, callback_data: {callback.data}")
        await callback.answer("❌ Ошибка выбора времени", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Сохраняем время в состояние
    data = await state.get_data()
    booking_date = data.get("booking_date")
    
    if not booking_date:
        await callback.answer("❌ Ошибка: дата не выбрана", show_alert=True)
        return

    await state.update_data(booking_time=start_time, end_time=end_time)
    await state.set_state(AdminBookingStates.choosing_master)

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем список мастеров
        try:
            logger.info(f"🔍 [HANDLER] Получаем список мастеров для company_id={company_id}")
            masters = await get_masters(session, company_id=company_id)
            logger.info(f"✅ [HANDLER] Получено мастеров: {len(masters) if masters else 0}")
        except Exception as e:
            logger.error(f"❌ [HANDLER] Ошибка получения мастеров: {e}", exc_info=True)
            await callback.answer("❌ Ошибка при получении списка мастеров", show_alert=True)
            return
        
        # Создаем клавиатуру с префиксом assign_master_0_ для нового заказа
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        
        if not masters:
            # Если нет мастеров, показываем ошибку
            logger.warning(f"⚠️ [admin_select_time] Нет доступных мастеров для company_id={company_id}")
            await callback.answer("❌ Нет доступных мастеров. Пожалуйста, добавьте мастеров в систему.", show_alert=True)
            await state.clear()
            return
        
        # Если есть мастера, показываем их выбор
        # Используем другой формат для новых заказов, чтобы они не попадали под фильтр assign_master_*
        for master in masters:
            buttons.append([
                InlineKeyboardButton(
                    text=f"👨‍🔧 {master.full_name}",
                    callback_data=f"new_master_{master.id}"
                )
            ])
        buttons.append([
            InlineKeyboardButton(text="🤖 Автоматически", callback_data="new_master_auto")
        ])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_booking")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(
            f"➕ Создание нового заказа\n"
            f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n\n"
            f"👨‍🔧 Выберите мастера:",
            reply_markup=keyboard
        )
        await callback.answer()


@router.callback_query(F.data.startswith("new_master_"), AdminBookingStates.choosing_master)
async def admin_select_master(callback: CallbackQuery, state: FSMContext):
    """Выбор мастера при создании заказа"""
    logger.info(f"🔵 [admin_select_master] НАЧАЛО: callback_data='{callback.data}', state={await state.get_state()}")
    
    try:
        parts = callback.data.split("_")
        
        if parts[2] == "auto":
            master_id = None
        else:
            master_id = int(parts[2])
        logger.info(f"🔵 [admin_select_master] Обрабатываем выбор мастера master_id={master_id}")
    except (ValueError, IndexError) as e:
        logger.error(f"❌ [admin_select_master] Ошибка парсинга: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем, что все необходимые данные уже есть в состоянии
    data = await state.get_data()
    booking_date = data.get("booking_date")
    booking_time = data.get("booking_time")
    end_time = data.get("end_time")
    client_id = data.get("client_id")
    service_id = data.get("service_id")
    
    logger.info(f"🔵 [admin_select_master] Проверка данных: booking_date={booking_date}, booking_time={booking_time}, end_time={end_time}, client_id={client_id}, service_id={service_id}")
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Если время не выбрано, не продолжаем
    if not booking_time or not end_time:
        logger.error(f"❌ [admin_select_master] Время не выбрано! booking_time={booking_time}, end_time={end_time}")
        await callback.answer("❌ Ошибка: время не выбрано. Пожалуйста, сначала выберите время записи.", show_alert=True)
        return
    
    if not booking_date:
        logger.error(f"❌ [admin_select_master] Дата не выбрана! booking_date={booking_date}")
        await callback.answer("❌ Ошибка: дата не выбрана. Пожалуйста, сначала выберите дату записи.", show_alert=True)
        return

    # Сохраняем master_id в состояние
    await state.update_data(master_id=master_id)
    await state.set_state(AdminBookingStates.choosing_post)
    logger.info(f"🔵 [admin_select_master] master_id={master_id} сохранен, переходим к выбору поста")

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем список постов
        posts = await get_posts(session, company_id=company_id)
        logger.info(f"🔵 [admin_select_master] Получено постов: {len(posts) if posts else 0}")
        
        if not posts:
            # Если нет постов, создаем заказ сразу (но только если все данные есть!)
            logger.info(f"🔵 [admin_select_master] Постов нет, создаем заказ сразу")
            await create_admin_booking_final(callback, state, session, company_id)
            return

        # Создаем клавиатуру с префиксом assign_post_0_ для нового заказа
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for post in posts:
            buttons.append([
                InlineKeyboardButton(
                    text=f"🏢 {post.name}",
                    callback_data=f"assign_post_0_{master_id or 0}_{post.id}"
                )
            ])
        buttons.append([
            InlineKeyboardButton(text="🤖 Автоматически", callback_data=f"assign_post_0_{master_id or 0}_auto")
        ])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_booking")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        logger.info(f"🔵 [admin_select_master] Показываем выбор поста")
        
        await callback.message.edit_text(
            f"➕ Создание нового заказа\n"
            f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {booking_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n\n"
            f"🏢 Выберите рабочее место:",
            reply_markup=keyboard
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_post_"), AdminBookingStates.choosing_post)
async def admin_select_post(callback: CallbackQuery, state: FSMContext):
    """Выбор поста при создании заказа"""
    logger.info(f"🔵 [admin_select_post] НАЧАЛО: callback_data='{callback.data}', user={callback.from_user.id}")
    
    try:
        parts = callback.data.split("_")
        booking_id_from_callback = parts[2]  # Может быть 0 для нового заказа
        master_id_from_callback = parts[3]  # Может быть 0
        if parts[4] == "auto":
            post_id = None
        else:
            post_id = int(parts[4])
        logger.info(f"🔵 [admin_select_post] Парсинг: booking_id={booking_id_from_callback}, master_id={master_id_from_callback}, post_id={post_id}")
    except (ValueError, IndexError) as e:
        logger.error(f"❌ [admin_select_post] Ошибка парсинга: {e}, callback_data='{callback.data}'")
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    # Проверяем, что это создание нового заказа (booking_id = 0)
    if booking_id_from_callback != "0":
        logger.debug(f"🔵 [admin_select_post] Пропускаем: booking_id={booking_id_from_callback} != 0")
        return  # Это не наш обработчик, пропускаем

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        logger.error(f"❌ [admin_select_post] company_id не найден")
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    logger.info(f"🔵 [admin_select_post] Сохраняем post_id={post_id} в состояние")
    # Сохраняем post_id в состояние
    await state.update_data(post_id=post_id)

    logger.info(f"🔵 [admin_select_post] Начинаем создание заказа")
    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Создаем заказ
        await create_admin_booking_final(callback, state, session, company_id)


async def create_admin_booking_final(callback: CallbackQuery, state: FSMContext, session, company_id: int):
    """Финальное создание заказа администратором"""
    logger.info(f"🔵 [create_admin_booking_final] НАЧАЛО: создание заказа")
    
    data = await state.get_data()
    client_id = data.get("client_id")
    service_id = data.get("service_id")
    booking_date = data.get("booking_date")
    booking_time = data.get("booking_time")
    end_time = data.get("end_time")
    master_id = data.get("master_id")
    post_id = data.get("post_id")
    service_duration = data.get("service_duration", 60)
    
    logger.info(f"🔵 [create_admin_booking_final] Данные: client_id={client_id}, service_id={service_id}, booking_date={booking_date}, booking_time={booking_time}, end_time={end_time}, master_id={master_id}, post_id={post_id}")
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Все обязательные данные должны быть заполнены
    if not all([client_id, service_id, booking_date, booking_time, end_time]):
        logger.error(f"❌ [create_admin_booking_final] Не все данные заполнены: client_id={client_id}, service_id={service_id}, booking_date={booking_date}, booking_time={booking_time}, end_time={end_time}")
        await callback.answer("❌ Ошибка: не все данные заполнены. Проверьте, что выбраны клиент, услуга, дата и время.", show_alert=True)
        await state.clear()
        return
    
    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: Время должно быть выбрано
    if not booking_time or not end_time:
        logger.error(f"❌ [create_admin_booking_final] Время не выбрано: booking_time={booking_time}, end_time={end_time}")
        await callback.answer("❌ Ошибка: время не выбрано. Пожалуйста, выберите время записи.", show_alert=True)
        await state.clear()
        return
    
    try:
        # Временно не ставим created_by, чтобы избежать FK ошибки, если админ не занесён в users
        created_by_user_id = None
        
        # Создаем заказ
        booking = await create_booking(
            session=session,
            client_id=client_id,
            service_id=service_id,
            booking_date=booking_date,
            booking_time=booking_time,
            duration=service_duration,
            end_time=end_time,
            created_by=created_by_user_id,
            company_id=company_id
        )
        
        # Авто-назначение мастера при выборе "Автоматически"
        if master_id is None:
            from bot.database.crud import get_masters, get_master_bookings_by_date
            masters = await get_masters(session, company_id=company_id)
            selected_master = None
            min_bookings = float("inf")
            for m in masters:
                cnt = len(await get_master_bookings_by_date(session, m.id, booking_date))
                if cnt < min_bookings:
                    min_bookings = cnt
                    selected_master = m
            if selected_master:
                master_id = selected_master.id
        
        # Авто-назначение поста при выборе "Автоматически"
        if post_id is None:
            posts = await get_posts(session, company_id=company_id)
            if posts:
                post_id = posts[0].id
        
        # Обновляем мастера и пост если указаны
        if master_id or post_id:
            # После commit search_path мог сброситься - выставляем перед апдейтом
            schema_name = f"tenant_{company_id}"
            await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
            await update_booking_status(
                session=session,
                booking_id=booking.id,
                status="confirmed",  # Созданные админом заказы сразу подтверждены
                master_id=master_id,
                post_id=post_id,
                company_id=company_id
            )
        
        # Получаем данные для отображения
        booking_result = await session.execute(
            text('SELECT booking_number FROM bookings WHERE id = :booking_id'),
            {"booking_id": booking.id}
        )
        booking_data = booking_result.fetchone()
        booking_number = booking_data[0] if booking_data else f"#{booking.id}"
        
        await callback.message.edit_text(
            f"✅ Заказ {booking_number} успешно создан!\n\n"
            f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {booking_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )
        await callback.answer("✅ Заказ создан")
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания заказа: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании заказа", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "admin_create_new_client")
async def admin_start_create_client(callback: CallbackQuery, state: FSMContext):
    """Начать создание нового клиента"""
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    # Переходим в состояние ввода ФИО
    await state.set_state(AdminBookingStates.creating_client_full_name)
    
    await callback.message.edit_text(
        "➕ Создание нового клиента\n\n"
        "👤 Введите ФИО клиента:"
    )
    await callback.answer()


@router.message(AdminBookingStates.creating_client_full_name)
async def admin_create_client_full_name(message: Message, state: FSMContext):
    """Обработка ввода ФИО нового клиента"""
    full_name = message.text.strip()
    
    if not full_name or len(full_name) < 2:
        await message.answer("❌ ФИО должно содержать минимум 2 символа. Попробуйте еще раз:")
        return
    
    # Сохраняем ФИО в состояние
    await state.update_data(new_client_full_name=full_name)
    await state.set_state(AdminBookingStates.creating_client_phone)
    
    await message.answer(
        f"✅ ФИО: {full_name}\n\n"
        f"📞 Введите номер телефона клиента (например: +79991234567 или 89991234567):"
    )


@router.message(AdminBookingStates.creating_client_phone)
async def admin_create_client_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона нового клиента и создание клиента"""
    phone = message.text.strip()
    
    # Простая валидация телефона
    import re
    phone_pattern = r'^(\+7|8)?[\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})$'
    phone_clean_input = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if not re.match(phone_pattern, phone_clean_input):
        await message.answer("❌ Неверный формат телефона. Введите номер в формате +79991234567 или 89991234567:")
        return
    
    # Нормализуем телефон (убираем пробелы, дефисы, скобки)
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    if phone_clean.startswith('8'):
        phone_clean = '+7' + phone_clean[1:]
    elif not phone_clean.startswith('+7'):
        phone_clean = '+7' + phone_clean
    
    # Получаем company_id из диспетчера
    try:
        dp = getattr(message.bot, '_dispatcher', None)
        if dp:
            company_id = dp.get('company_id')
        else:
            await message.answer("❌ Ошибка конфигурации бота")
            await state.clear()
            return
    except Exception as e:
        logger.error(f"❌ Ошибка получения company_id: {e}")
        await message.answer("❌ Ошибка конфигурации бота")
        await state.clear()
        return
    
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота")
        await state.clear()
        return
    
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота")
        await state.clear()
        return
    
    data = await state.get_data()
    full_name = data.get("new_client_full_name")
    
    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Проверяем, существует ли уже пользователь с таким телефоном
        user_result = await session.execute(
            text('SELECT id FROM users WHERE phone = :phone'),
            {"phone": phone_clean}
        )
        existing_user = user_result.fetchone()
        
        if existing_user:
            # Пользователь уже существует, проверяем есть ли клиент
            user_id = existing_user[0]
            client_result = await session.execute(
                text('SELECT id FROM clients WHERE user_id = :user_id'),
                {"user_id": user_id}
            )
            existing_client = client_result.fetchone()
            
            if existing_client:
                # Клиент уже существует, используем его
                client_id = existing_client[0]
                await message.answer(
                    f"✅ Клиент с таким телефоном уже существует!\n\n"
                    f"👤 {full_name}\n"
                    f"📞 {phone_clean}\n\n"
                    f"Продолжаем создание заказа..."
                )
            else:
                # Создаем клиента для существующего пользователя
                from bot.database.crud import create_client
                client = await create_client(session, user_id, full_name, phone_clean, company_id=company_id)
                client_id = client.id
                await message.answer(
                    f"✅ Клиент создан!\n\n"
                    f"👤 {full_name}\n"
                    f"📞 {phone_clean}\n\n"
                    f"Продолжаем создание заказа..."
                )
        else:
            # Создаем нового пользователя и клиента
            from bot.database.crud import create_user, create_client
            from datetime import datetime
            
            # Создаем пользователя
            user_result = await session.execute(
                text('''
                    INSERT INTO users (username, email, password_hash, full_name, phone, role, telegram_id, is_active, created_at, updated_at)
                    VALUES (:username, :email, :password_hash, :full_name, :phone, :role, :telegram_id, :is_active, :created_at, :updated_at)
                    RETURNING id
                '''),
                {
                    "username": phone_clean.replace('+', '').replace(' ', ''),
                    "email": f"{phone_clean.replace('+', '').replace(' ', '')}@temp.local",
                    "password_hash": "",  # Пароль не нужен для клиента
                    "full_name": full_name,
                    "phone": phone_clean,
                    "role": "client",
                    "telegram_id": None,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            )
            user_id = user_result.fetchone()[0]
            await session.commit()
            
            # Создаем клиента
            client = await create_client(session, user_id, full_name, phone_clean, company_id=company_id)
            client_id = client.id
            await message.answer(
                f"✅ Клиент создан!\n\n"
                f"👤 {full_name}\n"
                f"📞 {phone_clean}\n\n"
                f"Продолжаем создание заказа..."
            )
        
        # Сохраняем client_id в состояние и переходим к выбору услуги
        await state.update_data(client_id=client_id)
        await state.set_state(AdminBookingStates.choosing_service)
        
        # Получаем список услуг
        services = await get_services(session, active_only=True, company_id=company_id)
        
        if not services:
            await message.answer("❌ Нет доступных услуг")
            await state.clear()
            return
        
        # Создаем клавиатуру с услугами
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        for service in services:
            buttons.append([
                InlineKeyboardButton(
                    text=f"{service.name} ({service.duration} мин)",
                    callback_data=f"admin_service_{service.id}"
                )
            ])
        buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel_booking")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(
            f"➕ Создание нового заказа\n\n"
            f"👤 Клиент: {full_name} ({phone_clean})\n\n"
            f"🛠️ Выберите услугу:",
            reply_markup=keyboard
        )


@router.callback_query(F.data == "admin_cancel_booking")
async def admin_cancel_booking_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания заказа"""
    await state.clear()
    await callback.message.edit_text("❌ Создание заказа отменено")
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_month_"), AdminEditBookingStates.editing_datetime)
async def edit_datetime_change_month(callback: CallbackQuery, state: FSMContext):
    """Смена месяца в календаре при изменении даты/времени заказа"""
    try:
        parts = callback.data.split("_")
        year = int(parts[2])
        month = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем доступные даты
        today = date.today()
        start_date = date(year, month, 1)
        end_date = date(year, month, 28) + timedelta(days=4)  # До конца месяца
        available_dates = await get_available_dates(session, start_date, end_date, company_id=company_id)

        calendar = generate_calendar(year, month, available_dates, today)

        # Получаем данные заказа из состояния
        data = await state.get_data()
        booking_id = data.get("booking_id")
        
        if booking_id:
            # Получаем текущую дату заказа
            booking_result = await session.execute(
                text('SELECT service_date FROM bookings WHERE id = :booking_id'),
                {"booking_id": booking_id}
            )
            booking_data = booking_result.fetchone()
            current_date_str = booking_data[0].strftime('%d.%m.%Y') if booking_data else ""
            
            await callback.message.edit_text(
                f"📅 Изменение даты и времени заказа #{booking_id}\n\n"
                f"Текущая дата: {current_date_str}\n\n"
                f"Выберите новую дату:",
                reply_markup=calendar
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            "📅 Выберите дату:",
            reply_markup=calendar
        )
        await callback.answer()




@router.callback_query(F.data.startswith("calendar_month_"), AdminBookingStates.choosing_date)
async def admin_change_calendar_month(callback: CallbackQuery, state: FSMContext):
    """Смена месяца в календаре при создании заказа"""
    try:
        parts = callback.data.split("_")
        year = int(parts[2])
        month = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    async for session in get_session():
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем доступные даты (проверяет занятость)
        today = date.today()
        start_date = date(year, month, 1)
        end_date = date(year, month, 28) + timedelta(days=4)  # До конца месяца
        available_dates = await get_available_dates(session, start_date, end_date, company_id=company_id)

        calendar = generate_calendar(year, month, available_dates, today)

        # Получаем данные услуги из состояния
        data = await state.get_data()
        service_id = data.get("service_id")
        
        if service_id:
            service_result = await session.execute(
                text('SELECT name, duration FROM services WHERE id = :service_id'),
                {"service_id": service_id}
            )
            service_data = service_result.fetchone()
            if service_data:
                service_name = service_data[0]
                service_duration = service_data[1] or 60
                await callback.message.edit_text(
                    f"➕ Создание нового заказа\n\n"
                    f"🛠️ Услуга: {service_name}\n"
                    f"⏱️ Длительность: {service_duration} мин\n\n"
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

