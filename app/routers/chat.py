from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db, User, Message
from app.database.schemas import ChatRequest, ChatResponse, MessageOut, HistoryResponse
from app.services.ai_service import get_ai_response

router = APIRouter(tags=["Chat & History"])


# ── Chat ──────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to Dr. Aria. History is automatically loaded from PostgreSQL."""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")

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

    db.add(Message(user_id=request.user_id, role="human", content=request.message))
    db.add(Message(user_id=request.user_id, role="ai",    content=ai_response))
    db.commit()

    turn = (len(history) + 2) // 2

    return ChatResponse(
        user_id=request.user_id,
        message=request.message,
        response=ai_response,
        turn=turn
    )


# ── History ───────────────────────────────────

@router.get("/users/{user_id}/history", response_model=HistoryResponse)
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


@router.delete("/users/{user_id}/history")
def clear_history(user_id: int, db: Session = Depends(get_db)):
    """Clear all chat history for a user (keep the user account)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    deleted = db.query(Message).filter(Message.user_id == user_id).delete()
    db.commit()
    return {"message": f"Cleared {deleted} messages for user '{user.name}'."}