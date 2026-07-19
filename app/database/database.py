from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from sqlalchemy.sql import func
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


# ─────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:yourpassword@localhost:5432/medical_chatbot")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "patste URL here")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

settings = Settings()


# ─────────────────────────────────────────────
#  SQLAlchemy Setup
# ─────────────────────────────────────────────
engine = create_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
#  Models
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(150), unique=True, nullable=False)
    age        = Column(Integer, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    messages   = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title      = Column(String(100), nullable=False, default="New Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User", back_populates="conversations")
    messages   = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")    


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String(10), nullable=False)   # "human" | "ai"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User", back_populates="messages")
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


# ─────────────────────────────────────────────
#  DB dependency for FastAPI
# ─────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)