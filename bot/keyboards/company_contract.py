"""Клавиатуры для генерации договора по компании."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_company_contract_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения генерации договора."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="company_contract_confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="company_contract_cancel"),
            ]
        ]
    )
