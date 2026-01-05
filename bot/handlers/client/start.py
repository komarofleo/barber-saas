"""Обработчик /start и регистрация"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.connection import get_session
from bot.database.crud import get_or_create_user, get_or_create_client
from bot.keyboards.client import get_client_main_keyboard, get_cancel_keyboard
from bot.states.client_states import RegistrationStates

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    async for session in get_session():
        # Получаем или создаем пользователя
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        # Проверяем, зарегистрирован ли как клиент
        from bot.database.crud import get_client_by_user_id
        client = await get_client_by_user_id(session, user.id)

        if not client:
            # Начинаем регистрацию
            await state.set_state(RegistrationStates.waiting_full_name)
            await message.answer(
                "👋 Добро пожаловать в автосервис!\n\n"
                "Для начала работы необходимо пройти регистрацию.\n"
                "Введите ваше ФИО:",
                reply_markup=get_cancel_keyboard()
            )
        else:
            # Пользователь уже зарегистрирован
            await message.answer(
                f"👋 Здравствуйте, {client.full_name}!\n\n"
                "Выберите действие:",
                reply_markup=get_client_main_keyboard()
            )
            await state.clear()


@router.message(RegistrationStates.waiting_full_name, F.text != "❌ Отмена")
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ввода ФИО"""
    full_name = message.text.strip()
    if len(full_name) < 3:
        await message.answer("❌ ФИО должно содержать минимум 3 символа. Попробуйте еще раз:")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_phone)
    await message.answer(
        "📞 Введите ваш номер телефона:\n"
        "(Например: +79991234567 или 89991234567)",
        reply_markup=get_cancel_keyboard()
    )


@router.message(RegistrationStates.waiting_phone, F.text != "❌ Отмена")
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    # Простая валидация телефона
    phone_clean = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone_clean.isdigit() or len(phone_clean) < 10:
        await message.answer("❌ Неверный формат телефона. Попробуйте еще раз:")
        return

    data = await state.get_data()
    full_name = data.get("full_name")

    async for session in get_session():
        # Получаем пользователя
        from bot.database.crud import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, message.from_user.id)

        if user:
            # Создаем клиента
            client = await get_or_create_client(
                session,
                user_id=user.id,
                full_name=full_name,
                phone=phone,
            )

            await message.answer(
                f"✅ Регистрация завершена!\n\n"
                f"ФИО: {client.full_name}\n"
                f"Телефон: {client.phone}\n\n"
                "Теперь вы можете записаться на услугу.",
                reply_markup=get_client_main_keyboard()
            )
            await state.clear()


@router.message(F.text == "❌ Отмена")
async def cancel_registration(message: Message, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    await message.answer(
        "❌ Регистрация отменена.\n"
        "Используйте /start для начала регистрации.",
        reply_markup=get_client_main_keyboard()
    )









