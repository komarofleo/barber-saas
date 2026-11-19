"""Клавиатуры для администраторов"""
from typing import Optional
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню администратора"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Новые заказы")],
            [KeyboardButton(text="✅ Все заказы")],
            [KeyboardButton(text="➕ Создать заказ")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🚪 Выход из админ-панели")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_bookings_keyboard(bookings) -> InlineKeyboardMarkup:
    """Клавиатура списка записей"""
    buttons = []
    for booking in bookings[:10]:  # Показываем первые 10
        client_name = booking.client.full_name if booking.client else "Неизвестно"
        date_str = booking.service_date.strftime("%d.%m")
        time_str = booking.time.strftime("%H:%M")
        service_name = booking.service.name if booking.service else "Неизвестно"
        
        text = f"{date_str} {time_str} - {client_name} ({service_name})"
        if len(text) > 60:
            text = text[:57] + "..."
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"booking_{booking.id}"
            )
        ])
    
    if len(bookings) > 10:
        buttons.append([InlineKeyboardButton(text="📄 Показать еще", callback_data="bookings_more")])
    
    buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{booking_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{booking_id}"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_bookings")],
        ]
    )
    return keyboard


def get_booking_actions_keyboard(booking_id: int, status: str) -> InlineKeyboardMarkup:
    """Клавиатура действий с заказом"""
    buttons = []
    
    # Кнопки изменения статуса
    if status == "new":
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"status_{booking_id}_confirmed"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"status_{booking_id}_cancelled"),
        ])
    elif status == "confirmed":
        buttons.append([
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"status_{booking_id}_completed"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"status_{booking_id}_cancelled"),
        ])
    elif status == "completed":
        buttons.append([
            InlineKeyboardButton(text="↩️ Вернуть", callback_data=f"status_{booking_id}_confirmed"),
        ])
    
    # Кнопки редактирования
    buttons.append([
        InlineKeyboardButton(text="📅 Изменить дату/время", callback_data=f"edit_datetime_{booking_id}"),
        InlineKeyboardButton(text="💰 Изменить оплату", callback_data=f"edit_payment_{booking_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text="👨‍🔧 Изменить мастера", callback_data=f"edit_master_{booking_id}"),
        InlineKeyboardButton(text="🏢 Изменить пост", callback_data=f"edit_post_{booking_id}"),
    ])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад к списку", callback_data="back_to_bookings")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_edit_booking_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура редактирования заказа"""
    buttons = [
        [InlineKeyboardButton(text="📅 Изменить дату/время", callback_data=f"edit_datetime_{booking_id}")],
        [InlineKeyboardButton(text="💰 Изменить оплату", callback_data=f"edit_payment_{booking_id}")],
        [InlineKeyboardButton(text="👨‍🔧 Изменить мастера", callback_data=f"edit_master_{booking_id}")],
        [InlineKeyboardButton(text="🏢 Изменить пост", callback_data=f"edit_post_{booking_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_{booking_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_masters_keyboard(masters, booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора мастера"""
    buttons = []
    for master in masters:
        buttons.append([
            InlineKeyboardButton(
                text=f"👨‍🔧 {master.full_name}",
                callback_data=f"assign_master_{booking_id}_{master.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🤖 Автоматически", callback_data=f"assign_master_{booking_id}_auto")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"booking_{booking_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_posts_keyboard(posts, booking_id: int, master_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора поста"""
    buttons = []
    for post in posts:
        buttons.append([
            InlineKeyboardButton(
                text=f"🏢 {post.name}",
                callback_data=f"assign_post_{booking_id}_{master_id}_{post.id}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🤖 Автоматически", callback_data=f"assign_post_{booking_id}_{master_id}_auto")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"assign_master_{booking_id}_0")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
