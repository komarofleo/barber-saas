"""Сервис генерации договора."""
import logging
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Optional, Tuple
import uuid

from docxtpl import DocxTemplate
from num2words import num2words
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def parse_amount(value: str) -> Decimal:
    """
    Преобразовать строку суммы в Decimal.
    
    Args:
        value: Строка суммы
    
    Returns:
        Decimal сумма
    
    Raises:
        ValueError: если сумма некорректна
    """
    try:
        normalized = value.replace(" ", "").replace(",", ".")
        amount = Decimal(normalized)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Некорректная сумма") from exc


def amount_to_words(amount: Decimal) -> str:
    """
    Преобразовать сумму в строку прописью.
    
    Args:
        amount: Сумма
    
    Returns:
        Сумма прописью
    """
    rubles = int(amount)
    kopeks = int((amount - Decimal(rubles)) * 100)
    rubles_words = num2words(rubles, lang="ru")
    if kopeks > 0:
        kopeks_words = num2words(kopeks, lang="ru")
        return f"{rubles_words} рублей {kopeks_words} копеек"
    return f"{rubles_words} рублей"


def build_contract_payload(contract_number: str, contract_date: date, data: Dict[str, str]) -> Dict[str, str]:
    """
    Сформировать данные для подстановки в шаблон.
    
    Args:
        contract_number: Номер договора
        contract_date: Дата договора
        data: Данные пользователя
    
    Returns:
        Словарь для шаблона
    """
    month_name = MONTHS_RU.get(contract_date.month, "")
    amount = parse_amount(data["СТОИМОСТЬ_ЦИФРАМИ"])
    
    return {
        "НОМЕР_ДОГОВОРА": contract_number,
        "ДЕНЬ": f"{contract_date.day:02d}",
        "МЕСЯЦ": month_name,
        "ГОД": str(contract_date.year),
        "НАЗВАНИЕ_ЗАКАЗЧИКА": data["НАЗВАНИЕ_ЗАКАЗЧИКА"],
        "ИНН_ЗАКАЗЧИКА": data["ИНН_ЗАКАЗЧИКА"],
        "АДРЕС_ЗАКАЗЧИКА": data["АДРЕС_ЗАКАЗЧИКА"],
        "ТЕЛЕФОН_ЗАКАЗЧИКА": data.get("ТЕЛЕФОН_ЗАКАЗЧИКА", ""),
        "ОСНОВАНИЕ_ДЕЙСТВИЯ": data["ОСНОВАНИЕ_ДЕЙСТВИЯ"],
        "СРОК_ДЕЙСТВИЯ": data["СРОК_ДЕЙСТВИЯ"],
        "СТОИМОСТЬ_ЦИФРАМИ": f"{amount}",
        "СТОИМОСТЬ_ПРОПИСЬЮ": amount_to_words(amount),
        "РЕКВИЗИТЫ_ЗАКАЗЧИКА": data["РЕКВИЗИТЫ_ЗАКАЗЧИКА"],
        "БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА": data.get("БАНКОВСКИЕ_РЕКВИЗИТЫ_ЗАКАЗЧИКА", ""),
        "ФИО_ПОДПИСАНТА": data["ФИО_ПОДПИСАНТА"],
    }


async def generate_contract_number(
    session: AsyncSession,
    contract_date: date,
) -> Tuple[str, int]:
    """
    Сформировать номер договора с авто-нумерацией.
    
    Формат: DOG-YYYYMMDD-XXXX
    
    Args:
        session: Сессия БД
        contract_date: Дата договора
    
    Returns:
        Кортеж (номер договора, порядковый номер внутри дня)
    """
    await session.execute(text('SET LOCAL search_path TO "public"'))
    result = await session.execute(
        text(
            """
            SELECT COALESCE(MAX(daily_seq), 0) 
            FROM public.contract_requests
            WHERE contract_date = :contract_date
            """
        ),
        {"contract_date": contract_date},
    )
    last_seq = int(result.scalar() or 0)
    next_seq = last_seq + 1
    number = f"DOG-{contract_date.strftime('%Y%m%d')}-{next_seq:04d}"
    return number, next_seq


def render_contract_docx(
    template_path: Path,
    output_dir: Path,
    payload: Dict[str, str],
    contract_number: str,
) -> Path:
    """
    Сгенерировать договор по шаблону.
    
    Args:
        template_path: Путь к шаблону
        output_dir: Папка выгрузки
        payload: Данные подстановки
        contract_number: Номер договора
    
    Returns:
        Путь к файлу договора
    """
    if not template_path.exists():
        raise FileNotFoundError("Шаблон договора не найден")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{contract_number}-{uuid.uuid4().hex[:6]}.docx"
    file_path = output_dir / file_name
    
    doc = DocxTemplate(str(template_path))
    doc.render(payload)
    doc.save(str(file_path))
    
    return file_path
