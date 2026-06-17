from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from database import (
    get_db, create_tables,
    User, Message,
    settings
)

# ─────────────────────────────────────────────
#  App
# ─────────────────────────────────────────────
app = FastAPI(
    title="🏥 Medical Assistant Chatbot API",
    description="""
A friendly AI doctor chatbot powered by **FastAPI + LangChain + Ollama**.

Each user has their own persistent chat history stored in **PostgreSQL**.

> ⚠️ *This chatbot is for informational purposes only and does not replace a real doctor.*
    """,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()


# ─────────────────────────────────────────────
#  LLM
# ─────────────────────────────────────────────
llm = OllamaLLM(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
)
output_parser = StrOutputParser()

DOCTOR_SYSTEM_PROMPT = """You are Dr. Aria, a warm, friendly, and knowledgeable AI medical assistant.

Your personality:
- Speak kindly and reassuringly, like a caring family doctor
- Use simple, easy-to-understand language (avoid heavy medical jargon)
- Always show empathy — patients may be worried or in pain
- Give practical, helpful general health guidance
- For serious symptoms (chest pain, breathing difficulty, stroke signs), always urge the user to seek emergency care immediately
- Never diagnose definitively — always recommend consulting a real doctor for serious concerns
- Keep responses concise but thorough

Start responses with a warm acknowledgment of what the patient said before giving advice.
"""


def get_ai_response(history: list[Message], user_message: str) -> str:
    """Build prompt from DB history and call the LLM."""
    messages_for_prompt = [("system", DOCTOR_SYSTEM_PROMPT)]

    for msg in history:
        role = "human" if msg.role == "human" else "ai"
        messages_for_prompt.append((role, msg.content))

    messages_for_prompt.append(("human", user_message))

    prompt = ChatPromptTemplate.from_messages(messages_for_prompt)
    chain = prompt | llm | output_parser
    return chain.invoke({})


# ─────────────────────────────────────────────
#  Pydantic Schemas
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "🏥 Medical Assistant Chatbot API is running!",
        "doctor":  "Dr. Aria — Your friendly AI health companion",
        "disclaimer": "For informational purposes only. Always consult a real doctor for medical decisions.",
        "docs": "/docs"
    }


# ── Users ─────────────────────────────────────

@app.post("/users", response_model=UserOut, tags=["Users"])
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new patient/user."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(name=data.name, email=data.email, age=data.age)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=list[UserOut], tags=["Users"])
def list_users(db: Session = Depends(get_db)):
    """List all registered users."""
    return db.query(User).all()


@app.get("/users/{user_id}", response_model=UserOut, tags=["Users"])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a single user's profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@app.delete("/users/{user_id}", tags=["Users"])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user and all their chat history."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user)
    db.commit()
    return {"message": f"User '{user.name}' and all their data deleted successfully."}


# ── Chat ──────────────────────────────────────

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Send a message to Dr. Aria.
    History is automatically loaded from PostgreSQL for context.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

    # Load this user's full history for context
    history = (
        db.query(Message)
        .filter(Message.user_id == request.user_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    try:
        ai_response = get_ai_response(history, request.message)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    # Save both messages to DB
    db.add(Message(user_id=request.user_id, role="human",  content=request.message))
    db.add(Message(user_id=request.user_id, role="ai",     content=ai_response))
    db.commit()

    turn = (len(history) + 2) // 2

    return ChatResponse(
        user_id=request.user_id,
        message=request.message,
        response=ai_response,
        turn=turn
    )


# ── History ───────────────────────────────────

@app.get("/users/{user_id}/history", response_model=HistoryResponse, tags=["History"])
def get_history(user_id: int, db: Session = Depends(get_db)):
    """Get the full conversation history for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return HistoryResponse(
        user_id=user_id,
        username=user.name,
        total=len(messages),
        messages=messages
    )


@app.delete("/users/{user_id}/history", tags=["History"])
def clear_history(user_id: int, db: Session = Depends(get_db)):
    """Clear all chat history for a user (keep the user account)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    deleted = db.query(Message).filter(Message.user_id == user_id).delete()
    db.commit()
    return {"message": f"Cleared {deleted} messages for user '{user.name}'."}


# ── Smart Endpoints ───────────────────────────

@app.post("/users/{user_id}/summarize", response_model=SummaryResponse, tags=["Smart"])
def summarize(user_id: int, db: Session = Depends(get_db)):
    """Ask Dr. Aria to summarize this user's medical conversation so far."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    history = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    if not history:
        raise HTTPException(status_code=400, detail="No chat history to summarize.")

    try:
        summary = get_ai_response(
            history,
            "Please summarize our medical conversation so far. List: main symptoms discussed, advice given, and any important warnings."
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    return SummaryResponse(user_id=user_id, summary=summary)


@app.get("/users/{user_id}/symptoms", tags=["Smart"])
def extract_symptoms(user_id: int, db: Session = Depends(get_db)):
    """Ask Dr. Aria to extract all symptoms the user has mentioned."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    history = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    if not history:
        raise HTTPException(status_code=400, detail="No chat history found.")

    try:
        result = get_ai_response(
            history,
            "Extract and list ONLY the symptoms and health complaints the patient mentioned in our conversation. Format as a clean bullet list. If none found, say so."
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    return {"user_id": user_id, "username": user.name, "symptoms_mentioned": result}


@app.post("/users/{user_id}/second-opinion", tags=["Smart"])
def second_opinion(user_id: int, db: Session = Depends(get_db)):
    """Ask Dr. Aria for a second opinion or deeper analysis of the conversation."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    history = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    if not history:
        raise HTTPException(status_code=400, detail="No chat history found.")

    try:
        opinion = get_ai_response(
            history,
            "Based on everything the patient shared, provide a deeper second-opinion analysis. Mention: possible conditions to explore, lifestyle suggestions, and when they should urgently see a real doctor."
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    return {
        "user_id": user_id,
        "username": user.name,
        "second_opinion": opinion,
        "reminder": "This is AI-generated. Always consult a licensed doctor."
    }