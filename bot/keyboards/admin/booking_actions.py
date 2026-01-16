"""Клавиатуры для редактирования записей"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional


def get_booking_actions_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру действий с записью.
    
    Args:
        booking_id: ID записи
        
    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="📅 Дата услуги",
        callback_data=f"edit_service_date_{booking_id}"
    ).row()
    
    builder.button(
        text="📝 Дата заявки",
        callback_data=f"edit_request_date_{booking_id}"
    ).row()
    
    builder.button(
        text="💰 Оплата",
        callback_data=f"edit_payment_{booking_id}"
    ).row()
    
    builder.button(
        text="👤 Клиент",
        callback_data=f"edit_client_{booking_id}"
    ).row()
    
    builder.button(
        text="🛠️ Услуга",
        callback_data=f"edit_service_{booking_id}"
    ).row()
    
    builder.button(
        text="👨 Мастер",
        callback_data=f"edit_master_{booking_id}"
    ).row()
    
    builder.button(
        text="🏢 Пост",
        callback_data=f"edit_post_{booking_id}"
    ).row()
    
    builder.button(
        text="⏰ Время",
        callback_data=f"edit_time_{booking_id}"
    ).row()
    
    builder.button(
        text="📝 Коментарий",
        callback_data=f"edit_comment_{booking_id}"
    ).row()
    
    builder.button(
        text="↩️ Назад",
        callback_data=f"back_to_booking_details_{booking_id}"
    ).row()
    
    return builder.as_markup()


def get_edit_service_date_keyboard(booking_id: int, current_service_date: str) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для редактирования даты услуги.
    
    Args:
        booking_id: ID записи
        current_service_date: Текущая дата услуги
        
    Returns:
        InlineKeyboardMarkup с кнопками редактирования
    """
    builder = InlineKeyboardBuilder()
    
    # Показываем текущую дату
    builder.button(
        text=f"📅 Текущая: {current_service_date}",
        callback_data=f"cancel_edit_service_date"
    ).row()
    
    # Быстрые кнопки для выбора дат
    builder.button(
        text="-1 день",
        callback_data=f"change_service_date_-1_{booking_id}"
    ).button(
        text="+1 день",
        callback_data=f"change_service_date_+1_{booking_id}"
    ).row()
    
    builder.button(
        text="-1 неделя",
        callback_data=f"change_service_date_-7_{booking_id}"
    ).button(
        text="+1 неделя",
        callback_data=f"change_service_date_+7_{booking_id}"
    ).row()
    
    # Текущая дата
    builder.button(
        text=f"✅ Подтвердить",
        callback_data=f"confirm_service_date_{booking_id}"
    ).button(
        text="❌ Отмена",
        callback_data=f"cancel_edit_service_date"
    ).row()
    
    return builder.as_markup()


def get_edit_request_date_keyboard(booking_id: int, current_request_date: Optional[str]) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для редактирования даты заявки.
    
    Args:
        booking_id: ID записи
        current_request_date: Текущая дата заявки
        
    Returns:
        InlineKeyboardMarkup с кнопками редактирования
    """
    builder = InlineKeyboardBuilder()
    
    # Показываем текущую дату заявки
    if current_request_date:
        builder.button(
            text=f"📝 Текущая: {current_request_date}",
            callback_data=f"cancel_edit_request_date"
        ).row()
    
    # Быстрые кнопки для выбора дат
    builder.button(
        text="-1 день",
        callback_data=f"change_request_date_-1_{booking_id}"
    ).button(
        text="+1 день",
        callback_data=f"change_request_date_+1_{booking_id}"
    ).row()
    
    builder.button(
        text="-1 неделя",
        callback_data=f"change_request_date_-7_{booking_id}"
    ).button(
        text="+1 неделя",
        callback_data=f"change_request_date_+7_{booking_id}"
    ).row()
    
    # Текущая дата
    builder.button(
        text=f"✅ Подтвердить",
        callback_data=f"confirm_request_date_{booking_id}"
    ).button(
        text="❌ Отмена",
        callback_data=f"cancel_edit_request_date"
    ).row()
    
    return builder.as_markup()
