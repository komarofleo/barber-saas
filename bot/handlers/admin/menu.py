"""Меню администратора"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.connection import get_session
from bot.database.crud import get_user_by_telegram_id, get_bookings_by_status
from bot.keyboards.admin import get_admin_main_keyboard, get_bookings_keyboard
from bot.keyboards.client import get_client_main_keyboard

router = Router()


def is_company_admin(telegram_id: int, bot=None, state: FSMContext = None) -> bool:
    """
    Проверить, является ли пользователь админом компании.
    
    Args:
        telegram_id: Telegram ID пользователя
        bot: Объект бота для доступа к диспетчеру
        state: FSM контекст для доступа к диспетчеру (альтернативный способ)
        
    Returns:
        True если пользователь является админом компании
    """
    import logging
    logger = logging.getLogger(__name__)
    
    dp = None
    
    # Пробуем получить диспетчер из глобального словаря по токену бота
    if bot and hasattr(bot, 'token'):
        try:
            from bot.main import get_dispatcher_by_token, _dispatchers_by_token
            token = bot.token
            logger.info(f"🔑 Ищем диспетчер для токена: {token[:20]}...")
            logger.info(f"📊 Всего диспетчеров в словаре: {len(_dispatchers_by_token)}")
            logger.info(f"📋 Ключи в словаре: {[k[:20] + '...' for k in _dispatchers_by_token.keys()]}")
            dp = get_dispatcher_by_token(token)
            if dp:
                logger.info(f"✅ Диспетчер найден в глобальном словаре по токену")
            else:
                logger.warning(f"⚠️ Диспетчер не найден для токена: {token[:20]}...")
                # Пробуем найти по части токена
                for key in _dispatchers_by_token.keys():
                    if token[:20] in key or key[:20] in token:
                        logger.info(f"🔍 Найден похожий ключ: {key[:20]}...")
                        dp = _dispatchers_by_token[key]
                        break
        except Exception as e:
            logger.error(f"❌ Ошибка получения диспетчера из глобального словаря: {e}", exc_info=True)
    
    # Если не получилось, пробуем через bot
    if not dp and bot:
        try:
            # В aiogram 3.x диспетчер может быть доступен через bot._dispatcher
            if hasattr(bot, '_dispatcher'):
                dp = bot._dispatcher
            # Или через bot.session если есть
            elif hasattr(bot, 'session') and hasattr(bot.session, 'dispatcher'):
                dp = bot.session.dispatcher
        except Exception as e:
            logger.warning(f"⚠️ Не удалось получить диспетчер через bot: {e}")
    
    if dp:
        try:
            admin_telegram_ids = dp.get('admin_telegram_ids', [])
            admin_telegram_id = dp.get('admin_telegram_id')
            
            logger.info(f"🔍 Проверка прав админа: telegram_id={telegram_id}, admin_telegram_id={admin_telegram_id}, admin_telegram_ids={admin_telegram_ids}")
            
            # Проверяем основной админ
            if admin_telegram_id and admin_telegram_id == telegram_id:
                logger.info(f"✅ Пользователь {telegram_id} является основным админом")
                return True
            
            # Проверяем список админов
            if telegram_id in admin_telegram_ids:
                logger.info(f"✅ Пользователь {telegram_id} найден в списке админов")
                return True
            
            logger.warning(f"❌ Пользователь {telegram_id} не является админом")
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке прав: {e}", exc_info=True)
    else:
        logger.error("❌ Диспетчер не найден")
    
    return False


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда /admin"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔵 Получена команда /admin от пользователя {message.from_user.id} (@{message.from_user.username})")
    
    # Получаем диспетчер из bot._dispatcher (сохранен при создании бота)
    dp = None
    is_admin = False
    
    # Пробуем получить через bot._dispatcher
    if hasattr(message.bot, '_dispatcher'):
        dp = message.bot._dispatcher
        logger.info(f"✅ Диспетчер получен из message.bot._dispatcher")
    else:
        logger.warning(f"⚠️ message.bot._dispatcher не найден, пробуем глобальный словарь")
        # Пробуем через глобальный словарь
        try:
            from bot.main import get_dispatcher_by_token
            token = message.bot.token
            logger.info(f"🔑 Ищем диспетчер для токена: {token[:20]}...")
            dp = get_dispatcher_by_token(token)
            if dp:
                logger.info(f"✅ Диспетчер найден в глобальном словаре")
        except Exception as e:
            logger.error(f"❌ Ошибка получения диспетчера: {e}", exc_info=True)
    
    # Если диспетчер найден, проверяем права напрямую
    if dp:
        try:
            admin_telegram_ids = dp.get('admin_telegram_ids', [])
            admin_telegram_id = dp.get('admin_telegram_id')
            logger.info(f"🔍 Проверка прав: telegram_id={message.from_user.id}, admin_telegram_id={admin_telegram_id}, admin_telegram_ids={admin_telegram_ids}")
            
            if admin_telegram_id and admin_telegram_id == message.from_user.id:
                logger.info(f"✅ Пользователь {message.from_user.id} является основным админом")
                is_admin = True
            elif message.from_user.id in admin_telegram_ids:
                logger.info(f"✅ Пользователь {message.from_user.id} найден в списке админов")
                is_admin = True
            else:
                logger.warning(f"❌ Пользователь {message.from_user.id} не является админом (admin_telegram_id={admin_telegram_id}, admin_telegram_ids={admin_telegram_ids})")
                is_admin = False
        except Exception as e:
            logger.error(f"❌ Ошибка проверки прав: {e}", exc_info=True)
            is_admin = False
    else:
        logger.error("❌ Диспетчер не найден ни через bot._dispatcher, ни через глобальный словарь")
        is_admin = False
    
    logger.info(f"🔍 Результат проверки прав: is_admin={is_admin}")
    
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return
    
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        await message.answer(
            "👨‍💼 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_main_keyboard()
        )


@router.message(F.text == "📋 Новые заказы")
async def show_new_bookings(message: Message, state: FSMContext):
    """Показать новые заказы"""
    # Проверяем права через контекст компании
    if not is_company_admin(message.from_user.id, bot=message.bot, state=state):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        bookings = await get_bookings_by_status(session, "new")
        if not bookings:
            await message.answer("✅ Новых заказов нет")
            return

        await message.answer(
            f"📋 Новые заказы ({len(bookings)}):",
            reply_markup=get_bookings_keyboard(bookings)
        )


@router.message(F.text == "🚪 Выход из админ-панели")
async def exit_admin_panel(message: Message, state: FSMContext):
    """Выход из админ-панели"""
    # Проверяем права через контекст компании
    if not is_company_admin(message.from_user.id, bot=message.bot, state=state):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        # Убираем админ-клавиатуру и показываем обычную
        await message.answer(
            "✅ Вы вышли из админ-панели",
            reply_markup=get_client_main_keyboard()
        )

