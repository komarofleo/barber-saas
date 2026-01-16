from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import date, time, datetime
from decimal import Decimal


class BookingResponse(BaseModel):
    id: int
    booking_number: str
    client_id: int
    service_id: Optional[int] = None
    master_id: Optional[int] = None
    post_id: Optional[int] = None
    service_date: date
    request_date: Optional[date] = None
    time: time
    duration: int
    end_time: time
    status: str
    amount: Optional[Decimal] = None
    is_paid: bool = False
    payment_method: Optional[str] = None
    comment: Optional[str] = None
    admin_comment: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Связанные данные
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_telegram_id: Optional[int] = None
    client_car_brand: Optional[str] = None
    client_car_model: Optional[str] = None
    service_name: Optional[str] = None
    master_name: Optional[str] = None
    post_number: Optional[int] = None
    
    # Флаг отправки уведомления
    notification_sent: Optional[bool] = None
    
    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int
    page: int
    page_size: int


class BookingCreateRequest(BaseModel):
    client_id: int
    service_id: Optional[int] = None
    master_id: Optional[int] = None
    post_id: Optional[int] = None
    service_date: date
    time: time
    duration: Optional[int] = 30
    status: Optional[str] = "new"
    amount: Optional[Decimal] = None
    comment: Optional[str] = None


class BookingUpdateRequest(BaseModel):
    client_id: Optional[int] = None
    service_id: Optional[int] = None
    master_id: Optional[int] = None
    post_id: Optional[int] = None
    service_date: Optional[date] = None
    request_date: Optional[date] = None
    time: Optional[time] = None
    duration: Optional[int] = None
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    is_paid: Optional[bool] = None
    payment_method: Optional[str] = None
    comment: Optional[str] = None
    admin_comment: Optional[str] = None
    
    model_config = {"extra": "forbid"}
