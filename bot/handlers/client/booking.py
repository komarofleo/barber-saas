"""Обработчик создания записи"""
import logging
from datetime import date, time, timedelta, datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from bot.database.connection import get_session
from bot.database.crud import (
    get_services, get_service_by_id, get_client_by_user_id,
    create_booking, get_user_by_telegram_id, get_available_dates
)
from bot.keyboards.client import get_client_main_keyboard, get_services_keyboard, get_cancel_keyboard
from bot.states.client_states import BookingStates
from bot.utils.calendar import generate_calendar
from shared.database.models import User, Booking

logger = logging.getLogger(__name__)
router = Router()


async def notify_admins_about_new_booking(bot: Bot, booking: Booking, service):
    """Отправить уведомление администраторам о новой записи"""
    try:
        async for session in get_session():
            # Загружаем связанные данные
            from sqlalchemy.orm import selectinload
            result = await session.execute(
                select(Booking)
                .where(Booking.id == booking.id)
                .options(
                    selectinload(Booking.client),
                    selectinload(Booking.service)
                )
            )
            booking_loaded = result.scalar_one_or_none()
            if not booking_loaded:
                logger.error(f"Запись {booking.id} не найдена для уведомления")
                return
            
            # Получаем всех администраторов с Telegram ID
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
                logger.warning("Не найдено администраторов для уведомления")
                return
            
            # Формируем сообщение
            date_str = booking_loaded.date.strftime("%d.%m.%Y")
            time_str = booking_loaded.time.strftime("%H:%M")
            client_name = booking_loaded.client.full_name if booking_loaded.client else "Неизвестно"
            client_phone = booking_loaded.client.phone if booking_loaded.client else "Не указан"
            service_name = service.name if service else (booking_loaded.service.name if booking_loaded.service else "Не указана")
            
            # Получаем информацию об автомобиле
            car_info = ""
            if booking_loaded.client:
                if booking_loaded.client.car_brand:
                    car_info = f"\n   🚗 {booking_loaded.client.car_brand}"
                    if booking_loaded.client.car_model:
                        car_info += f" {booking_loaded.client.car_model}"
                    if booking_loaded.client.car_number:
                        car_info += f" ({booking_loaded.client.car_number})"
                elif booking_loaded.comment and "Марка автомобиля:" in booking_loaded.comment:
                    # Извлекаем марку из комментария
                    car_brand = booking_loaded.comment.replace("Марка автомобиля:", "").strip()
                    if car_brand:
                        car_info = f"\n   🚗 {car_brand}"
            
            text = f"🔔 Новая запись!\n\n"
            text += f"📋 {booking_loaded.booking_number}\n"
            text += f"   👤 {client_name}\n"
            text += f"   📞 {client_phone}{car_info}\n"
            text += f"   📅 {date_str} в {time_str}\n"
            text += f"   🛠️ {service_name}\n"
            
            # Отправляем уведомление всем администраторам
            for admin in admins:
                try:
                    await bot.send_message(
                        chat_id=admin.telegram_id,
                        text=text
                    )
                    logger.info(f"Уведомление отправлено администратору {admin.id} (telegram_id: {admin.telegram_id})")
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления администратору {admin.id}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Ошибка в notify_admins_about_new_booking: {e}", exc_info=True)


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    """Начать процесс записи"""
    # Проверяем подписку компании
    from bot.handlers.booking_subscription_check import check_subscription_before_booking
    can_book = await check_subscription_before_booking(message, state)
    if not can_book:
        # Проверка уже завершена в check_subscription_before_booking
        return
    
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        client = await get_client_by_user_id(session, user.id)
        if not client:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        # Получаем список услуг
        services = await get_services(session, active_only=True)
        if not services:
            await message.answer("❌ Нет доступных услуг. Обратитесь к администратору.")
            return

        await state.set_state(BookingStates.choosing_service)
        await message.answer(
            "🛠️ Выберите услугу:",
            reply_markup=get_services_keyboard(services)
        )


@router.callback_query(F.data.startswith("service_"))
async def process_service(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора услуги - показываем календарь"""
    logger.info(f"Получен callback: {callback.data}")
    try:
        service_id = int(callback.data.split("_")[1])
        logger.info(f"Выбрана услуга с ID: {service_id}")
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга service_id: {e}")
        await callback.answer("❌ Ошибка выбора услуги", show_alert=True)
        return
    
    async for session in get_session():
        try:
            service = await get_service_by_id(session, service_id)
            if not service:
                await callback.answer("❌ Услуга не найдена", show_alert=True)
                return

            # Сохраняем выбранную услугу в состояние
            await state.update_data(service_id=service_id, service_duration=service.duration)
            await state.set_state(BookingStates.choosing_date)

            # Получаем доступные даты (на 2 месяца вперед)
            today = date.today()
            end_date = today + timedelta(days=60)
            available_dates = await get_available_dates(session, today, end_date)

            # Показываем календарь текущего месяца
            calendar = generate_calendar(
                today.year,
                today.month,
                available_dates,
                today
            )

            await callback.message.edit_text(
                f"🛠️ Услуга: {service.name}\n"
                f"⏱️ Длительность: {service.duration} мин\n\n"
                f"📅 Выберите дату:",
                reply_markup=calendar
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка при выборе услуги: {e}", exc_info=True)
            await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data.startswith("time_"), BookingStates.choosing_time)
async def process_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени - переходим к вводу марки автомобиля"""
    try:
        parts = callback.data.split("_")
        hour = int(parts[1])
        minute = int(parts[2])
        selected_time = time(hour, minute)
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга времени: {e}")
        await callback.answer("❌ Ошибка выбора времени", show_alert=True)
        return

    # Сохраняем выбранное время
    await state.update_data(booking_time=selected_time)
    await state.set_state(BookingStates.adding_car_brand)
    
    # Получаем данные из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    booking_date = data.get("booking_date")

    if not service_id or not booking_date:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    async for session in get_session():
        try:
            service = await get_service_by_id(session, service_id)
            if not service:
                await callback.answer("❌ Услуга не найдена", show_alert=True)
                return

            # Показываем запрос на ввод марки автомобиля (необязательно)
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_car_brand")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
            ])
            
            await callback.message.edit_text(
                f"🛠️ Услуга: {service.name}\n"
                f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                f"⏰ Время: {selected_time.strftime('%H:%M')}\n\n"
                f"🚗 Укажите марку автомобиля (необязательно):\n\n"
                f"Например: Toyota, BMW, Mercedes и т.д.\n"
                f"Или нажмите 'Пропустить'",
                reply_markup=keyboard
            )
            await callback.answer()
        except Exception as e:
            logger.error(f"Ошибка при обработке времени: {e}", exc_info=True)
            await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "skip_car_brand", BookingStates.adding_car_brand)
async def skip_car_brand(callback: CallbackQuery, state: FSMContext):
    """Пропустить ввод марки автомобиля"""
    await state.update_data(car_brand=None)
    await finalize_booking(callback, state)


@router.message(BookingStates.adding_car_brand)
async def process_car_brand(message: Message, state: FSMContext):
    """Обработка ввода марки автомобиля"""
    # Проверяем, не введена ли уже марка
    data = await state.get_data()
    if data.get("car_brand") is not None:
        await message.answer("✅ Марка автомобиля уже введена. Запись создается, пожалуйста, подождите...")
        return
    
    # Игнорируем известные команды из клавиатуры
    known_commands = ["📅 Записаться", "📋 Мои записи", "👤 Профиль", "ℹ️ О нас", "❌ Отмена"]
    if message.text and message.text.strip() in known_commands:
        await message.answer("⚠️ Пожалуйста, введите марку автомобиля текстом или нажмите 'Пропустить' в сообщении выше.")
        return
    
    # Получаем и очищаем марку от пробелов
    car_brand = message.text.strip() if message.text else None
    
    # Если после очистки осталась пустая строка, считаем что марка не указана
    if car_brand == "":
        car_brand = None
    
    if car_brand and len(car_brand) > 100:
        await message.answer("❌ Марка автомобиля слишком длинная (максимум 100 символов). Попробуйте снова:")
        return
    
    # Сохраняем марку
    await state.update_data(car_brand=car_brand)
    logger.info(f"Марка автомобиля сохранена в state: {car_brand}")
    
    # Немедленно отправляем подтверждение
    if car_brand:
        confirmation_msg = f"✅ Марка автомобиля введена: {car_brand}\n\n⏳ Создаю запись..."
    else:
        confirmation_msg = "✅ Марка автомобиля пропущена\n\n⏳ Создаю запись..."
    sent_message = await message.answer(confirmation_msg)
    
    # Переходим к финализации заявки
    from aiogram.types import CallbackQuery
    class FakeCallback:
        def __init__(self, message, sent_message):
            self.message = sent_message  # Используем отправленное сообщение для редактирования
            self.bot = message.bot
            self.from_user = message.from_user
            
        async def answer(self, *args, **kwargs):
            pass
    
    fake_callback = FakeCallback(message, sent_message)
    await finalize_booking(fake_callback, state)


async def finalize_booking(callback, state: FSMContext):
    """Финальное создание заявки"""
    # Получаем данные из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    service_duration = data.get("service_duration", 60)
    booking_date = data.get("booking_date")
    booking_time = data.get("booking_time")
    car_brand = data.get("car_brand")

    if not service_id or not booking_date or not booking_time:
        if hasattr(callback, 'answer'):
            await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    async for session in get_session():
        try:
            service = await get_service_by_id(session, service_id)
            if not service:
                if hasattr(callback, 'answer'):
                    await callback.answer("❌ Услуга не найдена", show_alert=True)
                return

            # Вычисляем время окончания
            end_time = (datetime.combine(date.min, booking_time) + timedelta(minutes=service_duration)).time()

            user = await get_user_by_telegram_id(session, callback.from_user.id)
            if not user:
                if hasattr(callback, 'answer'):
                    await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

            client = await get_client_by_user_id(session, user.id)
            if not client:
                if hasattr(callback, 'answer'):
                    await callback.answer("❌ Клиент не найден. Пройдите регистрацию через /start", show_alert=True)
                return

            # Обновляем марку автомобиля в профиле клиента, если указана
            if car_brand and car_brand.strip():
                from bot.database.crud import update_client_car_brand
                updated_client = await update_client_car_brand(session, client.id, car_brand.strip())
                if updated_client:
                    logger.info(f"Марка автомобиля обновлена в профиле клиента: {car_brand.strip()}")
                    # Обновляем объект client для дальнейшего использования
                    client = updated_client
            
            # Формируем комментарий с маркой автомобиля, если указана (для обратной совместимости)
            comment = None
            if car_brand and car_brand.strip():
                comment = f"Марка автомобиля: {car_brand.strip()}"
                logger.info(f"Создание заявки с маркой автомобиля: {car_brand}")
            else:
                logger.info(f"Создание заявки без марки автомобиля. car_brand={car_brand}")

            # Создаем запись
            booking = await create_booking(
                session,
                client_id=client.id,
                service_id=service_id,
                booking_date=booking_date,
                booking_time=booking_time,
                duration=service.duration,
                end_time=end_time,
                comment=comment,
                created_by=user.id,
            )
            logger.info(f"Заявка создана: ID={booking.id}, booking_number={booking.booking_number}, comment={comment}")

            # Отправляем уведомление администраторам о новой записи
            try:
                await notify_admins_about_new_booking(callback.bot, booking, service)
                logger.info(f"Уведомление администраторам отправлено для записи {booking.id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления администраторам: {e}", exc_info=True)
                # Пытаемся через Celery
                try:
                    import sys
                    import os
                    web_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web', 'backend')
                    if web_path not in sys.path:
                        sys.path.insert(0, web_path)
                    from app.tasks.notifications import notify_admin_new_bookings_task
                    notify_admin_new_bookings_task.delay()
                    logger.info(f"Запущена Celery задача уведомления администраторов о новой записи {booking.id}")
                except Exception as e2:
                    logger.error(f"Ошибка запуска Celery задачи: {e2}", exc_info=True)

            # Отправляем подтверждение пользователю
            car_info = f"\n🚗 Авто: {car_brand}" if car_brand else ""
            confirmation_text = (
                f"✅ Запись создана!\n\n"
                f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
                f"⏰ Время: {booking.time.strftime('%H:%M')}\n"
                f"🛠️ Услуга: {service.name}\n"
                f"💰 Цена: {service.price}₽{car_info}\n\n"
                f"Номер записи: {booking.booking_number}\n\n"
                f"Ожидайте подтверждения администратора."
            )
            
            if hasattr(callback, 'message') and hasattr(callback.message, 'edit_text'):
                await callback.message.edit_text(confirmation_text)
            else:
                await callback.bot.send_message(
                    chat_id=callback.from_user.id,
                    text=confirmation_text
                )
            
            if hasattr(callback, 'answer'):
                await callback.answer("✅ Запись создана!")
            await state.clear()
        except Exception as e:
            logger.error(f"Ошибка при создании записи: {e}", exc_info=True)
            if hasattr(callback, 'answer'):
                await callback.answer("❌ Произошла ошибка. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "cancel")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    """Отмена создания записи"""
    await state.clear()
    await callback.message.edit_text("❌ Создание записи отменено")
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_attendance_"))
async def confirm_attendance(callback: CallbackQuery):
    """Подтвердить явку на запись"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    async for session in get_session():
        from bot.database.crud import get_booking_by_id, get_user_by_telegram_id
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        booking = await get_booking_by_id(session, booking_id)
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        # Проверяем, что это запись этого клиента
        if booking.client.user_id != user.id:
            await callback.answer("❌ Это не ваша запись", show_alert=True)
            return
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"✅ Явка подтверждена!\n\n"
            f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
            f"Ждем вас в салоне красоты!"
        )
        await callback.answer("✅ Явка подтверждена")

