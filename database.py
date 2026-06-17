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
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://154.57.212.236:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages   = relationship("Message", back_populates="user", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role       = Column(String(10), nullable=False)   # "human" | "ai"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User", back_populates="messages")


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