"""FSM состояния для генерации договора."""
from aiogram.fsm.state import State, StatesGroup


class ContractStates(StatesGroup):
    """Состояния опроса для генерации договора."""
    customer_name = State()
    customer_inn = State()
    customer_address = State()
    customer_phone = State()
    action_basis = State()
    contract_term = State()
    price_amount = State()
    customer_requisites = State()
    customer_bank_requisites = State()
    signer_name = State()
    confirm = State()
