"""Меню администратора"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.database.connection import get_session
from bot.database.crud import get_user_by_telegram_id, get_bookings_by_status
from bot.keyboards.admin import get_admin_main_keyboard, get_bookings_keyboard
from bot.keyboards.client import get_client_main_keyboard
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
router = Router()


def get_company_context(message: Message):
    """
    Получить контекст компании из диспетчера бота.
    
    Returns:
        dict с ключами: company_id, admin_telegram_id, admin_telegram_ids
    """
    try:
        # Получаем диспетчер из бота
        dp = getattr(message.bot, '_dispatcher', None)
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


def is_company_admin(telegram_id: int, message: Message) -> bool:
    """
    Проверить, является ли пользователь админом компании.
    
    Args:
        telegram_id: Telegram ID пользователя
        message: Сообщение для доступа к боту и диспетчеру
        
    Returns:
        True если пользователь является админом компании
    """
    ctx = get_company_context(message)
    admin_telegram_id = ctx.get('admin_telegram_id')
    admin_telegram_ids = ctx.get('admin_telegram_ids', [])
    
    logger.info(f"🔍 Проверка прав: telegram_id={telegram_id}, admin_telegram_id={admin_telegram_id}, admin_telegram_ids={admin_telegram_ids}")
    
    # Проверяем основной админ
    if admin_telegram_id and admin_telegram_id == telegram_id:
        logger.info(f"✅ Пользователь {telegram_id} является основным админом")
        return True
    
    # Проверяем список админов
    if telegram_id in admin_telegram_ids:
        logger.info(f"✅ Пользователь {telegram_id} найден в списке админов")
        return True
    
    logger.warning(f"❌ Пользователь {telegram_id} не является админом")
    return False


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда /admin - открыть панель администратора"""
    logger.info(f"🔵 Получена команда /admin от пользователя {message.from_user.id} (@{message.from_user.username})")
    
    # Проверяем права
    if not is_company_admin(message.from_user.id, message):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    logger.info(f"🔍 Результат проверки прав: is_admin=True")
    
    # Получаем контекст компании
    ctx = get_company_context(message)
    company_id = ctx.get('company_id')
    
    if not company_id:
        logger.error("❌ company_id не найден в контексте!")
        await message.answer("❌ Ошибка конфигурации бота")
        return
    
    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
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
    logger.info(f"🔵 [HANDLER] show_new_bookings: от пользователя {message.from_user.id}")
    
    # Проверяем права
    if not is_company_admin(message.from_user.id, message):
        logger.warning(f"❌ Пользователь {message.from_user.id} не является админом")
        await message.answer("❌ У вас нет прав администратора")
        return
    
    # Получаем контекст компании
    ctx = get_company_context(message)
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
            logger.error(f"❌ Пользователь {message.from_user.id} не найден в БД")
            await message.answer("❌ Пользователь не найден")
            return
        
        # Получаем заказы со статусом 'new'
        logger.info(f"🔵 [HANDLER] Запрашиваем заказы со статусом 'new'...")
        bookings = await get_bookings_by_status(session, "new", company_id=company_id)
        logger.info(f"🔵 [HANDLER] Получено заказов: {len(bookings) if bookings else 0}")
        
        if not bookings:
            logger.info(f"🔵 [HANDLER] Новых заказов нет")
            await message.answer("✅ Новых заказов нет")
            return

        logger.info(f"🔵 [HANDLER] Отправляем список из {len(bookings)} заказов")
        await message.answer(
            f"📋 Новые заказы ({len(bookings)}):",
            reply_markup=get_bookings_keyboard(bookings)
        )


@router.message(F.text == "🚪 Выход из админ-панели")
async def exit_admin_panel(message: Message, state: FSMContext):
    """Выход из админ-панели"""
    logger.info(f"🔵 [HANDLER] exit_admin_panel: от пользователя {message.from_user.id}")
    
    # Проверяем права
    if not is_company_admin(message.from_user.id, message):
        await message.answer("❌ У вас нет прав администратора")
        return
    
    # Получаем контекст компании
    ctx = get_company_context(message)
    company_id = ctx.get('company_id')
    
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота")
        return
    
    async for session in get_session():
        # Устанавливаем search_path
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        # Убираем админ-клавиатуру и показываем обычную
        await message.answer(
            "✅ Вы вышли из админ-панели",
            reply_markup=get_client_main_keyboard()
        )
