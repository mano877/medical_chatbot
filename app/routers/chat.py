from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.utils.security import get_current_user

from app.database.database import get_db, User, Message, Conversation
from app.database.schemas import ChatRequest, ChatResponse, MessageOut, HistoryResponse, ConversationOut
from app.services.ai_service import get_ai_response
from app.services.rag_service import get_rag_context

router = APIRouter(tags=["Chat & History"])


# ── Chat ──────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Send a message to Dr. Aria. History is automatically loaded from PostgreSQL."""
    if request.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only chat as yourself.")

    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    conversation = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
    if not conversation or conversation.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Invalid conversation.")

    history = (
        db.query(Message)
        .filter(Message.user_id == request.user_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # Retrieve RAG context from uploaded medical documents (if any)
    # Gracefully degrade to non-RAG if the vector store is unreachable
    try:
        rag_context = get_rag_context(request.message, current_user_id)
    except Exception:
        rag_context = None  # fall back to standard Dr. Aria response

    try:
        ai_response = get_ai_response(history, request.message, rag_context=rag_context)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    db.add(Message(user_id=request.user_id, role="human", content=request.message, conversation_id=request.conversation_id))
    db.add(Message(user_id=request.user_id, role="ai",    content=ai_response, conversation_id=request.conversation_id))
    db.commit()

    turn = (len(history) + 2) // 2

    return ChatResponse(
        user_id=request.user_id,
        message=request.message,
        response=ai_response,
        turn=turn
    )

# ── Conversations ─────────────────────────────

@router.post("/conversations", response_model=ConversationOut)
def create_conversation(db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Start a new chat conversation."""
    conversation = Conversation(user_id=current_user_id, title="New Chat")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """List all conversations for the logged-in user, newest first."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user_id)
        .order_by(Conversation.created_at.desc())
        .all()
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Get all messages in one conversation."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conversation.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only view your own conversations.")

    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

@router.delete("/messages/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Delete a single message."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")
    if message.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own messages.")

    db.delete(message)
    db.commit()
    return {"message": "Message deleted successfully."}

@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conversation.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own conversations.")

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted successfully."}

# ── History ───────────────────────────────────

@router.get("/users/{user_id}/history", response_model=HistoryResponse)
def get_history(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Get the full conversation history for a user."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only view your own history.")

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
def clear_history(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Clear all chat history for a user (keep the user account)."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only clear your own history.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    deleted = db.query(Message).filter(Message.user_id == user_id).delete()
    db.commit()
    return {"message": f"Cleared {deleted} messages for user '{user.name}'."}