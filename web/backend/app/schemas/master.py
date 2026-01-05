from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MasterResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    full_name: str
    phone: Optional[str] = None
    telegram_id: Optional[int] = None
    specialization: Optional[str] = None
    is_universal: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class MasterListResponse(BaseModel):
    items: list[MasterResponse]
    total: int
    page: int
    page_size: int


class MasterCreateRequest(BaseModel):
    user_id: Optional[int] = None
    full_name: str
    phone: Optional[str] = None
    telegram_id: Optional[int] = None
    specialization: Optional[str] = None
    is_universal: bool = True


class MasterUpdateRequest(BaseModel):
    user_id: Optional[int] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[int] = None
    specialization: Optional[str] = None
    is_universal: Optional[bool] = None

