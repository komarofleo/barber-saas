"""FSM состояния для регистрации компании через бота."""
from aiogram.fsm.state import State, StatesGroup


class CompanyRegistrationStates(StatesGroup):
    """Состояния упрощенной регистрации компании."""
    waiting_admin_telegram_id = State()
    waiting_email = State()
    waiting_phone = State()
