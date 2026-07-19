from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db, User
from app.database.schemas import UserCreate, UserOut, LoginRequest, Token
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user 

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserOut)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new patient/user."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        name=data.name,
        email=data.email,
        age=data.age,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Log in with email and password, get an access token."""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id)
    return Token(access_token=token, user_id=user.id)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Get a single user's profile."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    """Delete your own account and all your chat history."""
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user)
    db.commit()
    return {"message": f"User '{user.name}' and all their data deleted successfully."}
    