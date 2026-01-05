from pydantic import BaseModel
from typing import Optional
from datetime import date, time, datetime

class BlockedSlotResponse(BaseModel):
    id: int
    block_type: str
    master_id: Optional[int] = None
    post_id: Optional[int] = None
    service_id: Optional[int] = None
    start_date: date
    end_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = None
    created_at: datetime
    master_name: Optional[str] = None
    post_number: Optional[int] = None
    service_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class BlockedSlotListResponse(BaseModel):
    items: list[BlockedSlotResponse]
    total: int

class BlockedSlotCreateRequest(BaseModel):
    block_type: str  # full_service, master, post, service
    master_id: Optional[int] = None
    post_id: Optional[int] = None
    service_id: Optional[int] = None
    start_date: date
    end_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: Optional[str] = None









