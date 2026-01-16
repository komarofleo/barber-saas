"""Клавиатуры для генерации договора."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_contract_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню для генерации договора."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📄 Генерация договора")]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой пропуска опционального поля."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True
    )


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения данных."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="contract_confirm"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="contract_cancel"),
            ]
        ]
    )
