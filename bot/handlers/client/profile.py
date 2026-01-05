"""Обработчики профиля и информации о сервисе"""
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.connection import get_session
from bot.database.crud import get_user_by_telegram_id, get_client_by_user_id
from shared.database.models import ClientHistory, Booking, Client
from sqlalchemy import select
from sqlalchemy.orm import selectinload

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    """Показать профиль клиента"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        client = await get_client_by_user_id(session, user.id)
        if not client:
            await message.answer("❌ Сначала зарегистрируйтесь через /start")
            return

        # Получаем историю обслуживания
        history_result = await session.execute(
            select(ClientHistory)
            .where(ClientHistory.client_id == client.id)
            .order_by(ClientHistory.date.desc())
            .limit(10)
            .options(
                selectinload(ClientHistory.service),
                selectinload(ClientHistory.master),
            )
        )
        history = list(history_result.scalars().all())

        # Получаем марки автомобилей из заявок, если их нет в профиле
        car_brands_from_bookings = set()
        if not client.car_brand:
            bookings_result = await session.execute(
                select(Booking)
                .where(Booking.client_id == client.id)
                .where(Booking.comment.isnot(None))
                .where(Booking.comment.like("Марка автомобиля:%"))
                .order_by(Booking.created_at.desc())
                .limit(10)
            )
            bookings = list(bookings_result.scalars().all())
            
            for booking in bookings:
                if booking.comment and "Марка автомобиля:" in booking.comment:
                    car_brand = booking.comment.replace("Марка автомобиля:", "").strip()
                    # Если есть перенос строки, берем только первую часть
                    if car_brand and "\n" in car_brand:
                        car_brand = car_brand.split("\n")[0].strip()
                    # Фильтруем некорректные значения
                    if car_brand and len(car_brand) >= 2 and len(car_brand) <= 50:
                        invalid_prefixes = ["/", "📋", "⏭️", "❌"]
                        if not any(car_brand.startswith(prefix) for prefix in invalid_prefixes):
                            car_brands_from_bookings.add(car_brand)
        
        # Формируем текст профиля
        text = "👤 Ваш профиль\n\n"
        text += f"📝 ФИО: {client.full_name}\n"
        text += f"📞 Телефон: {client.phone}\n"
        
        # Показываем марку из профиля или из заявок
        if client.car_brand:
            text += f"🚗 Автомобиль: {client.car_brand}"
            if client.car_model:
                text += f" {client.car_model}"
            if client.car_number:
                text += f" ({client.car_number})"
            text += "\n"
        elif car_brands_from_bookings:
            # Показываем марки из заявок
            brands_display = ", ".join(sorted(car_brands_from_bookings))
            text += f"🚗 Автомобили (из заявок): {brands_display}\n"
        
        text += f"\n📊 Статистика:\n"
        text += f"  • Всего визитов: {client.total_visits}\n"
        text += f"  • Общая сумма: {client.total_amount}₽\n"
        
        if history:
            text += f"\n📋 История обслуживания (последние {len(history)}):\n"
            for hist in history:
                date_str = hist.date.strftime("%d.%m.%Y")
                service_name = hist.service.name if hist.service else "Неизвестно"
                master_name = hist.master.full_name if hist.master else ""
                amount = f"{float(hist.amount)}₽" if hist.amount else "—"
                
                text += f"  • {date_str} - {service_name}"
                if master_name:
                    text += f" (Мастер: {master_name})"
                text += f" - {amount}\n"
        else:
            text += "\n📋 История обслуживания: пока нет записей\n"
        
        keyboard = None
        if history:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Показать всю историю", callback_data="show_full_history")]
            ])
        
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "show_full_history")
async def show_full_history(callback):
    """Показать полную историю обслуживания"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        client = await get_client_by_user_id(session, user.id)
        if not client:
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        # Получаем всю историю
        history_result = await session.execute(
            select(ClientHistory)
            .where(ClientHistory.client_id == client.id)
            .order_by(ClientHistory.date.desc())
            .options(
                selectinload(ClientHistory.service),
                selectinload(ClientHistory.master),
            )
        )
        history = list(history_result.scalars().all())

        if not history:
            await callback.answer("История пуста", show_alert=True)
            return

        text = "📋 История обслуживания\n\n"
        for i, hist in enumerate(history, 1):
            date_str = hist.date.strftime("%d.%m.%Y")
            service_name = hist.service.name if hist.service else "Неизвестно"
            master_name = hist.master.full_name if hist.master else ""
            amount = f"{float(hist.amount)}₽" if hist.amount else "—"
            
            text += f"{i}. {date_str}\n"
            text += f"   Услуга: {service_name}\n"
            if master_name:
                text += f"   Мастер: {master_name}\n"
            text += f"   Сумма: {amount}\n"
            if hist.notes:
                text += f"   Примечание: {hist.notes}\n"
            text += "\n"

        # Разбиваем на части если слишком длинное
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await callback.message.answer(part)
        else:
            await callback.message.answer(text)
        
        await callback.answer()


@router.message(F.text == "ℹ️ О нас")
async def show_about(message: Message):
    """Показать информацию о сервисе"""
    text = "ℹ️ О нас\n\n"
    text += "Самый лучший автосерви!\n"
    text += "📞 8 800 555 78 13"
    
    await message.answer(text)

