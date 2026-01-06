"""API для аутентификации"""
from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from dataclasses import dataclass

from app.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.config import settings
from shared.database.models import User

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


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    """Вход в систему"""
    try:
        telegram_id = int(form_data.username)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Ищем пользователя по telegram_id в public схеме
    result = await db.execute(
        text("""
            SELECT id, telegram_id, username, first_name, last_name, phone, 
                   is_admin, is_master, is_blocked, created_at, updated_at
            FROM public.users 
            WHERE telegram_id = :telegram_id
        """),
        {"telegram_id": telegram_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Создаем простой объект UserData
    user = UserData(
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
    
    # Простая проверка: пароль = telegram_id (для начальной версии)
    if form_data.password != str(user.telegram_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Создаем токен
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "is_master": user.is_master or False,
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

