from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    name: str
    content: str
    format: str
    source_type: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    name: str
    format: str
    source_type: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True
