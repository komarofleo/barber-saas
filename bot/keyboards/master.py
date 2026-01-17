"""Клавиатуры для мастеров"""
from datetime import date
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_master_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню мастера"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Лист-наряд")],
            [KeyboardButton(text="🚪 Выход из панели мастера")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_work_order_keyboard(bookings, work_date: date) -> InlineKeyboardMarkup:
    """Клавиатура лист-наряда"""
    buttons = []
    for booking in bookings:
        if isinstance(booking, dict):
            time_value = booking.get("time")
            time_str = time_value.strftime("%H:%M") if time_value else "??:??"
            client_name = booking.get("client_name") or "Неизвестно"
            service_name = booking.get("service_name") or "Неизвестно"
            booking_id = booking.get("id")
        else:
            time_str = booking.time.strftime("%H:%M")
            client_name = booking.client.full_name if booking.client else "Неизвестно"
            service_name = booking.service.name if booking.service else "Неизвестно"
            booking_id = booking.id
        
        text = f"{time_str} - {client_name} ({service_name})"
        if len(text) > 60:
            text = text[:57] + "..."
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"master_booking_{booking_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="📅 Календарь", callback_data="master_calendar_open"),
        InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_work_order"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_booking_actions_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с записью для мастера"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✔️ Завершить",
                    callback_data=f"complete_booking_{booking_id}"
                ),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_work_order")],
        ]
    )
    return keyboard

