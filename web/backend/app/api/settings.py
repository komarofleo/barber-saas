from fastapi import APIRouter, Depends, HTTPException, File, Request, UploadFile
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from ..deps.tenant import get_tenant_db
from ..config import settings
from shared.database.models import User, Setting
from ..schemas.setting import SettingResponse, SettingUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_SETTINGS: dict[str, dict[str, str]] = {
    "work_start_time": {"value": "09:00", "description": "Время начала работы"},
    "work_end_time": {"value": "18:00", "description": "Время окончания работы"},
    "slot_duration": {"value": "30", "description": "Длительность слота в минутах"},
    "reminder_day_before_time": {"value": "10:00", "description": "Время напоминания за день"},
    "reminder_hour_before": {"value": "true", "description": "Напоминание за час"},
    "notify_admin_delay_minutes": {"value": "0", "description": "Задержка уведомления админу"},
    "work_order_time": {"value": "08:00", "description": "Время отправки лист-наряда"},
    "accepting_bookings": {"value": "true", "description": "Принимаются ли заявки (глобальная блокировка)"},
    "enable_master_specialization": {
        "value": "true",
        "description": "Учитывать специализацию мастеров",
    },
    "company_contact_full_name": {
        "value": "",
        "description": "ФИО ответственного лица",
    },
    "company_phone": {
        "value": "",
        "description": "Телефон компании",
    },
    "company_name": {
        "value": "",
        "description": "Название компании",
    },
    "company_bank_details": {
        "value": "",
        "description": "Банковские реквизиты компании",
    },
    "company_address": {
        "value": "",
        "description": "Адрес компании",
    },
    "company_inn": {
        "value": "",
        "description": "ИНН компании",
    },
    "master_specializations": {
        "value": "Парикмахер\nВизажист\nНогтевой мастер\nКосметолог\nБарбер\nКолорист\nСтилист\nМассажист\nЛэшмейкер\nБровист",
        "description": "Список специализаций мастеров (по одной в строке)",
    },
    "bot_welcome_text": {
        "value": "👋 Добро пожаловать в салон красоты!\n\nЗдесь вы можете записаться на наши услуги.",
        "description": "Текст приветствия в Telegram боте",
    },
    "bot_welcome_photo": {
        "value": "",
        "description": "Картинка приветствия (путь к файлу)",
    },
    "bot_about_text": {
        "value": "ℹ️ О нас\n\nСамый лучший салон красоты в городе!\n📞 8 800 555 78 13",
        "description": "Текст раздела «О нас» в Telegram боте",
    },
    "bot_about_photo": {
        "value": "",
        "description": "Картинка для раздела «О нас» (путь к файлу)",
    },
}


def _validate_setting_value(key: str, value: str) -> str:
    """Провалидировать значение настройки."""
    time_keys = {
        "work_start_time",
        "work_end_time",
        "reminder_day_before_time",
        "work_order_time",
    }
    boolean_keys = {
        "accepting_bookings",
        "reminder_hour_before",
        "enable_master_specialization",
    }
    integer_keys = {"slot_duration", "notify_admin_delay_minutes"}

    if key in time_keys:
        if not value or len(value) != 5 or value[2] != ":":
            raise HTTPException(status_code=400, detail="Некорректный формат времени (HH:MM)")
        hours, minutes = value.split(":")
        if not (hours.isdigit() and minutes.isdigit()):
            raise HTTPException(status_code=400, detail="Некорректный формат времени (HH:MM)")
        hours_int = int(hours)
        minutes_int = int(minutes)
        if hours_int < 0 or hours_int > 23 or minutes_int < 0 or minutes_int > 59:
            raise HTTPException(status_code=400, detail="Некорректное значение времени")
        return value

    if key in boolean_keys:
        if value not in {"true", "false"}:
            raise HTTPException(status_code=400, detail="Некорректное логическое значение")
        return value

    if key in integer_keys:
        if value == "" or not value.isdigit():
            raise HTTPException(status_code=400, detail="Некорректное числовое значение")
        return value

    return value


async def _ensure_default_settings(db: AsyncSession) -> None:
    """Создать недостающие настройки по умолчанию."""
    result = await db.execute(select(Setting))
    existing = {setting.key for setting in result.scalars().all()}
    missing_keys = [key for key in DEFAULT_SETTINGS.keys() if key not in existing]
    if not missing_keys:
        return

    for key in missing_keys:
        default_data = DEFAULT_SETTINGS[key]
        db.add(Setting(key=key, value=default_data["value"], description=default_data["description"]))
    await db.commit()

@router.get("", response_model=list[SettingResponse])
async def get_settings(
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить все настройки"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать настройки")

    await _ensure_default_settings(db)
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings = result.scalars().all()
    return [SettingResponse.model_validate(setting) for setting in settings]

@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Получить настройку по ключу"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут просматривать настройки")

    await _ensure_default_settings(db)
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    
    return SettingResponse.model_validate(setting)

@router.patch("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_data: SettingUpdateRequest,
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить настройку"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут изменять настройки")

    if key not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=404, detail="Настройка не найдена")

    normalized_value = _validate_setting_value(key, setting_data.value)
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        default_data = DEFAULT_SETTINGS[key]
        setting = Setting(
            key=key,
            value=normalized_value,
            description=default_data["description"],
        )
        db.add(setting)
    else:
        setting.value = normalized_value
    await db.commit()
    result = await db.execute(select(Setting).where(Setting.key == key))
    fresh_setting = result.scalar_one_or_none()
    if not fresh_setting:
        raise HTTPException(status_code=404, detail="Настройка не найдена")
    return SettingResponse.model_validate(fresh_setting)


@router.post("/upload/{key}", response_model=SettingResponse)
async def upload_setting_file(
    key: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Загрузить файл для настройки (например, изображение бота)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Только администраторы могут изменять настройки")

    allowed_keys = {"bot_welcome_photo", "bot_about_photo"}
    if key not in allowed_keys:
        raise HTTPException(status_code=404, detail="Недоступный ключ для загрузки файла")

    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Разрешены только изображения JPG/PNG/WEBP")

    company_id = getattr(request.state, "company_id", None)
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id не найден")

    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        file_ext = ".jpg"

    target_dir = Path(settings.BOT_MEDIA_DIR) / f"tenant_{company_id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{key}{file_ext}"

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Файл пустой")

    target_path.write_bytes(file_bytes)

    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        default_data = DEFAULT_SETTINGS[key]
        setting = Setting(key=key, value=str(target_path), description=default_data["description"])
        db.add(setting)
    else:
        setting.value = str(target_path)
    await db.commit()
    await db.refresh(setting)

    return SettingResponse.model_validate(setting)









