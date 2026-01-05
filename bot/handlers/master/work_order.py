"""Обработчики лист-наряда для мастеров"""
import logging
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from bot.database.connection import get_session
from bot.database.crud import get_user_by_telegram_id
from shared.database.models import Master, Booking, Client, Service, Post
from bot.keyboards.master import get_work_order_keyboard, get_booking_actions_keyboard, get_master_main_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("master"))
async def cmd_master(message: Message):
    """Команда /master"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        # Проверяем, является ли пользователь мастером
        result = await session.execute(
            select(Master).where(
                (Master.user_id == user.id) | (Master.telegram_id == user.telegram_id)
            )
        )
        master = result.scalar_one_or_none()

        if not master:
            await message.answer(
                "❌ Вы не зарегистрированы как мастер.\n"
                "Обратитесь к администратору для добавления в систему."
            )
            return

        # Показываем меню мастера
        await message.answer(
            "👨‍🔧 Панель мастера\n\n"
            "Выберите действие:",
            reply_markup=get_master_main_keyboard()
        )


@router.message(F.text == "📋 Лист-наряд")
async def show_work_order_today(message: Message):
    """Показать лист-наряд на сегодня"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            return

        result = await session.execute(
            select(Master).where(
                (Master.user_id == user.id) | (Master.telegram_id == user.telegram_id)
            )
        )
        master = result.scalar_one_or_none()

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер")
            return

        await show_work_order(message, master.id, date.today())


async def show_work_order(message: Message, master_id: int, work_date: date):
    """Показать лист-наряд мастера на дату"""
    async for session in get_session():
        # Получаем записи мастера на дату
        result = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.master_id == master_id,
                    Booking.date == work_date,
                    Booking.status.in_(["confirmed", "new"])
                )
            )
            .order_by(Booking.time.asc())
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
                selectinload(Booking.post),
            )
        )
        bookings = list(result.scalars().all())

        if not bookings:
            await message.answer(
                f"📋 Лист-наряд на {work_date.strftime('%d.%m.%Y')}\n\n"
                f"✅ На сегодня записей нет"
            )
            return

        # Формируем текст лист-наряда
        text = f"📋 Лист-наряд на {work_date.strftime('%d.%m.%Y')}\n\n"
        
        for i, booking in enumerate(bookings, 1):
            client = booking.client
            service = booking.service
            post = booking.post
            
            text += f"{i}. ⏰ {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
            text += f"   🛠️ {service.name if service else 'Не указана'}\n"
            text += f"   👤 {client.full_name if client else 'Неизвестно'}\n"
            if client and client.phone:
                text += f"   📞 {client.phone}\n"
            if client and client.car_number:
                text += f"   🚗 {client.car_number}\n"
            if post:
                text += f"   🏢 {post.name}\n"
            text += f"   📊 Статус: {booking.status}\n"
            if booking.comment:
                text += f"   💬 {booking.comment}\n"
            text += "\n"

        await message.answer(
            text,
            reply_markup=get_work_order_keyboard(bookings, work_date)
        )


@router.callback_query(F.data.startswith("master_booking_"))
async def show_booking_for_master(callback: CallbackQuery):
    """Показать детали записи для мастера"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        from bot.database.crud import get_booking_by_id
        booking = await get_booking_by_id(session, booking_id)
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return

        client = booking.client
        service = booking.service
        post = booking.post

        text = f"📋 Запись #{booking.booking_number}\n\n"
        text += f"⏰ Время: {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
        text += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text += f"👤 Клиент: {client.full_name if client else 'Неизвестно'}\n"
        if client and client.phone:
            text += f"📞 Телефон: {client.phone}\n"
        if client and client.car_brand:
            text += f"🚗 Авто: {client.car_brand}"
            if client.car_model:
                text += f" {client.car_model}"
            if client.car_number:
                text += f" ({client.car_number})"
            text += "\n"
        if post:
            text += f"🏢 Пост: {post.name}\n"
        text += f"📊 Статус: {booking.status}\n"
        if booking.comment:
            text += f"\n💬 Комментарий: {booking.comment}\n"

        # Показываем кнопки действий только для подтвержденных записей
        if booking.status == "confirmed":
            await callback.message.edit_text(
                text,
                reply_markup=get_booking_actions_keyboard(booking_id)
            )
        else:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_work_order")],
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
        
        await callback.answer()


@router.callback_query(F.data.startswith("complete_booking_"))
async def complete_booking(callback: CallbackQuery):
    """Завершить запись"""
    try:
        booking_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        from bot.database.crud import update_booking_status
        booking = await update_booking_status(session, booking_id, "completed")
        if not booking:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return

        await callback.message.edit_text(
            f"✅ Запись #{booking.booking_number} завершена!\n\n"
            f"Работа выполнена."
        )
        await callback.answer("✅ Запись завершена")


@router.callback_query(F.data == "refresh_work_order")
async def refresh_work_order(callback: CallbackQuery):
    """Обновить лист-наряд"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        result = await session.execute(
            select(Master).where(
                (Master.user_id == user.id) | (Master.telegram_id == user.telegram_id)
            )
        )
        master = result.scalar_one_or_none()

        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        await show_work_order(callback.message, master.id, date.today())
        await callback.answer("🔄 Лист-наряд обновлен")


@router.callback_query(F.data == "back_to_work_order")
async def back_to_work_order(callback: CallbackQuery):
    """Вернуться к лист-наряду"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            return

        result = await session.execute(
            select(Master).where(
                (Master.user_id == user.id) | (Master.telegram_id == user.telegram_id)
            )
        )
        master = result.scalar_one_or_none()

        if not master:
            await callback.answer("❌ Мастер не найден", show_alert=True)
            return

        # Получаем записи на сегодня
        result = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.master_id == master.id,
                    Booking.date == date.today(),
                    Booking.status.in_(["confirmed", "new"])
                )
            )
            .order_by(Booking.time.asc())
            .options(
                selectinload(Booking.client).selectinload(Client.user),
                selectinload(Booking.service),
                selectinload(Booking.post),
            )
        )
        bookings = list(result.scalars().all())

        if not bookings:
            await callback.message.edit_text(
                f"📋 Лист-наряд на {date.today().strftime('%d.%m.%Y')}\n\n"
                f"✅ На сегодня записей нет"
            )
        else:
            text = f"📋 Лист-наряд на {date.today().strftime('%d.%m.%Y')}\n\n"
            for i, booking in enumerate(bookings, 1):
                client = booking.client
                service = booking.service
                post = booking.post
                
                text += f"{i}. ⏰ {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                text += f"   🛠️ {service.name if service else 'Не указана'}\n"
                text += f"   👤 {client.full_name if client else 'Неизвестно'}\n"
                if post:
                    text += f"   🏢 {post.name}\n"
                text += "\n"

            await callback.message.edit_text(
                text,
                reply_markup=get_work_order_keyboard(bookings, date.today())
            )
        
        await callback.answer()


@router.message(F.text == "🚪 Выход из панели мастера")
async def exit_master_panel(message: Message):
    """Выход из панели мастера"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Пользователь не найден")
            return

        result = await session.execute(
            select(Master).where(
                (Master.user_id == user.id) | (Master.telegram_id == user.telegram_id)
            )
        )
        master = result.scalar_one_or_none()

        if not master:
            await message.answer("❌ Вы не зарегистрированы как мастер")
            return

        # Убираем мастер-клавиатуру и показываем обычную
        from bot.keyboards.client import get_client_main_keyboard
        await message.answer(
            "✅ Вы вышли из панели мастера",
            reply_markup=get_client_main_keyboard()
        )

