from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    name:  str
    email: str
    age:   Optional[int] = None


class UserOut(BaseModel):
    id:         int
    name:       str
    email:      str
    age:        Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    user_id: int
    message: str


class ChatResponse(BaseModel):
    user_id:  int
    message:  str
    response: str
    turn:     int


class MessageOut(BaseModel):
    id:         int
    role:       str
    content:    str
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    user_id:  int
    username: str
    total:    int
    messages: list[MessageOut]


class SummaryResponse(BaseModel):
    user_id: int
    summary: str