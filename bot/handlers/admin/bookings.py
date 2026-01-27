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
    get_all_clients,
    get_services,
    create_booking,
)
from bot.keyboards.admin import (
    get_bookings_keyboard, get_confirm_keyboard, get_admin_main_keyboard,
    get_masters_keyboard, get_posts_keyboard, get_booking_actions_keyboard
)
from shared.database.models import Master, Post
from sqlalchemy import select, text, func
from datetime import date, time, timedelta
from bot.states.admin_states import AdminBookingStates, AdminEditBookingStates
from bot.utils.calendar import generate_calendar, get_available_dates
from bot.utils.time_slots import generate_time_slots

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

    # КРИТИЧЕСКАЯ ПРОВЕРКА: Если booking_id == 0, это новый заказ, не обрабатываем
    if booking_id == 0:
        logger.debug(f"🔵 [show_booking_details] Пропускаем: booking_id=0 - это новый заказ. Обрабатывается в bookings_edit.py")
        return  # НЕ вызываем callback.answer(), чтобы не блокировать обработчик в bookings_edit.py

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

        # Получаем данные заказа из БД напрямую
        booking_data_result = await session.execute(
            text('''
                SELECT 
                    b.booking_number, b.service_date, b.time, b.end_time, b.duration, b.status,
                    b.comment, b.admin_comment, b.master_id, b.post_id, b.service_id,
                    c.full_name as client_name, c.phone as client_phone,
                    s.name as service_name, s.price as service_price
                FROM bookings b
                LEFT JOIN clients c ON b.client_id = c.id
                LEFT JOIN services s ON b.service_id = s.id
                WHERE b.id = :booking_id
            '''),
            {"booking_id": booking_id}
        )
        booking_data = booking_data_result.fetchone()
        
        if not booking_data:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return
        
        # Получаем имя мастера если есть
        master_name = None
        if booking_data[8]:  # master_id
            master_result = await session.execute(
                text('SELECT full_name FROM masters WHERE id = :master_id'),
                {"master_id": booking_data[8]}
            )
            master_row = master_result.fetchone()
            if master_row:
                master_name = master_row[0]
        
        # Получаем имя поста если есть
        post_name = None
        if booking_data[9]:  # post_id
            post_result = await session.execute(
                text('SELECT name FROM posts WHERE id = :post_id'),
                {"post_id": booking_data[9]}
            )
            post_row = post_result.fetchone()
            if post_row:
                post_name = post_row[0]

        # Формируем текст с деталями заказа
        text_msg = f"📋 Заказ {booking_data[0]}\n\n"  # booking_number
        text_msg += f"👤 Клиент: {booking_data[11] or 'Неизвестно'}\n"  # client_name
        text_msg += f"📞 Телефон: {booking_data[12] or 'Не указан'}\n"  # client_phone
        
        text_msg += f"\n🛠️ Услуга: {booking_data[13] or 'Не указана'}\n"  # service_name
        if booking_data[14]:  # service_price
            text_msg += f"💰 Цена: {booking_data[14]}₽\n"
        text_msg += f"📅 Дата: {booking_data[1].strftime('%d.%m.%Y')}\n"  # service_date
        text_msg += f"⏰ Время: {booking_data[2].strftime('%H:%M')} - {booking_data[3].strftime('%H:%M')}\n"  # time - end_time
        text_msg += f"⏱️ Длительность: {booking_data[4]} мин\n"  # duration
        text_msg += f"📊 Статус: {booking_data[5]}\n"  # status
        
        if master_name:
            text_msg += f"👨‍🔧 Мастер: {master_name}\n"
        if post_name:
            text_msg += f"🏢 Рабочее место: {post_name}\n"
        
        if booking_data[6]:  # comment
            text_msg += f"\n💬 Комментарий: {booking_data[6]}\n"
        
        if booking_data[7]:  # admin_comment
            text_msg += f"\n📝 Комментарий админа: {booking_data[7]}\n"

        # Показываем кнопки действий с заказом
        from bot.keyboards.admin import get_booking_actions_keyboard
        await callback.message.edit_text(
            text_msg, 
            reply_markup=get_booking_actions_keyboard(booking_id, booking_data[5])  # status
        )
        
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """Начать подтверждение заказа - выбор мастера"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    # КРИТИЧЕСКАЯ ПРОВЕРКА: Если booking_id == 0, это новый заказ, не обрабатываем
    if booking_id == 0:
        logger.debug(f"🔵 [confirm_booking] Пропускаем: booking_id=0 - это новый заказ. Обрабатывается в bookings_edit.py")
        return  # НЕ вызываем callback.answer(), чтобы не блокировать обработчик в bookings_edit.py

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
        masters = await get_masters(session, company_id=company_id)
        if not masters:
            await callback.answer("❌ Нет доступных мастеров", show_alert=True)
            return

        service = booking.service
        text_msg = f"📋 Заказ #{booking.booking_number}\n\n"
        text_msg += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text_msg += f"📅 Дата: {booking.service_date.strftime('%d.%m.%Y')}\n"
        text_msg += f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
        text_msg += "👨‍🔧 Выберите мастера:"

        await callback.message.edit_text(
            text_msg,
            reply_markup=get_masters_keyboard(masters, booking_id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_master_"))
async def assign_master_to_booking(callback: CallbackQuery, state: FSMContext):
    """
    Назначить мастера существующему заказу.
    
    Обрабатывает только существующие заказы (booking_id > 0).
    Новые заказы обрабатываются в bookings_edit.py через admin_select_master.
    
    Формат callback_data: assign_master_{booking_id}_{master_id}
    - booking_id > 0: существующий заказ
    - master_id: ID мастера или "auto" для автоматического выбора
    """
    logger.info(f"🔵 [assign_master_to_booking] НАЧАЛО: callback_data='{callback.data}', user_id={callback.from_user.id}")
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА: Исключаем новые заказы и неправильные форматы
    if callback.data.startswith("assign_master_0_") or callback.data.startswith("new_master_"):
        logger.debug(f"🔵 [assign_master_to_booking] Пропускаем: это новый заказ или неправильный формат")
        await callback.answer("", show_alert=False)
        return
    
    # Парсим callback_data: assign_master_{booking_id}_{master_id}
    try:
        parts = callback.data.split("_")
        if len(parts) < 4:
            logger.warning(f"⚠️ [assign_master_to_booking] Неверный формат callback_data: '{callback.data}'")
            await callback.answer("❌ Ошибка формата", show_alert=True)
            return
        
        booking_id = int(parts[2])
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: booking_id должен быть > 0 (существующий заказ)
        if booking_id <= 0:
            logger.warning(f"⚠️ [assign_master_to_booking] booking_id={booking_id} <= 0, это новый заказ. Пропускаем.")
            await callback.answer("", show_alert=False)
            return
        
        # Парсим master_id
        if parts[3] == "auto":
            master_id = None
        else:
            master_id = int(parts[3])
        
        logger.info(f"🔵 [assign_master_to_booking] Парсинг: booking_id={booking_id}, master_id={master_id}")
        
    except (ValueError, IndexError) as e:
        logger.error(f"❌ [assign_master_to_booking] Ошибка парсинга: {e}, callback_data='{callback.data}'")
        await callback.answer("❌ Ошибка обработки", show_alert=True)
        return

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        logger.error("❌ [assign_master_to_booking] company_id не найден")
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    # Проверяем права администратора
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        logger.warning(f"⚠️ [assign_master_to_booking] Пользователь {callback.from_user.id} не является админом")
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path для tenant схемы
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Проверяем пользователя
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        if not user:
            logger.error(f"❌ [assign_master_to_booking] Пользователь {callback.from_user.id} не найден")
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем заказ из БД
        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            logger.error(f"❌ [assign_master_to_booking] Заказ {booking_id} не найден в БД")
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Если мастер не выбран, выбираем наименее загруженного
        if master_id is None:
            from bot.database.crud import get_master_bookings_by_date
            masters = await get_masters(session, company_id=company_id)
            if not masters:
                await callback.answer("❌ Нет доступных мастеров", show_alert=True)
                return
            
            min_bookings = float('inf')
            selected_master = None
            for master in masters:
                bookings_count = len(await get_master_bookings_by_date(session, master.id, booking.service_date))
                if bookings_count < min_bookings:
                    min_bookings = bookings_count
                    selected_master = master
            
            if selected_master:
                master_id = selected_master.id
                logger.info(f"🔵 [assign_master_to_booking] Автоматически выбран мастер: {master_id}")

        # Получаем список постов
        posts = await get_posts(session, company_id=company_id)
        if not posts:
            # Если нет постов, подтверждаем заказ сразу
            booking = await update_booking_status(
                session,
                booking_id,
                "confirmed",
                master_id=master_id,
                company_id=company_id,
            )
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
        text_msg += f"📅 Дата: {booking.service_date.strftime('%d.%m.%Y')}\n"
        text_msg += f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
        text_msg += "🏢 Выберите рабочее место:"

        await callback.message.edit_text(
            text_msg,
            reply_markup=get_posts_keyboard(posts, booking_id, master_id or 0)
        )
        await callback.answer()


@router.callback_query(
    F.data.startswith("assign_post_") & 
    ~F.data.startswith("assign_post_0_")  # Исключаем новые заказы (booking_id=0)
)
async def assign_post_to_booking(callback: CallbackQuery, state: FSMContext):
    """
    Назначить пост существующему заказу и подтвердить.
    
    Обрабатывает только существующие заказы (booking_id > 0).
    Новые заказы обрабатываются в bookings_edit.py через admin_select_post.
    
    Формат callback_data: assign_post_{booking_id}_{master_id}_{post_id}
    - booking_id > 0: существующий заказ
    - master_id: ID мастера или "0" если не выбран
    - post_id: ID поста или "auto" для автоматического выбора
    """
    logger.info(f"🔵 [assign_post_to_booking] НАЧАЛО: callback_data='{callback.data}', user={callback.from_user.id}")
    
    # КРИТИЧЕСКАЯ ПРОВЕРКА ПЕРВЫМ ДЕЛОМ: Исключаем новые заказы
    try:
        parts = callback.data.split("_")
        if len(parts) < 5:
            logger.warning(f"⚠️ [assign_post_to_booking] Неверный формат callback_data: '{callback.data}'")
            await callback.answer("❌ Ошибка формата", show_alert=True)
            return
        
        booking_id_from_callback = parts[2]  # Может быть "0" для нового заказа
        
        # КРИТИЧЕСКАЯ ПРОВЕРКА: Если booking_id = "0", это новый заказ - НЕ ОБРАБАТЫВАЕМ
        # НЕ вызываем callback.answer(), чтобы обработчик в bookings_edit.py мог обработать callback
        if booking_id_from_callback == "0":
            logger.debug(f"🔵 [assign_post_to_booking] Пропускаем: это новый заказ (booking_id=0). Обрабатывается в bookings_edit.py")
            return  # НЕ вызываем callback.answer(), чтобы не блокировать обработчик в bookings_edit.py
        
        booking_id = int(booking_id_from_callback)
        
        # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: booking_id должен быть > 0
        if booking_id <= 0:
            logger.debug(f"🔵 [assign_post_to_booking] Пропускаем: booking_id={booking_id} <= 0. Обрабатывается в bookings_edit.py")
            return  # НЕ вызываем callback.answer(), чтобы не блокировать обработчик в bookings_edit.py
        
        master_id = int(parts[3]) if parts[3] != "0" else None
        if parts[4] == "auto":
            post_id = None
        else:
            post_id = int(parts[4])
        
        logger.info(f"🔵 [assign_post_to_booking] Парсинг: booking_id={booking_id}, master_id={master_id}, post_id={post_id}")
        
    except (ValueError, IndexError) as e:
        logger.error(f"❌ [assign_post_to_booking] Ошибка парсинга callback_data: {e}, callback_data='{callback.data}'")
        await callback.answer("❌ Ошибка обработки", show_alert=True)
        return
    
    # Проверяем состояние FSM - если это choosing_post, то это новый заказ
    current_state = await state.get_state()
    logger.info(f"🔵 [assign_post_to_booking] current_state={current_state}")
    
    from bot.states.admin_states import AdminBookingStates
    if current_state == AdminBookingStates.choosing_post:
        logger.debug(f"🔵 [assign_post_to_booking] Пропускаем: состояние choosing_post - это новый заказ. Обрабатывается в bookings_edit.py")
        return  # НЕ вызываем callback.answer(), чтобы не блокировать обработчик в bookings_edit.py

    # Получаем контекст компании
    ctx = get_company_context_from_bot(callback.bot)
    company_id = ctx.get('company_id')
    
    if not company_id:
        logger.error("❌ [HANDLER] company_id не найден в контексте!")
        await callback.answer("❌ Ошибка конфигурации бота", show_alert=True)
        return

    logger.info(f"🔵 [HANDLER] company_id={company_id}")

    # Проверяем права
    if not is_company_admin_from_bot(callback.from_user.id, callback.bot):
        await callback.answer("❌ У вас нет прав", show_alert=True)
        return

    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        logger.info(f"🔵 [HANDLER] Устанавливаем search_path: {schema_name}")
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id, company_id=company_id)
        if not booking:
            logger.error(f"❌ [HANDLER] Заказ {booking_id} не найден")
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Если пост не выбран, выбираем первый доступный
        if post_id is None:
            logger.info(f"🔵 [HANDLER] Пост не выбран, выбираем первый доступный")
            posts = await get_posts(session, company_id=company_id)
            if posts:
                post_id = posts[0].id
                logger.info(f"🔵 [HANDLER] Выбран пост: {post_id}")

        logger.info(f"🔵 [HANDLER] Обновляем статус заказа {booking_id}: master_id={master_id}, post_id={post_id}")
        
        # Подтверждаем заказ с назначенными мастером и постом
        booking = await update_booking_status(
            session,
            booking_id,
            "confirmed",
            master_id=master_id,
            post_id=post_id,
            company_id=company_id,
        )

        if not booking:
            logger.error(f"❌ [HANDLER] Ошибка при обновлении статуса заказа {booking_id}")
            await callback.answer("❌ Ошибка при подтверждении", show_alert=True)
            return

        logger.info(f"✅ [HANDLER] Заказ {booking_id} успешно подтвержден")

        # Получаем имена мастера и поста из БД
        master_name = "Автоматически"
        if master_id:
            master_result = await session.execute(
                text('SELECT full_name FROM masters WHERE id = :master_id'),
                {"master_id": master_id}
            )
            master_row = master_result.fetchone()
            if master_row:
                master_name = master_row[0]
        
        post_name = "Не назначен"
        if post_id:
            post_result = await session.execute(
                text('SELECT name FROM posts WHERE id = :post_id'),
                {"post_id": post_id}
            )
            post_row = post_result.fetchone()
            if post_row:
                post_name = post_row[0]

        # Получаем booking_number из БД
        booking_number_result = await session.execute(
            text('SELECT booking_number FROM bookings WHERE id = :booking_id'),
            {"booking_id": booking_id}
        )
        booking_number_row = booking_number_result.fetchone()
        booking_number = booking_number_row[0] if booking_number_row else f"#{booking_id}"

        logger.info(f"🔵 [HANDLER] Отправляем сообщение о подтверждении: booking_number={booking_number}, master={master_name}, post={post_name}")
        
        await callback.message.edit_text(
            f"✅ Заказ {booking_number} подтвержден!\n\n"
            f"👨‍🔧 Мастер: {master_name}\n"
            f"🏢 Рабочее место: {post_name}\n\n"
            f"Клиент будет уведомлен."
        )
        await callback.answer("✅ Заказ подтвержден")
        
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
        
        # Отправляем уведомление клиенту
        try:
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
                    
                    client_message = (
                        f"✅ Ваша запись подтверждена!\n\n"
                        f"📋 Номер записи: {booking_number}\n"
                        f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                        f"⏰ Время: {booking_time.strftime('%H:%M')}\n"
                        f"🛠️ Услуга: {service_name}\n"
                        f"👨‍🔧 Мастер: {master_name}\n"
                        f"🏢 Рабочее место: {post_name}"
                    )
                    await callback.bot.send_message(
                        chat_id=client_telegram_id,
                        text=client_message
                    )
                    logger.info(f"✅ [HANDLER] Уведомление отправлено клиенту {client_telegram_id}")
                else:
                    logger.warning(
                        f"⚠️ [HANDLER] Не найдены данные записи для уведомления: booking_id={booking_id}"
                    )
            else:
                logger.warning(
                    "⚠️ [HANDLER] У клиента нет telegram_id или запись не найдена: "
                    f"booking_id={booking_id}"
                )
        except Exception as e:
            logger.error(f"❌ [HANDLER] Ошибка отправки уведомления клиенту: {e}", exc_info=True)


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
                    
                    client_message = (
                        f"❌ Запись отменена\n\n"
                        f"📋 Номер записи: {booking_number}\n"
                        f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                        f"⏰ Время: {booking_time.strftime('%H:%M')}\n"
                        f"🛠️ Услуга: {service_name}"
                    )
                    
                    await callback.bot.send_message(
                        chat_id=client_telegram_id,
                        text=client_message
                    )
                    logger.info(f"✅ [HANDLER] Уведомление об отмене отправлено клиенту {client_telegram_id}")
                else:
                    logger.warning(
                        f"⚠️ [HANDLER] Не найдены данные записи для уведомления: booking_id={booking_id}"
                    )
            else:
                logger.warning(
                    f"⚠️ [HANDLER] У клиента нет telegram_id или запись не найдена: booking_id={booking_id}"
                )
        except Exception as e:
            logger.error(f"❌ [HANDLER] Ошибка отправки уведомления клиенту об отмене: {e}", exc_info=True)


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
