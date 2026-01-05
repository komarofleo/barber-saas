from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class BroadcastResponse(BaseModel):
    id: int
    text: str
    image_path: Optional[str] = None
    target_audience: str
    filter_params: Optional[Dict[str, Any]] = None
    status: str
    total_sent: int
    total_errors: int
    created_by: Optional[int] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BroadcastListResponse(BaseModel):
    items: list[BroadcastResponse]
    total: int

class BroadcastCreateRequest(BaseModel):
    text: str
    image_path: Optional[str] = None
    target_audience: str  # all, active, new, by_service, selected_clients
    filter_params: Optional[Dict[str, Any]] = None  # Для selected_clients: {"client_ids": [1, 2, 3]}



