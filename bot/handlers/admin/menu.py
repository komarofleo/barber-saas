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


def is_company_admin(telegram_id: int, state: FSMContext) -> bool:
    """
    Проверить, является ли пользователь админом компании.
    
    Args:
        telegram_id: Telegram ID пользователя
        state: FSM контекст для доступа к диспетчеру
        
    Returns:
        True если пользователь является админом компании
    """
    try:
        dp = state.resolve_dp()
        if dp:
            admin_telegram_ids = dp.get('admin_telegram_ids', [])
            admin_telegram_id = dp.get('admin_telegram_id')
            
            # Проверяем основной админ
            if admin_telegram_id == telegram_id:
                return True
            
            # Проверяем список админов
            if telegram_id in admin_telegram_ids:
                return True
    except:
        pass
    
    return False


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Команда /admin"""
    # Проверяем права через контекст компании
    if not is_company_admin(message.from_user.id, state):
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
    if not is_company_admin(message.from_user.id, state):
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
    if not is_company_admin(message.from_user.id, state):
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

