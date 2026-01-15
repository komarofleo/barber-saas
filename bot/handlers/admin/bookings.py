"""Обработчики для работы с заказами в админ-панели"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.database.connection import get_session
from bot.database.crud import (
    get_user_by_telegram_id,
    get_bookings_by_status,
    get_all_bookings,
    get_booking_by_id,
    update_booking_status,
    get_masters,
    get_posts,
)
from bot.keyboards.admin import (
    get_bookings_keyboard, get_confirm_keyboard, get_admin_main_keyboard,
    get_masters_keyboard, get_posts_keyboard
)
from bot.keyboards.client import get_confirm_attendance_keyboard
from shared.database.models import Master, Post
from sqlalchemy import select, text, func

logger = logging.getLogger(__name__)
router = Router()


def get_company_context_from_bot(bot):
    """
    Получить контекст компании из диспетчера бота.
    
    Returns:
        dict с ключами: company_id, admin_telegram_id, admin_telegram_ids
    """
    try:
        dp = getattr(bot, '_dispatcher', None)
        if dp:
            return {
                'company_id': dp.get('company_id'),
                'admin_telegram_id': dp.get('admin_telegram_id'),
                'admin_telegram_ids': dp.get('admin_telegram_ids', []),
                'schema_name': dp.get('schema_name'),
            }
    except Exception as e:
        logger.error(f"❌ Ошибка получения контекста компании: {e}")
    return {}


def is_company_admin_from_bot(telegram_id: int, bot) -> bool:
    """
    Проверить, является ли пользователь админом компании.
    """
    ctx = get_company_context_from_bot(bot)
    admin_telegram_id = ctx.get('admin_telegram_id')
    admin_telegram_ids = ctx.get('admin_telegram_ids', [])
    
    logger.info(f"🔍 Проверка прав админа: telegram_id={telegram_id}, admin_telegram_id={admin_telegram_id}, admin_telegram_ids={admin_telegram_ids}")
    
    if admin_telegram_id and admin_telegram_id == telegram_id:
        logger.info(f"✅ Пользователь {telegram_id} является основным админом")
        return True
    
    if telegram_id in admin_telegram_ids:
        logger.info(f"✅ Пользователь {telegram_id} найден в списке админов")
        return True
    
    logger.warning(f"❌ Пользователь {telegram_id} не является админом")
    return False


@router.message(F.text == "✅ Все заказы")
async def show_all_bookings(message: Message, state: FSMContext):
    """Показать все подтвержденные заказы"""
    logger.info(f"🔵 [HANDLER] show_all_bookings: от пользователя {message.from_user.id}")
    
    # Проверяем права
    if not is_company_admin_from_bot(message.from_user.id, message.bot):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    # Получаем контекст компании
    ctx = get_company_context_from_bot(message.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        logger.error("❌ company_id не найден в контексте!")
        await message.answer("❌ Ошибка конфигурации бота")
        return
    
    logger.info(f"🔵 [HANDLER] company_id={company_id}")
    
    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔵 [HANDLER] Устанавливаем search_path: {schema_name}")
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем пользователя
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        # Получаем заказы со статусом confirmed
        logger.info(f"🔵 [HANDLER] Запрашиваем заказы со статусом 'confirmed'...")
        bookings = await get_bookings_by_status(session, "confirmed", company_id=company_id)
        logger.info(f"🔵 [HANDLER] Получено заказов: {len(bookings) if bookings else 0}")
        
        if not bookings:
            await message.answer("✅ Подтвержденных заказов нет")
            return

        await message.answer(
            f"✅ Подтвержденные заказы ({len(bookings)}):",
            reply_markup=get_bookings_keyboard(bookings)
        )


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message, state: FSMContext):
    """Показать статистику"""
    logger.info(f"🔵 [HANDLER] show_statistics: от пользователя {message.from_user.id}")
    
    # Проверяем права
    if not is_company_admin_from_bot(message.from_user.id, message.bot):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    # Получаем контекст компании
    ctx = get_company_context_from_bot(message.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        logger.error("❌ company_id не найден в контексте!")
        await message.answer("❌ Ошибка конфигурации бота")
        return
    
    logger.info(f"🔵 [HANDLER] company_id={company_id}")
    
    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔵 [HANDLER] Устанавливаем search_path: {schema_name}")
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Проверяем search_path
        result = await session.execute(text("SHOW search_path"))
        current_path = result.scalar()
        logger.info(f"🔵 [HANDLER] Текущий search_path: {current_path}")
        
        # Получаем пользователя
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        from shared.database.models import Booking, Client
        
        # Подсчет статистики
        logger.info(f"🔵 [HANDLER] Подсчитываем статистику...")
        
        total_bookings = await session.execute(select(func.count(Booking.id)))
        total = total_bookings.scalar() or 0
        logger.info(f"🔵 [HANDLER] Всего заказов: {total}")
        
        new_bookings = await session.execute(
            select(func.count(Booking.id)).where(Booking.status == "new")
        )
        new_count = new_bookings.scalar() or 0
        logger.info(f"🔵 [HANDLER] Новых заказов: {new_count}")
        
        confirmed_bookings = await session.execute(
            select(func.count(Booking.id)).where(Booking.status == "confirmed")
        )
        confirmed_count = confirmed_bookings.scalar() or 0
        logger.info(f"🔵 [HANDLER] Подтвержденных заказов: {confirmed_count}")
        
        total_clients = await session.execute(select(func.count(Client.id)))
        clients_count = total_clients.scalar() or 0
        logger.info(f"🔵 [HANDLER] Всего клиентов: {clients_count}")

        stats_text = "📊 Статистика\n\n"
        stats_text += f"📋 Всего заказов: {total}\n"
        stats_text += f"🆕 Новых: {new_count}\n"
        stats_text += f"✅ Подтвержденных: {confirmed_count}\n"
        stats_text += f"👥 Всего клиентов: {clients_count}\n"

        logger.info(f"🔵 [HANDLER] Отправляем статистику")
        await message.answer(stats_text)


@router.callback_query(F.data.startswith("booking_"))
async def show_booking_details(callback: CallbackQuery, state: FSMContext):
    """Показать детали заказа"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Формируем текст с деталями заказа
        client = booking.client
        service = booking.service
        master = booking.master
        post = booking.post

        text_msg = f"📋 Заказ #{booking.booking_number}\n\n"
        text_msg += f"👤 Клиент: {client.full_name if client else 'Неизвестно'}\n"
        text_msg += f"📞 Телефон: {client.phone if client else 'Не указан'}\n"
        
        if client and hasattr(client, 'car_brand') and client.car_brand:
            text_msg += f"🚗 Авто: {client.car_brand}"
            if hasattr(client, 'car_model') and client.car_model:
                text_msg += f" {client.car_model}"
            if hasattr(client, 'car_number') and client.car_number:
                text_msg += f" ({client.car_number})"
            text_msg += "\n"
        
        text_msg += f"\n🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text_msg += f"💰 Цена: {service.price}₽\n" if service else ""
        text_msg += f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        text_msg += f"⏰ Время: {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
        text_msg += f"⏱️ Длительность: {booking.duration} мин\n"
        text_msg += f"📊 Статус: {booking.status}\n"
        
        if master:
            text_msg += f"👨‍🔧 Мастер: {master.full_name}\n"
        if post:
            text_msg += f"🏢 Рабочее место: {post.name}\n"
        
        if booking.comment:
            text_msg += f"\n💬 Комментарий: {booking.comment}\n"
        
        if booking.admin_comment:
            text_msg += f"\n📝 Комментарий админа: {booking.admin_comment}\n"

        # Показываем кнопки подтверждения только для новых заказов
        if booking.status == "new":
            await callback.message.edit_text(text_msg, reply_markup=get_confirm_keyboard(booking_id))
        else:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_bookings")],
            ])
            await callback.message.edit_text(text_msg, reply_markup=keyboard)
        
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Начать подтверждение заказа - выбор мастера"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Получаем список мастеров
        masters = await get_masters(session)
        if not masters:
            await callback.answer("❌ Нет доступных мастеров", show_alert=True)
            return

        service = booking.service
        text_msg = f"📋 Заказ #{booking.booking_number}\n\n"
        text_msg += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text_msg += f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        text_msg += f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
        text_msg += "👨‍🔧 Выберите мастера:"

        await callback.message.edit_text(
            text_msg,
            reply_markup=get_masters_keyboard(masters, booking_id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_master_"))
async def assign_master_to_booking(callback: CallbackQuery, state: FSMContext):
    """Назначить мастера заказу"""
    try:
        parts = callback.data.split("_")
        booking_id = int(parts[2])
        if parts[3] == "auto":
            master_id = None
        else:
            master_id = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Если мастер не выбран, выбираем наименее загруженного
        if master_id is None:
            from bot.database.crud import get_master_bookings_by_date
            masters = await get_masters(session)
            if not masters:
                await callback.answer("❌ Нет доступных мастеров", show_alert=True)
                return
            
            min_bookings = float('inf')
            selected_master = None
            for master in masters:
                bookings_count = len(await get_master_bookings_by_date(session, master.id, booking.date))
                if bookings_count < min_bookings:
                    min_bookings = bookings_count
                    selected_master = master
            
            if selected_master:
                master_id = selected_master.id

        # Получаем список постов
        posts = await get_posts(session)
        if not posts:
            # Если нет постов, подтверждаем сразу
            booking = await update_booking_status(session, booking_id, "confirmed", master_id=master_id, company_id=company_id)
            await callback.message.edit_text(
                f"✅ Заказ #{booking.booking_number} подтвержден!\n\n"
                f"Мастер назначен.\n"
                f"Клиент будет уведомлен."
            )
            await callback.answer("✅ Заказ подтвержден")
            return

        # Показываем выбор поста
        service = booking.service
        master = None
        if master_id:
            result = await session.execute(select(Master).where(Master.id == master_id))
            master = result.scalar_one_or_none()

        text_msg = f"📋 Заказ #{booking.booking_number}\n\n"
        text_msg += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text_msg += f"👨‍🔧 Мастер: {master.full_name if master else 'Автоматически'}\n"
        text_msg += f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        text_msg += f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
        text_msg += "🏢 Выберите рабочее место:"

        await callback.message.edit_text(
            text_msg,
            reply_markup=get_posts_keyboard(posts, booking_id, master_id or 0)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_post_"))
async def assign_post_to_booking(callback: CallbackQuery, state: FSMContext):
    """Назначить пост заказу и подтвердить"""
    try:
        parts = callback.data.split("_")
        booking_id = int(parts[2])
        master_id = int(parts[3]) if parts[3] != "0" else None
        if parts[4] == "auto":
            post_id = None
        else:
            post_id = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Если пост не выбран, выбираем первый доступный
        if post_id is None:
            posts = await get_posts(session)
            if posts:
                post_id = posts[0].id

        # Подтверждаем заказ с назначенными мастером и постом
        booking = await update_booking_status(
            session, booking_id, "confirmed",
            master_id=master_id,
            post_id=post_id,
            company_id=company_id
        )

        if not booking:
            await callback.answer("❌ Ошибка при подтверждении", show_alert=True)
            return

        master_name = "Автоматически"
        if booking.master:
            master_name = booking.master.full_name
        
        post_name = "Не назначен"
        if booking.post:
            post_name = booking.post.name

        await callback.message.edit_text(
            f"✅ Заказ #{booking.booking_number} подтвержден!\n\n"
            f"👨‍🔧 Мастер: {master_name}\n"
            f"🏢 Рабочее место: {post_name}\n\n"
            f"Клиент будет уведомлен."
        )
        await callback.answer("✅ Заказ подтвержден")
        
        # Отправляем уведомление клиенту
        try:
            if booking.client and booking.client.user and booking.client.user.telegram_id:
                service_name = booking.service.name if booking.service else "Не указана"
                client_message = (
                    f"✅ Ваша запись подтверждена!\n\n"
                    f"📋 Номер записи: {booking.booking_number}\n"
                    f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
                    f"⏰ Время: {booking.time.strftime('%H:%M')}\n"
                    f"🛠️ Услуга: {service_name}\n"
                    f"👨‍🔧 Мастер: {master_name}\n"
                    f"🏢 Рабочее место: {post_name}\n\n"
                    f"Пожалуйста, подтвердите явку:"
                )
                await callback.bot.send_message(
                    chat_id=booking.client.user.telegram_id,
                    text=client_message,
                    reply_markup=get_confirm_attendance_keyboard(booking.id)
                )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления клиенту: {e}", exc_info=True)


@router.callback_query(F.data.startswith("reject_"))
async def reject_booking(callback: CallbackQuery, state: FSMContext):
    """Отклонить заказ"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Обновляем статус
        await session.execute(
            text('UPDATE bookings SET status = :status, cancelled_at = CURRENT_TIMESTAMP WHERE id = :booking_id'),
            {"status": "cancelled", "booking_id": booking_id}
        )
        await session.commit()
        
        booking.status = "cancelled"

        await callback.message.edit_text(
            f"❌ Заказ #{booking.booking_number} отклонен.\n\n"
            f"Клиент будет уведомлен."
        )
        await callback.answer("❌ Заказ отклонен")


@router.callback_query(F.data == "back_to_bookings")
async def back_to_bookings(callback: CallbackQuery, state: FSMContext):
    """Вернуться к списку заказов"""
    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return
    
    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        bookings = await get_bookings_by_status(session, "new", company_id=company_id)
        if not bookings:
            await callback.message.edit_text("✅ Новых заказов нет")
        else:
            await callback.message.edit_text(
                f"📋 Новые заказы ({len(bookings)}):",
                reply_markup=get_bookings_keyboard(bookings)
            )
        await callback.answer()


@router.callback_query(F.data == "close")
async def close_bookings_list(callback: CallbackQuery):
    """Закрыть список заказов"""
    await callback.message.delete()
    await callback.answer()
