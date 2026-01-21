"""Упрощенная регистрация компании через @barber76_bot."""
import logging
import os
import re

import httpx
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.client.company_contract import _get_main_keyboard
from bot.states.company_registration_states import CompanyRegistrationStates


logger = logging.getLogger(__name__)
router = Router()

API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", "http://45.144.67.47").rstrip("/")


def _normalize_phone(raw: str) -> str:
    """Нормализовать телефон к формату +7XXXXXXXXXX."""
    digits = re.sub(r"[^\d]", "", raw or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return f"+{digits}"
    return raw


@router.message(F.text == "📝 Регистрация")
async def start_registration(message: Message, state: FSMContext) -> None:
    """Запустить упрощенную регистрацию."""
    await state.clear()
    await state.set_state(CompanyRegistrationStates.waiting_admin_telegram_id)
    await message.answer("Введите Telegram ID администратора:")


@router.message(CompanyRegistrationStates.waiting_admin_telegram_id)
async def handle_admin_telegram_id(message: Message, state: FSMContext) -> None:
    """Сохранить Telegram ID администратора и запросить email."""
    raw_value = (message.text or "").strip()
    if not raw_value.isdigit():
        await message.answer("❌ Telegram ID должен быть числом. Попробуйте ещё раз.")
        return
    await state.update_data(admin_telegram_id=int(raw_value))
    await state.set_state(CompanyRegistrationStates.waiting_email)
    await message.answer("Введите email для входа в систему:")


@router.message(CompanyRegistrationStates.waiting_email)
async def handle_email(message: Message, state: FSMContext) -> None:
    """Сохранить email и запросить телефон."""
    email = (message.text or "").strip()
    if "@" not in email:
        await message.answer("❌ Некорректный email. Попробуйте ещё раз.")
        return
    await state.update_data(email=email)
    await state.set_state(CompanyRegistrationStates.waiting_phone)
    await message.answer("Введите телефон в формате +7XXXXXXXXXX:")


@router.message(CompanyRegistrationStates.waiting_phone)
async def handle_phone(message: Message, state: FSMContext) -> None:
    """Сохранить телефон и выполнить регистрацию."""
    phone_raw = (message.text or "").strip()
    phone = _normalize_phone(phone_raw)

    if not re.match(r"^\+7\d{10}$", phone):
        await message.answer("❌ Телефон должен быть в формате +7XXXXXXXXXX. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    payload = {
        "email": data.get("email"),
        "phone": phone,
        "admin_telegram_id": data.get("admin_telegram_id"),
    }

    await message.answer("⏳ Регистрируем компанию...")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/public/companies/register-lite",
                json=payload,
            )
        if response.status_code != 201:
            await message.answer(f"❌ Ошибка регистрации: {response.text}")
            return

        result = response.json()
        login_email = result.get("login_email")
        password = result.get("password")
        dashboard_url = result.get("dashboard_url") or "http://45.144.67.47/"

        await message.answer(
            "✅ Компания зарегистрирована!\n\n"
            f"🔐 Логин: {login_email}\n"
            f"🔐 Пароль: {password}\n\n"
            f"🌐 Вход: {dashboard_url}\n\n"
            "Остальные данные заполните в Настройках веб‑панели."
        )

        # Отправляем данные на указанный TG ID
        admin_telegram_id = data.get("admin_telegram_id")
        if admin_telegram_id:
            try:
                await message.bot.send_message(
                    admin_telegram_id,
                    "✅ Компания зарегистрирована!\n\n"
                    f"🔐 Логин: {login_email}\n"
                    f"🔐 Пароль: {password}\n\n"
                    f"🌐 Вход: {dashboard_url}"
                )
            except Exception as exc:
                logger.warning(
                    f"⚠️ Не удалось отправить данные в TG {admin_telegram_id}: {exc}"
                )
                await message.answer(
                    "⚠️ Не удалось отправить данные на указанный Telegram ID. "
                    "Убедитесь, что пользователь запускал бота /start."
                )
    except Exception as exc:
        logger.error(f"Ошибка регистрации через бот: {exc}")
        await message.answer("❌ Ошибка регистрации. Попробуйте позже.")
    finally:
        await state.clear()
        await message.answer("Выберите действие:", reply_markup=_get_main_keyboard())
