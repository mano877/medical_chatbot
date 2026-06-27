from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import create_tables
from app.routers import users, chat, smart, documents


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
#  Routers
# ─────────────────────────────────────────────
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(smart.router)
app.include_router(documents.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "🏥 Medical Assistant Chatbot API is running!",
        "doctor": "Dr. Aria — Your friendly AI health companion",
        "disclaimer": "For informational purposes only. Always consult a real doctor.",
        "docs": "/docs"
    }