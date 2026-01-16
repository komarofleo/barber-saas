"""FSM состояния для администраторов"""
from aiogram.fsm.state import State, StatesGroup


class AdminBookingStates(StatesGroup):
    """Состояния создания/редактирования заказа администратором"""
    choosing_client = State()  # Выбор клиента
    creating_client_full_name = State()  # Ввод ФИО нового клиента
    creating_client_phone = State()  # Ввод телефона нового клиента
    choosing_service = State()  # Выбор услуги
    choosing_date = State()  # Выбор даты
    choosing_time = State()  # Выбор времени
    choosing_master = State()  # Выбор мастера
    choosing_post = State()  # Выбор поста
    adding_comment = State()  # Добавление комментария


class AdminEditBookingStates(StatesGroup):
    """Состояния редактирования существующего заказа"""
    editing_service_date = State()  # Изменение даты услуги
    editing_request_date = State()  # Изменение даты заявки
    editing_payment = State()  # Изменение оплаты
    editing_master = State()  # Изменение мастера
    editing_post = State()  # Изменение поста
