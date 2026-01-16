"""Обработчик создания записи"""
import logging
from typing import Optional
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


def get_company_id_from_message(message: Message) -> Optional[int]:
    """Получить company_id из контекста диспетчера через message"""
    try:
        # В aiogram 3.x диспетчер доступен через message.bot.session
        # Но проще использовать middleware data
        return None  # Будет получать через middleware
    except:
        pass
    return None


async def notify_admins_about_new_booking(bot: Bot, booking: Booking, service):
    """Отправить уведомление администраторам о новой записи
    
    Args:
        bot: Экземпляр Telegram бота
        booking: Объект записи
        service: Объект услуги
    
    Логирует:
        - company_id, booking_id на каждом этапе
        - Список найденных админов с их telegram_id
        - Результат отправки каждому админу
        - Причины ошибок при отправке
    """
    import logging
    from sqlalchemy import text
    from bot.database.connection import get_session
    
    logger = logging.getLogger(__name__)
    
    logger.info(f"📤 [NOTIFY_ADMIN] === НАЧАЛО ОТПРАВКИ УВЕДОМЛЕНИЯ АДМИНАМ ===")
    logger.info(f"📤 [NOTIFY_ADMIN] booking_id={booking.id if booking else None}, booking_number={booking.booking_number if booking else None}")
    
    try:
        # Получаем company_id из booking (если есть) или из токена бота
        company_id = None
        try:
            from bot.database.connection import async_session_maker
            bot_token = bot.token
            logger.info(f"📤 [NOTIFY_ADMIN] Получаем company_id для токена: {bot_token[:10]}...")
            async with async_session_maker() as temp_session:
                result = await temp_session.execute(
                    text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                    {"token": bot_token}
                )
                row = result.fetchone()
                if row:
                    company_id = row[0]
                    logger.info(f"✅ [NOTIFY_ADMIN] Найден company_id: {company_id}")
                else:
                    logger.error(f"❌ [NOTIFY_ADMIN] Компания с таким токеном не найдена!")
        except Exception as e:
            logger.error(f"❌ [NOTIFY_ADMIN] Ошибка получения company_id: {e}", exc_info=True)
        
        if not company_id:
            logger.error(f"❌ [NOTIFY_ADMIN] === ОШИБКА: НЕ УДАЛОСЬ ПОЛУЧИТЬ company_id ===")
            logger.error(f"❌ [NOTIFY_ADMIN] booking_id={booking.id if booking else None}")
            return
        
        async for session in get_session():
            schema_name = f"tenant_{company_id}"
            # Устанавливаем search_path для tenant схемы
            await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
            logger.info(f"✅ [NOTIFY_ADMIN] Установлен search_path: {schema_name}")
            
            # Загружаем запись с клиентом через прямой SQL
            booking_result = await session.execute(
                text(f"""
                    SELECT b.id, b.booking_number, b.service_date, b.time, b.client_id, b.service_id
                    FROM "{schema_name}".bookings b
                    WHERE b.id = :booking_id
                """),
                {"booking_id": booking.id}
            )
            booking_row = booking_result.fetchone()
            
            if not booking_row:
                logger.error(f"❌ [NOTIFY_ADMIN] Запись {booking.id} не найдена в схеме {schema_name}")
                return
            
            # Загружаем клиента
            client_result = await session.execute(
                text(f"""
                    SELECT id, user_id, full_name, phone
                    FROM "{schema_name}".clients
                    WHERE id = :client_id
                """),
                {"client_id": booking_row[4]}  # client_id из booking
            )
            client_row = client_result.fetchone()
            
            if not client_row:
                logger.error(f"❌ [NOTIFY_ADMIN] Клиент {booking_row[4]} не найден")
                return
            
            # Загружаем услугу
            service_result = await session.execute(
                text(f"""
                    SELECT id, name, price, duration
                    FROM "{schema_name}".services
                    WHERE id = :service_id
                """),
                {"service_id": booking_row[5]}  # service_id из booking
            )
            service_row = service_result.fetchone()
            
            # Получаем всех администраторов с Telegram ID (в tenant схемах используется role='admin')
            logger.info(f"📤 [NOTIFY_ADMIN] Ищем администраторов в tenant_{company_id}.users")
            logger.info(f"📤 [NOTIFY_ADMIN] Условия: role='admin' AND telegram_id IS NOT NULL")
            
            admins_result = await session.execute(
                text(f"""
                    SELECT id, telegram_id, username, full_name, phone, role
                    FROM "{schema_name}".users
                    WHERE role = 'admin' AND telegram_id IS NOT NULL
                """)
            )
            admin_rows = admins_result.fetchall()
            
            # Создаем объекты User для совместимости
            admins = []
            for row in admin_rows:
                user = type('User', (), {})()
                user.id = row[0]
                user.telegram_id = row[1]
                user.username = row[2] or ''
                user.full_name = row[3]
                user.phone = row[4]
                user.role = row[5]
                user.is_admin = True
                admins.append(user)
                logger.info(f"📤 [NOTIFY_ADMIN] Найден админ: user_id={user.id}, telegram_id={user.telegram_id}, full_name={user.full_name}")
            
            if not admins:
                logger.warning(f"⚠️ [NOTIFY_ADMIN] === НЕ НАЙДЕНО АДМИНИСТРАТОРОВ ===")
                logger.warning(f"⚠️ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking.id if booking else None}")
                logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: В tenant_{company_id}.users нет пользователей с role='admin' и telegram_id IS NOT NULL")
                return
            
            logger.info(f"✅ [NOTIFY_ADMIN] === НАЙДЕНО {len(admins)} АДМИНИСТРАТОРОВ ===")
            logger.info(f"✅ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking.id if booking else None}")
            
            # Формируем сообщение
            from datetime import datetime
            booking_date = booking_row[2]  # date
            booking_time = booking_row[3]  # time
            date_str = booking_date.strftime("%d.%m.%Y")
            time_str = booking_time.strftime("%H:%M")
            
            client_name = client_row[2] if client_row[2] else "Неизвестно"  # full_name
            client_phone = client_row[3] if client_row[3] else "Не указан"  # phone
            service_name = service_row[1] if service_row else (service.name if service else "Не указана")  # name
            
            logger.info(f"📋 [NOTIFY_ADMIN] Данные записи: booking_number={booking_row[1]}, client_name={client_name}, client_phone={client_phone}, service_name={service_name}")
            
            message_text = f"🔔 Новая запись!\n\n"
            message_text += f"📋 {booking_row[1]}\n"  # booking_number
            message_text += f"   👤 {client_name}\n"
            message_text += f"   📞 {client_phone}\n"
            message_text += f"   📅 {date_str} в {time_str}\n"
            message_text += f"   🛠️ {service_name}\n"
            
            # Отправляем уведомление всем администраторам
            logger.info(f"📤 [NOTIFY_ADMIN] === ОТПРАВКА УВЕДОМЛЕНИЙ АДМИНИСТРАТОРАМ ===")
            logger.info(f"📤 [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking.id if booking else None}")
            logger.info(f"📤 [NOTIFY_ADMIN] Количество админов: {len(admins)}")
            logger.info(f"📤 [NOTIFY_ADMIN] Текст сообщения: {message_text[:200]}...")
            
            sent_count = 0
            failed_count = 0
            for admin in admins:
                try:
                    logger.info(f"📤 [NOTIFY_ADMIN] Отправляем уведомление админу: user_id={admin.id}, telegram_id={admin.telegram_id}, full_name={admin.full_name}")
                    result = await bot.send_message(
                        chat_id=admin.telegram_id,
                        text=message_text
                    )
                    sent_count += 1
                    logger.info(f"✅ [NOTIFY_ADMIN] Уведомление отправлено успешно: user_id={admin.id}, telegram_id={admin.telegram_id}, message_id={result.message_id}")
                except Exception as e:
                    error_msg = str(e)
                    error_type = type(e).__name__
                    failed_count += 1
                    logger.error(f"❌ [NOTIFY_ADMIN] === ОШИБКА ОТПРАВКИ АДМИНУ ===")
                    logger.error(f"❌ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking.id if booking else None}")
                    logger.error(f"❌ [NOTIFY_ADMIN] user_id={admin.id}, telegram_id={admin.telegram_id}, full_name={admin.full_name}")
                    logger.error(f"❌ [NOTIFY_ADMIN] Тип ошибки: {error_type}")
                    logger.error(f"❌ [NOTIFY_ADMIN] Текст ошибки: {error_msg}")
                    logger.error(f"❌ [NOTIFY_ADMIN] Полный traceback:", exc_info=True)
                    
                    # Проверяем специфичные ошибки Telegram API
                    error_lower = error_msg.lower()
                    if "chat not found" in error_lower or "user not found" in error_lower:
                        logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: Админ {admin.id} не начал диалог с ботом или не найден")
                    elif "blocked" in error_lower:
                        logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: Админ {admin.id} заблокировал бота")
                    elif "forbidden" in error_lower:
                        logger.warning(f"⚠️ [NOTIFY_ADMIN] Причина: Бот не может отправить сообщение админу {admin.id}")
            
            logger.info(f"✅ [NOTIFY_ADMIN] === ИТОГИ ОТПРАВКИ ===")
            logger.info(f"✅ [NOTIFY_ADMIN] company_id={company_id}, booking_id={booking.id if booking else None}")
            logger.info(f"✅ [NOTIFY_ADMIN] Отправлено успешно: {sent_count} из {len(admins)}")
            if failed_count > 0:
                logger.warning(f"⚠️ [NOTIFY_ADMIN] Не отправлено: {failed_count} из {len(admins)}")
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error(f"❌ [NOTIFY_ADMIN] === КРИТИЧЕСКАЯ ОШИБКА В notify_admins_about_new_booking ===")
        logger.error(f"❌ [NOTIFY_ADMIN] booking_id={booking.id if booking else None}")
        logger.error(f"❌ [NOTIFY_ADMIN] Тип ошибки: {error_type}")
        logger.error(f"❌ [NOTIFY_ADMIN] Текст ошибки: {error_msg}")
        logger.error(f"❌ [NOTIFY_ADMIN] Полный traceback:", exc_info=True)


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    """Начать процесс записи"""
    # Проверяем подписку компании
    from bot.handlers.booking_subscription_check import check_subscription_before_booking
    can_book = await check_subscription_before_booking(message, state)
    if not can_book:
        # Проверка уже завершена в check_subscription_before_booking
        return
    
    # Получаем company_id из data (передается через SubscriptionMiddleware)
    # Получаем company_id из токена бота (используем отдельную сессию для public схемы)
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = message.bot.token
        logger.info(f"🔑 Получаем company_id для токена: {bot_token[:20]}...")
        
        async with async_session_maker() as temp_session:
            result = await temp_session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
                logger.info(f"✅ Найден company_id: {company_id}")
            else:
                logger.error(f"❌ Компания с таким токеном не найдена! Токен: {bot_token[:20]}...")
    except Exception as e:
        logger.error(f"❌ Ошибка получения company_id из токена: {e}", exc_info=True)
        pass
    
    if not company_id:
        logger.error("❌ Не удалось получить company_id! Услуги не будут найдены.")
        await message.answer("❌ Ошибка конфигурации бота. Обратитесь к администратору.")
        return
    
    async for session in get_session():
        # Получаем company_id из токена бота для правильной работы с tenant схемой
        user = await get_user_by_telegram_id(session, message.from_user.id, company_id=company_id)
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        client = await get_client_by_user_id(session, user.id, company_id=company_id)
        if not client:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        # Получаем список услуг с указанием company_id для установки search_path
        logger.info(f"📋 Запрашиваем услуги для company_id={company_id}")
        services = await get_services(session, active_only=True, company_id=company_id)
        logger.info(f"📊 Получено услуг: {len(services) if services else 0}")
        
        if not services:
            logger.warning(f"⚠️ Нет доступных услуг для company_id={company_id}")
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
    
    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        bot_token = callback.bot.token
        async for session in get_session():
            result = await session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
            break
    except Exception as e:
        logger.error(f"Ошибка получения company_id из токена: {e}")
        pass
    
    async for session in get_session():
        try:
            service = await get_service_by_id(session, service_id, company_id=company_id)
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
    
    # Получаем данные из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    booking_date = data.get("booking_date")

    if not service_id or not booking_date:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    # Сразу переходим к созданию записи (без запроса марки автомобиля)
    logger.info(f"✅ Выбрано время: {selected_time}, переходим к созданию записи")
    await callback.answer("⏳ Создаю запись...")
    await finalize_booking(callback, state)


# Обработчики для марки автомобиля удалены - поле больше не используется


async def finalize_booking(callback, state: FSMContext):
    """Финальное создание заявки"""
    # Получаем данные из состояния
    data = await state.get_data()
    service_id = data.get("service_id")
    service_duration = data.get("service_duration", 60)
    booking_date = data.get("booking_date")
    booking_time = data.get("booking_time")

    if not service_id or not booking_date or not booking_time:
        if hasattr(callback, 'answer'):
            await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    logger.info(f"📋 Создание записи: service_id={service_id}, date={booking_date}, time={booking_time}")

    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = callback.bot.token
        logger.info(f"🔑 Получаем company_id для токена: {bot_token[:20]}...")
        
        async with async_session_maker() as temp_session:
            result = await temp_session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
                logger.info(f"✅ Найден company_id: {company_id}")
            else:
                logger.error(f"❌ Компания с таким токеном не найдена!")
    except Exception as e:
        logger.error(f"❌ Ошибка получения company_id из токена: {e}", exc_info=True)
        pass
    
    if not company_id:
        logger.error("❌ Не удалось получить company_id!")
        if hasattr(callback, 'answer'):
            await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return
    
    async for session in get_session():
        try:
            service = await get_service_by_id(session, service_id, company_id=company_id)
            if not service:
                if hasattr(callback, 'answer'):
                    await callback.answer("❌ Услуга не найдена", show_alert=True)
                return

            # Вычисляем время окончания
            end_time = (datetime.combine(date.min, booking_time) + timedelta(minutes=service_duration)).time()

            user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
            if not user:
                if hasattr(callback, 'answer'):
                    await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

            client = await get_client_by_user_id(session, user.id, company_id=company_id)
            if not client:
                if hasattr(callback, 'answer'):
                    await callback.answer("❌ Клиент не найден. Пройдите регистрацию через /start", show_alert=True)
                return

            # Убрано поле марки автомобиля - comment всегда None
            comment = None
            logger.info(f"Создание заявки без марки автомобиля")

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
                company_id=company_id,
            )
            logger.info(f"Заявка создана: ID={booking.id}, booking_number={booking.booking_number}, comment={comment}")

            # Отправляем уведомление администраторам о новой записи
            try:
                await notify_admins_about_new_booking(callback.bot, booking, service)
                logger.info(f"Уведомление администраторам отправлено для записи {booking.id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления администраторам: {e}", exc_info=True)
                # Не пытаемся через Celery, так как уведомление уже отправлено синхронно
                # Если не удалось - просто логируем ошибку

            # Отправляем подтверждение пользователю
            confirmation_text = (
                f"✅ Запись создана!\n\n"
                f"📅 Дата: {booking.service_date.strftime('%d.%m.%Y')}\n"
                f"⏰ Время: {booking.time.strftime('%H:%M')}\n"
                f"🛠️ Услуга: {service.name}\n"
                f"💰 Цена: {service.price}₽\n\n"
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
    
    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = callback.bot.token
        async with async_session_maker() as temp_session:
            result = await temp_session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
    except Exception as e:
        logger.error(f"Ошибка получения company_id: {e}")
        pass
    
    async for session in get_session():
        from bot.database.crud import get_booking_by_id, get_user_by_telegram_id
        
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
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
            f"📅 Дата: {booking.service_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
            f"Ждем вас в салоне красоты!"
        )
        await callback.answer("✅ Явка подтверждена")


@router.callback_query(F.data.startswith("cancel_booking_"))
async def cancel_booking_by_client(callback: CallbackQuery):
    """Отменить запись клиентом"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = callback.bot.token
        async with async_session_maker() as temp_session:
            result = await temp_session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
    except Exception as e:
        logger.error(f"Ошибка получения company_id: {e}")
        pass
    
    async for session in get_session():
        from bot.database.crud import get_booking_by_id, get_user_by_telegram_id, update_booking_status
        from sqlalchemy import text
        
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        # Проверяем, что это запись этого клиента
        if booking.client.user_id != user.id:
            await callback.answer("❌ Это не ваша запись", show_alert=True)
            return
        
        # Проверяем, что запись еще не отменена или завершена
        if booking.status in ['cancelled', 'completed']:
            await callback.answer("❌ Запись уже отменена или завершена", show_alert=True)
            return
        
        # Обновляем статус записи на "cancelled"
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        await update_booking_status(
            session=session,
            booking_id=booking_id,
            status="cancelled",
            company_id=company_id
        )
        
        # Обновляем сообщение
        await callback.message.edit_text(
            f"❌ Запись отменена\n\n"
            f"📅 Дата: {booking.service_date.strftime('%d.%m.%Y')}\n"
            f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
            f"Если у вас возникли вопросы, свяжитесь с администратором."
        )
        await callback.answer("❌ Запись отменена")

