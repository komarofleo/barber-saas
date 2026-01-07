"""API для аутентификации"""
from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from dataclasses import dataclass
import bcrypt
import logging

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.config import settings
from shared.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class UserData:
    """Простой объект для хранения данных пользователя"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    is_admin: bool
    is_master: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> UserData:
    """Получить текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id: int = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Используем raw SQL с явным указанием схемы public
    result = await db.execute(
        text("""
            SELECT id, telegram_id, username, first_name, last_name, phone, 
                   is_admin, is_master, is_blocked, created_at, updated_at
            FROM public.users 
            WHERE id = :user_id
        """),
        {"user_id": user_id}
    )
    row = result.fetchone()
    if row is None:
        raise credentials_exception
    
    # Создаем простой объект UserData
    return UserData(
        id=row[0],
        telegram_id=row[1],
        username=row[2],
        first_name=row[3],
        last_name=row[4],
        phone=row[5],
        is_admin=row[6],
        is_master=row[7],
        is_blocked=row[8],
        created_at=row[9],
        updated_at=row[10],
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создать JWT токен"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль с помощью bcrypt.
    
    Args:
        plain_password: Введенный пароль
        hashed_password: Хешированный пароль из БД
        
    Returns:
        True, если пароли совпадают, иначе False
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"Ошибка при проверке пароля: {e}")
        return False


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    """
    Универсальный вход в систему.
    
    Поддерживает два способа входа:
    1. По Email и паролю (для владельцев компаний)
    2. По Telegram ID и паролю (для владельцев компаний)
    
    Args:
        form_data: username (Email или Telegram ID) и password
        db: Асинхронная сессия БД
        
    Returns:
        Токен доступа и данные пользователя
    """
    import re
    
    username = form_data.username
    password = form_data.password
    
    logger.info(f"Попытка входа: {username}")
    
    # Определяем, что ввели: Email или Telegram ID
    is_email = re.match(r'^[^@]+@[^@]+\.[^@]+$', username) is not None
    
    if is_email:
        # Пытаемся войти как владелец компании по Email
        logger.info(f"Попытка входа владельца компании по email: {username}")
        
        # Ищем компанию по email в public схеме
        result = await db.execute(
            text("""
                SELECT id, name, email, phone, telegram_bot_token, admin_telegram_id,
                       subscription_status, can_create_bookings, subscription_end_date,
                       password_hash, is_active
                FROM public.companies
                WHERE email = :email
            """),
            {"email": username}
        )
        row = result.fetchone()
        
        if not row:
            logger.warning(f"Компания с email {username} не найдена")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        # Распаковываем данные
        company_id = row[0]
        company_name = row[1]
        company_email = row[2]
        phone = row[3]
        admin_telegram_id = row[5]
        subscription_status = row[6]
        can_create_bookings = row[7]
        subscription_end_date = row[8]
        password_hash = row[9]
        is_active = row[10]
        
        # Проверяем, активна ли компания
        if not is_active:
            logger.warning(f"Компания {company_id} неактивна")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Компания неактивна. Обратитесь в поддержку."
            )
        
        # Проверяем пароль
        if not password_hash:
            logger.warning(f"Пароль не установлен для компании {company_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный email или пароль"
            )
        
        # Проверяем пароль через verify_password
        is_password_valid = verify_password(password, password_hash)
        
        if not is_password_valid:
            logger.warning(f"Неверный пароль для email {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        # Проверяем статус подписки
        if subscription_status != "active":
            logger.warning(f"Подписка компании {company_id} неактивна: {subscription_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Подписка неактивна. Статус: {subscription_status}"
            )
        
        # Создаем токен с company_id
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={
                "sub": str(company_id),
                "type": "company_admin",
                "company_id": company_id
            }, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Владелец компании {company_id} ({username}) успешно вошел в систему")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": company_id,
                "company_id": company_id,
                "telegram_id": admin_telegram_id,
                "username": company_name,
                "first_name": company_name,
                "last_name": None,
                "is_admin": True,
                "is_master": False,
                "email": company_email,
                "phone": phone,
                "subscription_status": subscription_status,
                "can_create_bookings": can_create_bookings,
                "subscription_end_date": subscription_end_date.isoformat() if subscription_end_date else None,
            }
        )
    
    else:
        # Пытаемся войти по Telegram ID (владелец компании)
        try:
            telegram_id = int(username)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        logger.info(f"Попытка входа владельца компании по telegram_id: {telegram_id}")
        
        # Ищем компанию по telegram_id в public схеме
        result = await db.execute(
            text("""
                SELECT id, name, email, phone, telegram_bot_token, admin_telegram_id,
                       subscription_status, can_create_bookings, subscription_end_date,
                       password_hash, is_active
                FROM public.companies
                WHERE admin_telegram_id = :telegram_id
            """),
            {"telegram_id": telegram_id}
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        # Распаковываем данные
        company_id = row[0]
        company_name = row[1]
        company_email = row[2]
        phone = row[3]
        admin_telegram_id = row[5]
        subscription_status = row[6]
        can_create_bookings = row[7]
        subscription_end_date = row[8]
        password_hash = row[9]
        is_active = row[10]
        
        # Проверяем, активна ли компания
        if not is_active:
            logger.warning(f"Компания {company_id} неактивна")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Компания неактивна. Обратитесь в поддержку."
            )
        
        # Проверяем пароль через verify_password
        if not password_hash:
            logger.warning(f"Пароль не установлен для компании {company_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        is_password_valid = verify_password(password, password_hash)
        
        if not is_password_valid:
            logger.warning(f"Неверный пароль для telegram_id {telegram_id} (компания {company_id})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный логин или пароль"
            )
        
        # Проверяем статус подписки
        if subscription_status != "active":
            logger.warning(f"Подписка компании {company_id} неактивна: {subscription_status}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Подписка неактивна. Статус: {subscription_status}"
            )
        
        # Создаем токен с company_id
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={
                "sub": str(company_id),
                "type": "company_admin",
                "company_id": company_id
            }, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"Владелец компании {company_id} ({telegram_id}) успешно вошел в систему по Telegram ID")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": company_id,
                "company_id": company_id,
                "telegram_id": admin_telegram_id,
                "username": company_name,
                "first_name": company_name,
                "last_name": None,
                "is_admin": True,
                "is_master": False,
                "email": company_email,
                "phone": phone,
                "subscription_status": subscription_status,
                "can_create_bookings": can_create_bookings,
                "subscription_end_date": subscription_end_date.isoformat() if subscription_end_date else None,
            }
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserData = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_admin=current_user.is_admin,
        is_master=current_user.is_master or False,
    )


@router.post("/logout")
async def logout():
    """Выход из системы"""
    return {"message": "Successfully logged out"}
