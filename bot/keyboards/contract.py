"""Клавиатуры для генерации договора."""
import os

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_contract_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню для генерации договора."""
    if os.getenv("CONTRACT_MENU_VARIANT", "").lower() == "barber76":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📄 Генерация договора")],
                [KeyboardButton(text="📄 Договор для пользователей")],
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите действие...",
        )
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


def get_contract_term_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура выбора срока договора в месяцах."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="1 мес"),
                KeyboardButton(text="3 мес"),
                KeyboardButton(text="6 мес"),
            ],
            [
                KeyboardButton(text="9 мес"),
                KeyboardButton(text="12 мес"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите срок договора",
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
