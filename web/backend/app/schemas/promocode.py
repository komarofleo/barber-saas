from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class PromocodeResponse(BaseModel):
    id: int
    code: str
    discount_type: str
    discount_value: Decimal
    service_id: Optional[int] = None
    min_amount: Decimal
    max_uses: Optional[int] = None
    current_uses: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: bool
    description: Optional[str] = None
    created_at: datetime
    service_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class PromocodeListResponse(BaseModel):
    items: list[PromocodeResponse]
    total: int

class PromocodeCreateRequest(BaseModel):
    code: str
    discount_type: str  # percent, fixed
    discount_value: Decimal
    service_id: Optional[int] = None
    min_amount: Decimal = Decimal("0.00")
    max_uses: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None

class PromocodeUpdateRequest(BaseModel):
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    service_id: Optional[int] = None
    min_amount: Optional[Decimal] = None
    max_uses: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class PromocodeValidateResponse(BaseModel):
    valid: bool
    promocode: Optional[PromocodeResponse] = None
    discount_amount: Optional[Decimal] = None
    final_amount: Optional[Decimal] = None
    error: Optional[str] = None









