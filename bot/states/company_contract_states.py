"""Состояния для генерации договора по данным компании."""
from aiogram.fsm.state import State, StatesGroup


class CompanyContractStates(StatesGroup):
    """Состояния сценария генерации договора по TG ID админа."""

    waiting_admin_telegram_id = State()
    confirm = State()
