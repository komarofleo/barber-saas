from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClientResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: Optional[str] = None
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    car_year: Optional[int] = None
    car_number: Optional[str] = None
    total_visits: int = 0
    total_amount: Optional[float] = None
    created_at: datetime
    
    # Связанные данные
    user_telegram_id: Optional[int] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_is_admin: Optional[bool] = None  # Статус администратора пользователя
    
    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int


class ClientCreateRequest(BaseModel):
    full_name: str
    phone: str
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    car_year: Optional[int] = None
    car_number: Optional[str] = None


class ClientUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    car_brand: Optional[str] = None
    car_model: Optional[str] = None
    car_year: Optional[int] = None
    car_number: Optional[str] = None



