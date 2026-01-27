"""Обработчики генерации договора."""
import logging
import os
from datetime import date
from pathlib import Path
from typing import Dict

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from sqlalchemy.exc import IntegrityError

from app.database import async_session_maker
from app.models.public_models import ContractRequest

from bot.handlers.client.company_contract import _get_main_keyboard
from bot.keyboards.contract import (
    get_skip_keyboard,
    get_confirm_keyboard,
    get_contract_term_keyboard,
)
from bot.services.contract_service import (
    parse_amount,
    build_contract_payload,
    generate_contract_number,
    render_contract_docx,
)
from bot.states.contract_states import ContractStates

logger = logging.getLogger(__name__)
router = Router()


def _get_contract_data(state_data: Dict) -> Dict[str, str]:
    return dict(state_data.get("contract_data", {}))


def _build_summary_text(data: Dict[str, str]) -> str:
    return (
        "📄 Проверьте данные договора:\n\n"
        f"🏷️ Название заказчика: {data.get('НАЗВАНИЕ_ЗАКАЗЧИКА')}\n"
        f"🔢 ИНН/ОГРН: {data.get('ИНН_ЗАКАЗЧИКА')}\n"
        f"📍 Адрес: {data.get('АДРЕС_ЗАКАЗЧИКА')}\n"
        f"📞 Телефон: {data.get('ТЕЛЕФОН_ЗАКАЗЧИКА')}\n"
        f"📜 Основание: {data.get('ОСНОВАНИЕ_ДЕЙСТВИЯ')}\n"
        f"🕒 Срок действия: {data.get('СРОК_ДЕЙСТВИЯ')}\n"
        f"💰 Стоимость: {data.get('СТОИМОСТЬ_ЦИФРАМИ')}\n"
        f"🧾 Реквизиты: {data.get('РЕКВИЗИТЫ_ЗАКАЗЧИКА')}\n"
        f"🏦 Банковские реквизиты: {data.get('БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА') or '—'}\n"
        f"✍️ ФИО подписанта: {data.get('ФИО_ПОДПИСАНТА')}\n"
    )


@router.message(F.text == "/start")
async def start_contract_bot(message: Message, state: FSMContext) -> None:
    """Старт бота генерации договора."""
    if os.getenv("CONTRACT_BOT_DISABLE_START", "false").lower() == "true":
        return
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Здесь можно сгенерировать договор по шаблону.",
        reply_markup=_get_main_keyboard(),
    )


@router.message(F.text == "📄 Генерация договора")
async def start_contract_generation(message: Message, state: FSMContext) -> None:
    """Начать генерацию договора."""
    await state.clear()
    await state.update_data(contract_date=date.today())
    await state.set_state(ContractStates.customer_name)
    await message.answer("Введите полное название заказчика (ИП/ООО):")


@router.message(ContractStates.customer_name)
async def handle_customer_name(message: Message, state: FSMContext) -> None:
    """Сохранить название заказчика."""
    data = _get_contract_data(await state.get_data())
    data["НАЗВАНИЕ_ЗАКАЗЧИКА"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.customer_inn)
    await message.answer("Введите ИНН/ОГРН заказчика:")


@router.message(ContractStates.customer_inn)
async def handle_customer_inn(message: Message, state: FSMContext) -> None:
    """Сохранить ИНН заказчика."""
    data = _get_contract_data(await state.get_data())
    data["ИНН_ЗАКАЗЧИКА"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.customer_address)
    await message.answer("Введите юридический адрес заказчика:")


@router.message(ContractStates.customer_address)
async def handle_customer_address(message: Message, state: FSMContext) -> None:
    """Сохранить адрес заказчика."""
    data = _get_contract_data(await state.get_data())
    data["АДРЕС_ЗАКАЗЧИКА"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.customer_phone)
    await message.answer("Введите телефон заказчика:")


@router.message(ContractStates.customer_phone)
async def handle_customer_phone(message: Message, state: FSMContext) -> None:
    """Сохранить телефон заказчика."""
    data = _get_contract_data(await state.get_data())
    data["ТЕЛЕФОН_ЗАКАЗЧИКА"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.action_basis)
    await message.answer("Введите основание действия (Устав, ЕГРИП, доверенность):")


@router.message(ContractStates.action_basis)
async def handle_action_basis(message: Message, state: FSMContext) -> None:
    """Сохранить основание действия."""
    data = _get_contract_data(await state.get_data())
    data["ОСНОВАНИЕ_ДЕЙСТВИЯ"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.contract_term)
    await message.answer(
        "Выберите срок действия договора:",
        reply_markup=get_contract_term_keyboard(),
    )


@router.message(ContractStates.contract_term)
async def handle_contract_term(message: Message, state: FSMContext) -> None:
    """Сохранить срок действия."""
    allowed_terms = {"1 мес", "3 мес", "6 мес", "9 мес", "12 мес"}
    term_value = message.text.strip()
    if term_value not in allowed_terms:
        await message.answer(
            "❌ Можно выбрать только 1, 3, 6, 9 или 12 месяцев.",
            reply_markup=get_contract_term_keyboard(),
        )
        return
    data = _get_contract_data(await state.get_data())
    data["СРОК_ДЕЙСТВИЯ"] = term_value
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.price_amount)
    await message.answer("Введите стоимость цифрами (например, 10000.00):")


@router.message(ContractStates.price_amount)
async def handle_price_amount(message: Message, state: FSMContext) -> None:
    """Сохранить стоимость."""
    try:
        _ = parse_amount(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректная сумма. Пример: 10000.00")
        return
    
    data = _get_contract_data(await state.get_data())
    data["СТОИМОСТЬ_ЦИФРАМИ"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.customer_requisites)
    await message.answer("Введите полные реквизиты заказчика:")


@router.message(ContractStates.customer_requisites)
async def handle_customer_requisites(message: Message, state: FSMContext) -> None:
    """Сохранить реквизиты заказчика."""
    data = _get_contract_data(await state.get_data())
    data["РЕКВИЗИТЫ_ЗАКАЗЧИКА"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.customer_bank_requisites)
    await message.answer("Введите банковские реквизиты (или нажмите «Пропустить»):", reply_markup=get_skip_keyboard())


@router.message(ContractStates.customer_bank_requisites)
async def handle_customer_bank_requisites(message: Message, state: FSMContext) -> None:
    """Сохранить банковские реквизиты."""
    data = _get_contract_data(await state.get_data())
    if message.text.strip().lower() == "пропустить":
        data["БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА"] = ""
    else:
        data["БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА"] = message.text.strip()
    
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.signer_name)
    await message.answer("Введите ФИО подписанта:", reply_markup=_get_main_keyboard())


@router.message(ContractStates.signer_name)
async def handle_signer_name(message: Message, state: FSMContext) -> None:
    """Сохранить ФИО подписанта."""
    data = _get_contract_data(await state.get_data())
    data["ФИО_ПОДПИСАНТА"] = message.text.strip()
    await state.update_data(contract_data=data)
    await state.set_state(ContractStates.confirm)
    await message.answer(_build_summary_text(data), reply_markup=get_confirm_keyboard())


@router.callback_query(F.data == "contract_cancel", ContractStates.confirm)
async def cancel_contract(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить генерацию договора."""
    await state.clear()
    await callback.message.edit_text("❌ Генерация договора отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=_get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "contract_confirm", ContractStates.confirm)
async def confirm_contract(callback: CallbackQuery, state: FSMContext) -> None:
    """Подтвердить генерацию договора."""
    state_data = await state.get_data()
    contract_date = state_data.get("contract_date", date.today())
    contract_data = _get_contract_data(state_data)
    
    template_path = Path(os.getenv("CONTRACT_TEMPLATE_PATH", "/app/dogovor/dogovor-shablon-tg.docx"))
    output_dir = Path(os.getenv("CONTRACT_OUTPUT_DIR", "/app/dogovor/generated"))
    public_base = os.getenv(
        "CONTRACTS_PUBLIC_BASE_URL",
        "http://45.144.67.47/api/public/contracts"
    ).rstrip("/")
    
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
        await callback.message.answer("Готово. Можно сгенерировать новый договор.", reply_markup=_get_main_keyboard())
        await state.clear()
    except IntegrityError:
        logger.warning("Конфликт номера договора, пробуем снова")
        await callback.message.answer("⚠️ Не удалось сгенерировать номер договора, попробуйте еще раз.")
    except Exception as exc:
        logger.error(f"Ошибка генерации договора: {exc}", exc_info=True)
        await callback.message.answer("❌ Ошибка генерации договора. Попробуйте позже.")
    finally:
        await callback.answer()
