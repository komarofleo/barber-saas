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
        import logging
        logger = logging.getLogger(__name__)
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

        # Формируем текст профиля
        text = "👤 Ваш профиль\n\n"
        text += f"📝 ФИО: {client.full_name}\n"
        text += f"📞 Телефон: {client.phone}\n"
        
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка получения company_id: {e}")
        pass
    
    async for session in get_session():
        if company_id:
            from sqlalchemy import text
            schema_name = f"tenant_{company_id}"
            await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        user = await get_user_by_telegram_id(session, callback.from_user.id, company_id=company_id)
        if not user:
            await callback.answer("❌ Ошибка", show_alert=True)
            return

        client = await get_client_by_user_id(session, user.id, company_id=company_id)
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
    """Показать информацию о салоне красоты"""
    text = "ℹ️ О нас\n\n"
    text += "Самый лучший салон красоты в городе!\n"
    text += "📞 8 800 555 78 13"
    
    await message.answer(text)

