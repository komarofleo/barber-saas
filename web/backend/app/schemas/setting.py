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


class CompanyCredentialsResponse(BaseModel):
    email: str
    name: str
    admin_telegram_id: Optional[int] = None
    telegram_bot_token: Optional[str] = None


class CompanyCredentialsUpdateRequest(BaseModel):
    name: Optional[str] = None
    admin_telegram_id: Optional[int] = None
    telegram_bot_token: Optional[str] = None


class CompanyCredentialsSendResponse(BaseModel):
    success: bool
    message: str









