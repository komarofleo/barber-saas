"""Обработчик "Мои записи" для клиентов"""
import logging
from datetime import date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from bot.database.connection import get_session
from bot.database.crud import get_user_by_telegram_id, get_client_by_user_id
from shared.database.models import Booking, Client, Service, Master
from bot.keyboards.client import get_my_bookings_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "📋 Мои записи")
async def show_my_bookings(message: Message):
    """Показать записи клиента"""
    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = message.bot.token
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
        if company_id:
            from sqlalchemy import text
            schema_name = f"tenant_{company_id}"
            await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, message.from_user.id, company_id=company_id)
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        client = await get_client_by_user_id(session, user.id, company_id=company_id)
        if not client:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        # Получаем все записи клиента
        result = await session.execute(
            select(Booking)
            .where(Booking.client_id == client.id)
            .order_by(Booking.service_date.desc(), Booking.time.desc())
            .options(
                selectinload(Booking.service),
                selectinload(Booking.master),
            )
        )
        bookings = list(result.scalars().all())

        if not bookings:
            await message.answer(
                "📋 У вас пока нет записей.\n\n"
                "Создайте запись через кнопку '📅 Записаться'"
            )
            return

        # Группируем по статусам
        new_bookings = [b for b in bookings if b.status == "new"]
        confirmed_bookings = [b for b in bookings if b.status == "confirmed"]
        completed_bookings = [b for b in bookings if b.status == "completed"]
        cancelled_bookings = [b for b in bookings if b.status == "cancelled"]

        text = "📋 Мои записи\n\n"
        
        if new_bookings:
            text += f"🆕 Новые ({len(new_bookings)}):\n"
            for booking in new_bookings[:5]:
                service_name = booking.service.name if booking.service else "Неизвестно"
                text += f"  • {booking.service_date.strftime('%d.%m.%Y')} {booking.time.strftime('%H:%M')} - {service_name}\n"
                text += f"    Номер: {booking.booking_number}\n"
            if len(new_bookings) > 5:
                text += f"  ... и еще {len(new_bookings) - 5}\n"
            text += "\n"

        if confirmed_bookings:
            text += f"✅ Подтвержденные ({len(confirmed_bookings)}):\n"
            for booking in confirmed_bookings[:5]:
                service_name = booking.service.name if booking.service else "Неизвестно"
                master_name = booking.master.full_name if booking.master else "Не назначен"
                text += f"  • {booking.service_date.strftime('%d.%m.%Y')} {booking.time.strftime('%H:%M')} - {service_name}\n"
                text += f"    Мастер: {master_name}\n"
                text += f"    Номер: {booking.booking_number}\n"
            if len(confirmed_bookings) > 5:
                text += f"  ... и еще {len(confirmed_bookings) - 5}\n"
            text += "\n"

        if completed_bookings:
            text += f"✔️ Выполненные ({len(completed_bookings)}):\n"
            for booking in completed_bookings[:3]:
                service_name = booking.service.name if booking.service else "Неизвестно"
                text += f"  • {booking.service_date.strftime('%d.%m.%Y')} - {service_name}\n"
            if len(completed_bookings) > 3:
                text += f"  ... и еще {len(completed_bookings) - 3}\n"
            text += "\n"

        if cancelled_bookings:
            text += f"❌ Отмененные ({len(cancelled_bookings)}):\n"
            for booking in cancelled_bookings[:3]:
                service_name = booking.service.name if booking.service else "Неизвестно"
                text += f"  • {booking.service_date.strftime('%d.%m.%Y')} - {service_name}\n"
            if len(cancelled_bookings) > 3:
                text += f"  ... и еще {len(cancelled_bookings) - 3}\n"

        await message.answer(text)


@router.callback_query(F.data.startswith("my_booking_"))
async def show_booking_details(callback: CallbackQuery):
    """Показать детали записи клиента"""
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

        service = booking.service
        master = booking.master

        text = f"📋 Запись #{booking.booking_number}\n\n"
        text += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text += f"💰 Цена: {service.price}₽\n" if service else ""
        text += f"📅 Дата: {booking.service_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Время: {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
        text += f"📊 Статус: {booking.status}\n"
        
        if master:
            text += f"👨‍🔧 Мастер: {master.full_name}\n"
        
        if booking.comment:
            text += f"\n💬 Комментарий: {booking.comment}\n"

        await callback.message.edit_text(text)
        await callback.answer()









