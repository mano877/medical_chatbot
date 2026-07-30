from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pydantic import EmailStr


class UserCreate(BaseModel):
    name:  str
    email: EmailStr
    age:   Optional[int] = None
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int    

class UserOut(BaseModel):
    id:         int
    name:       str
    email:      str
    age:        Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    
    message: str
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    user_id: int
    conversation_id: int
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

class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes= True
# ─────────────────────────────────────────────
#  Documents
# ─────────────────────────────────────────────


class DocumentOut(BaseModel):
    doc_id: str
    filename: str
    uploaded_at: str
    chunks: int
    status: str


class DocumentListResponse(BaseModel):
    total: int
    documents: list[DocumentOut]


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    message: str