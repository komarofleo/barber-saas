"""Схемы для аутентификации"""
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Запрос на вход"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Ответ с токеном"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """Информация о пользователе"""
    id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool
    is_master: bool









