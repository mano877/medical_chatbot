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
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "paste URL here")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Pinecone
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "medical-chatbot")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")

    # lowercase aliases so both styles work across the codebase
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def ollama_base_url(self) -> str:
        return self.OLLAMA_BASE_URL

    @property
    def pinecone_api_key(self) -> str:
        return self.PINECONE_API_KEY

    @property
    def pinecone_index_name(self) -> str:
        return self.PINECONE_INDEX_NAME

    @property
    def pinecone_environment(self) -> str:
        return self.PINECONE_ENVIRONMENT


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
    documents  = relationship("Document", back_populates="user", cascade="all, delete-orphan")


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


class Document(Base):
    """Tracks uploaded PDF documents. Actual vectors live in Pinecone —
    this table just tracks WHICH documents exist, so listing/deleting
    survives server restarts (unlike a local JSON file)."""
    __tablename__ = "documents"

    id          = Column(Integer, primary_key=True, index=True)
    doc_id      = Column(String(64), unique=True, nullable=False, index=True)
    filename    = Column(String(255), nullable=False)
    chunks      = Column(Integer, nullable=False, default=0)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), nullable=False, default="processing")
    user        = relationship("User", back_populates="documents")
   


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