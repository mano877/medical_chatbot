from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db, User, Message
from app.schemas import SummaryResponse
from app.services.ai_service import get_ai_response

router = APIRouter(prefix="/users", tags=["Smart"])


@router.post("/{user_id}/summarize", response_model=SummaryResponse)
def summarize(user_id: int, db: Session = Depends(get_db)):
    """Ask Dr. Aria to summarize this user's medical conversation."""
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


@router.get("/{user_id}/symptoms")
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
            "Extract and list ONLY the symptoms and health complaints the patient mentioned. Format as a clean bullet list. If none found, say so."
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {str(e)}")

    return {"user_id": user_id, "username": user.name, "symptoms_mentioned": result}


@router.post("/{user_id}/second-opinion")
def second_opinion(user_id: int, db: Session = Depends(get_db)):
    """Ask Dr. Aria for a deeper analysis of the conversation."""
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