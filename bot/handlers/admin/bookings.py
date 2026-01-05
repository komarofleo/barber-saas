"""Обработчики для работы с заказами в админ-панели"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.connection import get_session
from bot.database.crud import (
    get_user_by_telegram_id,
    get_bookings_by_status,
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
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("booking_"))
async def show_booking_details(callback: CallbackQuery):
    """Показать детали заказа"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Формируем текст с деталями заказа
        client = booking.client
        service = booking.service
        master = booking.master
        post = booking.post

        text = f"📋 Заказ #{booking.booking_number}\n\n"
        text += f"👤 Клиент: {client.full_name if client else 'Неизвестно'}\n"
        text += f"📞 Телефон: {client.phone if client else 'Не указан'}\n"
        
        if client and client.car_brand:
            text += f"🚗 Авто: {client.car_brand}"
            if client.car_model:
                text += f" {client.car_model}"
            if client.car_number:
                text += f" ({client.car_number})"
            text += "\n"
        
        text += f"\n🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text += f"💰 Цена: {service.price}₽\n" if service else ""
        text += f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Время: {booking.time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
        text += f"⏱️ Длительность: {booking.duration} мин\n"
        text += f"📊 Статус: {booking.status}\n"
        
        if master:
            text += f"👨‍🔧 Мастер: {master.full_name}\n"
        if post:
            text += f"🏢 Пост: {post.name}\n"
        
        if booking.comment:
            text += f"\n💬 Комментарий: {booking.comment}\n"
        
        if booking.admin_comment:
            text += f"\n📝 Комментарий админа: {booking.admin_comment}\n"

        # Показываем кнопки подтверждения только для новых заказов
        if booking.status == "new":
            await callback.message.edit_text(text, reply_markup=get_confirm_keyboard(booking_id))
        else:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_bookings")],
            ])
            await callback.message.edit_text(text, reply_markup=keyboard)
        
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery):
    """Начать подтверждение заказа - выбор мастера"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Получаем список мастеров
        masters = await get_masters(session)
        if not masters:
            await callback.answer("❌ Нет доступных мастеров", show_alert=True)
            return

        service = booking.service
        text = f"📋 Заказ #{booking.booking_number}\n\n"
        text += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text += f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
        text += "👨‍🔧 Выберите мастера:"

        await callback.message.edit_text(
            text,
            reply_markup=get_masters_keyboard(masters, booking_id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_master_"))
async def assign_master_to_booking(callback: CallbackQuery):
    """Назначить мастера заказу"""
    try:
        parts = callback.data.split("_")
        booking_id = int(parts[2])
        if parts[3] == "auto":
            master_id = None  # Автоматический выбор
        else:
            master_id = int(parts[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id)
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        # Если мастер не выбран автоматически, выбираем наименее загруженного
        if master_id is None:
            from bot.database.crud import get_master_bookings_by_date
            masters = await get_masters(session)
            if not masters:
                await callback.answer("❌ Нет доступных мастеров", show_alert=True)
                return
            
            # Находим мастера с наименьшим количеством записей на эту дату
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
            booking = await update_booking_status(session, booking_id, "confirmed", master_id=master_id)
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
            from shared.database.models import Master
            result = await session.execute(select(Master).where(Master.id == master_id))
            master = result.scalar_one_or_none()

        text = f"📋 Заказ #{booking.booking_number}\n\n"
        text += f"🛠️ Услуга: {service.name if service else 'Не указана'}\n"
        text += f"👨‍🔧 Мастер: {master.full_name if master else 'Автоматически'}\n"
        text += f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Время: {booking.time.strftime('%H:%M')}\n\n"
        text += "🏢 Выберите пост:"

        await callback.message.edit_text(
            text,
            reply_markup=get_posts_keyboard(posts, booking_id, master_id or 0)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("assign_post_"))
async def assign_post_to_booking(callback: CallbackQuery):
    """Назначить пост заказу и подтвердить"""
    try:
        parts = callback.data.split("_")
        booking_id = int(parts[2])
        master_id = int(parts[3]) if parts[3] != "0" else None
        if parts[4] == "auto":
            post_id = None  # Автоматический выбор
        else:
            post_id = int(parts[4])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return

        booking = await get_booking_by_id(session, booking_id)
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
            post_id=post_id
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
            f"🏢 Пост: {post_name}\n\n"
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
                    f"🏢 Пост: {post_name}\n\n"
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
async def reject_booking(callback: CallbackQuery):
    """Отклонить заказ"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return

    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return

        booking = await update_booking_status(session, booking_id, "cancelled")
        if not booking:
            await callback.answer("❌ Заказ не найден", show_alert=True)
            return

        await callback.message.edit_text(
            f"❌ Заказ #{booking.booking_number} отклонен.\n\n"
            f"Клиент будет уведомлен."
        )
        await callback.answer("❌ Заказ отклонен")


@router.callback_query(F.data == "back_to_bookings")
async def back_to_bookings(callback: CallbackQuery):
    """Вернуться к списку заказов"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user or not user.is_admin:
            await callback.answer("❌ У вас нет прав", show_alert=True)
            return

        bookings = await get_bookings_by_status(session, "new")
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


@router.message(F.text == "✅ Все заказы")
async def show_all_bookings(message: Message):
    """Показать все заказы"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет прав администратора")
            return

        # Получаем заказы со статусом confirmed
        bookings = await get_bookings_by_status(session, "confirmed")
        if not bookings:
            await message.answer("✅ Подтвержденных заказов нет")
            return

        await message.answer(
            f"✅ Подтвержденные заказы ({len(bookings)}):",
            reply_markup=get_bookings_keyboard(bookings)
        )


@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показать статистику"""
    async for session in get_session():
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user or not user.is_admin:
            await message.answer("❌ У вас нет прав администратора")
            return

        from sqlalchemy import select, func
        from shared.database.models import Booking, Client
        
        # Подсчет статистики
        total_bookings = await session.execute(select(func.count(Booking.id)))
        total = total_bookings.scalar() or 0
        
        new_bookings = await session.execute(
            select(func.count(Booking.id)).where(Booking.status == "new")
        )
        new_count = new_bookings.scalar() or 0
        
        confirmed_bookings = await session.execute(
            select(func.count(Booking.id)).where(Booking.status == "confirmed")
        )
        confirmed_count = confirmed_bookings.scalar() or 0
        
        total_clients = await session.execute(select(func.count(Client.id)))
        clients_count = total_clients.scalar() or 0

        text = "📊 Статистика\n\n"
        text += f"📋 Всего заказов: {total}\n"
        text += f"🆕 Новых: {new_count}\n"
        text += f"✅ Подтвержденных: {confirmed_count}\n"
        text += f"👥 Всего клиентов: {clients_count}\n"

        await message.answer(text)

