from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ServiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    duration: int  # в минутах
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ServiceListResponse(BaseModel):
    items: list[ServiceResponse]
    total: int
    page: int
    page_size: int


class ServiceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    duration: int
    is_active: bool = True


class ServiceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    duration: Optional[int] = None
    is_active: Optional[bool] = None









