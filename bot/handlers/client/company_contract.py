"""Генерация договора по данным компании."""
import logging
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from bot.database.connection import get_session, async_session_maker
from bot.database.crud import get_setting_value
from bot.keyboards.company_contract import get_company_contract_confirm_keyboard
from bot.states.company_contract_states import CompanyContractStates
from bot.services.contract_service import (
    build_contract_payload,
    generate_contract_number,
    render_contract_docx,
)
from app.models.public_models import ContractRequest

logger = logging.getLogger(__name__)
router = Router()


def _get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню бота договоров."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Генерация договора")],
            [KeyboardButton(text="📄 Договор для пользователей")],
        ],
        resize_keyboard=True,
    )


def _format_amount(value: Optional[Decimal]) -> str:
    """Отформатировать стоимость в формате 0.00."""
    if value is None:
        return "1.00"
    return f"{Decimal(value):.2f}"


def _build_requisites(
    company_name: str,
    company_inn: str,
    company_address: str,
    company_phone: str,
    admin_telegram_id: int,
) -> str:
    """Сформировать реквизиты компании для договора."""
    return (
        f"Название: {company_name}\n"
        f"ИНН: {company_inn}\n"
        f"Адрес: {company_address}\n"
        f"Телефон: {company_phone}\n"
        f"Telegram ID администратора: {admin_telegram_id}"
    )


def _build_summary_text(data: Dict[str, str], admin_telegram_id: int) -> str:
    """Сформировать текст для подтверждения договора."""
    return (
        "📄 Проверьте данные договора:\n\n"
        f"🏷️ Название заказчика: {data.get('НАЗВАНИЕ_ЗАКАЗЧИКА')}\n"
        f"🔢 ИНН: {data.get('ИНН_ЗАКАЗЧИКА')}\n"
        f"📍 Адрес: {data.get('АДРЕС_ЗАКАЗЧИКА')}\n"
        f"📞 Телефон: {data.get('ТЕЛЕФОН_ЗАКАЗЧИКА')}\n"
        f"📜 Основание: {data.get('ОСНОВАНИЕ_ДЕЙСТВИЯ')}\n"
        f"🕒 Срок действия: {data.get('СРОК_ДЕЙСТВИЯ')}\n"
        f"💰 Стоимость: {data.get('СТОИМОСТЬ_ЦИФРАМИ')}\n"
        f"🧾 Реквизиты: {data.get('РЕКВИЗИТЫ_ЗАКАЗЧИКА')}\n"
        f"🏦 Банковские реквизиты: {data.get('БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА')}\n"
        f"✍️ ФИО подписанта: {data.get('ФИО_ПОДПИСАНТА')}\n"
        f"🆔 TG ID админа: {admin_telegram_id}\n"
    )


@router.message(F.text == "📄 Договор для пользователей")
async def start_company_contract(message: Message, state: FSMContext) -> None:
    """Начать генерацию договора по данным компании."""
    await state.clear()
    await state.set_state(CompanyContractStates.waiting_admin_telegram_id)
    await message.answer(
        "Введите Telegram ID администратора компании.\n"
        "ID должен быть зарегистрирован как админ в этой компании."
    )


@router.message(F.text == "/start")
async def start_contract_menu(message: Message, state: FSMContext) -> None:
    """Показать главное меню бота договоров."""
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать!\n\nВыберите действие:",
        reply_markup=_get_main_keyboard(),
    )


@router.message(CompanyContractStates.waiting_admin_telegram_id)
async def handle_admin_telegram_id(message: Message, state: FSMContext) -> None:
    """Принять Telegram ID администратора и подтянуть данные компании."""
    raw_value = (message.text or "").strip()
    if not raw_value.isdigit():
        await message.answer("❌ Telegram ID должен быть числом. Попробуйте ещё раз.")
        return

    admin_telegram_id = int(raw_value)

    async for session in get_session():
        await session.execute(text('SET LOCAL search_path TO "public"'))
        company_row = await session.execute(
            text(
                """
                SELECT c.id, c.name, c.plan_id, p.price_monthly
                FROM public.companies c
                LEFT JOIN public.plans p ON p.id = c.plan_id
                WHERE c.admin_telegram_id = :telegram_id
                   OR :telegram_id = ANY(c.telegram_admin_ids)
                LIMIT 1
                """
            ),
            {"telegram_id": admin_telegram_id},
        )
        company_data = company_row.fetchone()
        if not company_data:
            await message.answer("❌ Компания по этому Telegram ID не найдена.")
            return

        company_id = company_data[0]
        await session.execute(text(f'SET LOCAL search_path TO "tenant_{company_id}", public'))
        admin_row = await session.execute(
            text(
                f"""
                SELECT full_name, phone, role
                FROM "tenant_{company_id}".users
                WHERE telegram_id = :telegram_id
                """
            ),
            {"telegram_id": admin_telegram_id},
        )
        admin_data = admin_row.fetchone()
        if not admin_data or (admin_data[2] or "").lower() != "admin":
            await message.answer("❌ Пользователь не найден или не имеет роль администратора.")
            return

        company_name = await get_setting_value(session, "company_name", company_id=company_id) or company_data[1] or "—"
        company_phone = await get_setting_value(session, "company_phone", company_id=company_id) or (admin_data[1] or "—")
        company_inn = await get_setting_value(session, "company_inn", company_id=company_id) or "—"
        company_address = await get_setting_value(session, "company_address", company_id=company_id) or "—"
        company_bank_details = await get_setting_value(session, "company_bank_details", company_id=company_id) or "—"
        company_contact_full_name = await get_setting_value(
            session, "company_contact_full_name", company_id=company_id
        ) or (admin_data[0] or "—")

        amount_str = _format_amount(company_data[3])
        requisites = _build_requisites(
            company_name=company_name,
            company_inn=company_inn,
            company_address=company_address,
            company_phone=company_phone,
            admin_telegram_id=admin_telegram_id,
        )

        contract_data = {
            "НАЗВАНИЕ_ЗАКАЗЧИКА": company_name,
            "ИНН_ЗАКАЗЧИКА": company_inn,
            "АДРЕС_ЗАКАЗЧИКА": company_address,
            "ТЕЛЕФОН_ЗАКАЗЧИКА": company_phone,
            "ОСНОВАНИЕ_ДЕЙСТВИЯ": "Устав",
            "СРОК_ДЕЙСТВИЯ": "12 месяцев",
            "СТОИМОСТЬ_ЦИФРАМИ": amount_str,
            "РЕКВИЗИТЫ_ЗАКАЗЧИКА": requisites,
            "БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА": company_bank_details,
            "ФИО_ПОДПИСАНТА": company_contact_full_name,
        }

        await state.update_data(
            contract_data=contract_data,
            company_id=company_id,
            admin_telegram_id=admin_telegram_id,
            contract_date=date.today(),
        )
        await state.set_state(CompanyContractStates.confirm)
        await message.answer(
            _build_summary_text(contract_data, admin_telegram_id),
            reply_markup=get_company_contract_confirm_keyboard(),
        )


@router.callback_query(F.data == "company_contract_cancel", CompanyContractStates.confirm)
async def cancel_company_contract(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить генерацию договора."""
    await state.clear()
    await callback.message.edit_text("❌ Генерация договора отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=_get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "company_contract_confirm", CompanyContractStates.confirm)
async def confirm_company_contract(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтвердить генерацию договора."""
    state_data = await state.get_data()
    contract_date = state_data.get("contract_date", date.today())
    contract_data = dict(state_data.get("contract_data", {}))

    template_path = Path(os.getenv("CONTRACT_TEMPLATE_PATH", "/app/dogovor/dogovor-shablon-tg.docx"))
    output_dir = Path(os.getenv("CONTRACT_OUTPUT_DIR", "/app/dogovor/generated"))
    public_base = os.getenv("CONTRACTS_PUBLIC_BASE_URL", "http://45.144.67.47/api/public/contracts").rstrip("/")

    await callback.message.edit_text("⏳ Генерируем договор, подождите...")

    try:
        async with async_session_maker() as session:
            contract_number, daily_seq = await generate_contract_number(session, contract_date)
            payload = build_contract_payload(contract_number, contract_date, contract_data)

            contract_request = ContractRequest(
                requester_telegram_id=callback.from_user.id,
                status="collecting",
                data=contract_data,
                contract_number=contract_number,
                contract_date=contract_date,
                daily_seq=daily_seq,
            )
            session.add(contract_request)
            await session.commit()
            await session.refresh(contract_request)

            file_path = render_contract_docx(
                template_path=template_path,
                output_dir=output_dir,
                payload=payload,
                contract_number=contract_number,
            )
            public_url = f"{public_base}/{file_path.name}"

            contract_request.status = "generated"
            contract_request.document_path = str(file_path)
            contract_request.public_url = public_url
            await session.commit()

        await callback.message.edit_text(
            "✅ Договор готов!\n\n"
            f"🔗 Ссылка: {public_url}\n\n"
            "Файл отправлен ниже."
        )
        await callback.message.answer_document(FSInputFile(str(file_path)))
        await state.clear()
    except IntegrityError:
        logger.warning("Конфликт номера договора, пробуем снова")
        await callback.message.answer("⚠️ Не удалось сгенерировать номер договора, попробуйте ещё раз.")
    except Exception as exc:
        logger.error(f"Ошибка генерации договора: {exc}", exc_info=True)
        await callback.message.answer("❌ Ошибка генерации договора. Попробуйте позже.")
    finally:
        await callback.answer()
