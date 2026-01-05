"""Меню администратора"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.connection import get_session
from bot.database.crud import get_user_by_telegram_id, get_bookings_by_status
from bot.keyboards.admin import get_admin_main_keyboard, get_bookings_keyboard
from bot.keyboards.client import get_client_main_keyboard

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет прав администратора")
            return

        await message.answer(
            "👨‍💼 Панель администратора\n\n"
            "Выберите действие:",
            reply_markup=get_admin_main_keyboard()
        )


@router.message(F.text == "📋 Новые заказы")
async def show_new_bookings(message: Message):
    """Показать новые заказы"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет прав администратора")
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
async def exit_admin_panel(message: Message):
    """Выход из админ-панели"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет прав администратора")
            return

        # Убираем админ-клавиатуру и показываем обычную
        await message.answer(
            "✅ Вы вышли из админ-панели",
            reply_markup=get_client_main_keyboard()
        )

