from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SettingResponse(BaseModel):
    id: int
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SettingUpdateRequest(BaseModel):
    value: str









