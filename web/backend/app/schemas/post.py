from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PostResponse(BaseModel):
    id: int
    number: int
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    page_size: int


class PostCreateRequest(BaseModel):
    number: int
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class PostUpdateRequest(BaseModel):
    number: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None









