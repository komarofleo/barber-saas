"""Клавиатуры для клиентов"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_client_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню клиента"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Записаться")],
            [KeyboardButton(text="📋 Мои записи")],
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="ℹ️ О нас")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_services_keyboard(services) -> InlineKeyboardMarkup:
    """Клавиатура выбора услуги"""
    buttons = []
    for service in services:
        buttons.append([
            InlineKeyboardButton(
                text=f"{service.name} ({service.duration} мин)",
                callback_data=f"service_{service.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❓ Другое", callback_data="service_other")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура отмены"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )
    return keyboard


def get_time_slots_keyboard(time_slots) -> InlineKeyboardMarkup:
    """Клавиатура выбора времени"""
    buttons = []
    for start_time, end_time in time_slots:
        buttons.append([
            InlineKeyboardButton(
                text=f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                callback_data=f"time_{start_time.hour}_{start_time.minute}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_my_bookings_keyboard(bookings) -> InlineKeyboardMarkup:
    """Клавиатура списка записей клиента"""
    buttons = []
    for booking in bookings[:10]:
        date_str = booking.service_date.strftime("%d.%m")
        time_str = booking.time.strftime("%H:%M")
        service_name = booking.service.name if booking.service else "Неизвестно"
        
        text = f"{date_str} {time_str} - {service_name}"
        if len(text) > 60:
            text = text[:57] + "..."
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"my_booking_{booking.id}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_attendance_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения явки на запись"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить явку",
                callback_data=f"confirm_attendance_{booking_id}"
            )
        ]
    ])
    return keyboard

