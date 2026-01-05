"""FSM состояния для клиентов"""
from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Состояния регистрации"""
    waiting_full_name = State()
    waiting_phone = State()
    waiting_car_brand = State()
    waiting_car_model = State()
    waiting_car_number = State()


class BookingStates(StatesGroup):
    """Состояния создания записи"""
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    adding_car_brand = State()
    adding_comment = State()





