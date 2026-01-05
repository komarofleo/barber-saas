from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class PromotionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount_type: str
    discount_value: Decimal
    service_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    created_at: datetime
    service_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class PromotionListResponse(BaseModel):
    items: list[PromotionResponse]
    total: int

class PromotionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    discount_type: str  # percent, fixed
    discount_value: Decimal
    service_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PromotionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    service_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None









