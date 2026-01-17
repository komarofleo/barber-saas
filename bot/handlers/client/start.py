"""Обработчик /start и регистрация"""
from aiogram import Router, F
from aiogram.types import FSInputFile, Message, ReplyKeyboardMarkup
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
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔵 Получена команда /start от пользователя {message.from_user.id} (@{message.from_user.username})")
    
    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = message.bot.token
        logger.info(f"🔑 Получаем company_id для токена: {bot_token[:20]}...")
        async with async_session_maker() as temp_session:
            result = await temp_session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
                logger.info(f"✅ Найден company_id: {company_id}")
            else:
                logger.error(f"❌ Компания с таким токеном не найдена!")
    except Exception as e:
        logger.error(f"❌ Ошибка получения company_id: {e}", exc_info=True)
        pass
    
    if not company_id:
        logger.error("❌ Не удалось получить company_id!")
        await message.answer("❌ Ошибка конфигурации бота. Обратитесь к администратору.")
        return
    
    logger.info(f"📋 Начинаем обработку /start для company_id={company_id}, telegram_id={message.from_user.id}")
    
    async def send_welcome_photo(caption: str, reply_markup: ReplyKeyboardMarkup | None = None) -> None:
        """Отправить приветствие с фото."""
        try:
            photo = FSInputFile("/app/bot/salon.jpg")
            logger.info("🖼️ Отправляем приветственное фото")
            await message.answer_photo(photo=photo, caption=caption, reply_markup=reply_markup)
            logger.info("✅ Приветственное фото отправлено")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить фото приветствия: {e}")
            await message.answer(caption, reply_markup=reply_markup)

    async for session in get_session():
        try:
            # Устанавливаем search_path для tenant схемы
            from sqlalchemy import text
            schema_name = f"tenant_{company_id}"
            await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
            logger.info(f"✅ Установлен search_path: {schema_name}")
            
            # Получаем или создаем пользователя
            logger.info(f"👤 Получаем или создаем пользователя telegram_id={message.from_user.id}")
            user = await get_or_create_user(
                session,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                company_id=company_id,
            )
            logger.info(f"✅ Пользователь получен/создан: user_id={user.id if user else None}")

            # Проверяем, зарегистрирован ли как клиент
            from bot.database.crud import get_client_by_user_id
            logger.info(f"🔍 Проверяем наличие клиента для user_id={user.id}")
            client = await get_client_by_user_id(session, user.id, company_id=company_id)
            logger.info(f"✅ Клиент получен: client_id={client.id if client else None}")

            if not client:
                # Начинаем регистрацию
                logger.info(f"📝 Клиент не найден, начинаем регистрацию")
                await state.set_state(RegistrationStates.waiting_full_name)
                await send_welcome_photo(
                    "👋 Добро пожаловать в салон красоты!\n\n"
                    "Здесь вы можете за 1 минуту записаться на наши услуги!\n\n"
                    "Для начала работы необходимо пройти регистрацию.\n"
                    "Введите ваше ФИО:",
                    reply_markup=get_cancel_keyboard()
                )
                logger.info(f"✅ Сообщение о регистрации отправлено")
            else:
                # Пользователь уже зарегистрирован
                logger.info(f"✅ Клиент найден: {client.full_name}, отправляем главное меню")
                await send_welcome_photo(
                    f"👋 Здравствуйте, {client.full_name}!\n\n"
                    "Здесь вы можете за 1 минуту записаться на наши услуги!\n\n"
                    "Выберите действие:",
                    reply_markup=get_client_main_keyboard()
                )
                await state.clear()
                logger.info(f"✅ Главное меню отправлено")
        except Exception as e:
            logger.error(f"❌ Ошибка в cmd_start: {e}", exc_info=True)
            await message.answer("❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору.")


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

    # Получаем company_id из токена бота
    company_id = None
    try:
        from sqlalchemy import text
        from bot.database.connection import async_session_maker
        bot_token = message.bot.token
        async with async_session_maker() as temp_session:
            result = await temp_session.execute(
                text("SELECT id FROM public.companies WHERE telegram_bot_token = :token"),
                {"token": bot_token}
            )
            row = result.fetchone()
            if row:
                company_id = row[0]
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка получения company_id: {e}")
        pass
    
    if not company_id:
        await message.answer("❌ Ошибка конфигурации бота. Обратитесь к администратору.")
        return
    
    async for session in get_session():
        # Устанавливаем search_path для tenant схемы
        from sqlalchemy import text
        schema_name = f"tenant_{company_id}"
        await session.execute(text(f'SET LOCAL search_path TO "{schema_name}", public'))
        
        # Получаем пользователя
        from bot.database.crud import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, message.from_user.id, company_id=company_id)

        if user:
            # Создаем клиента
            client = await get_or_create_client(
                session,
                user_id=user.id,
                full_name=full_name,
                phone=phone,
                company_id=company_id,
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









