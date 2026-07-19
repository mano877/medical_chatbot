# 🏥 Medical Assistant Chatbot API — Dr. Aria

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-000000?style=flat&logo=chainlink&logoColor=white)

> Meet **Dr. Aria** — a warm, friendly AI medical assistant with authenticated, per-patient chat sessions, document-grounded answers (RAG), and AI-generated insights.

> ⚠️ *For informational purposes only. Always consult a real doctor for medical decisions.*

A React frontend for this API is available separately see [medical-chatbot-frontend](../medical-chatbot-frontend).

---

## ⚙️ Setup with `uv`

```bash
git clone <this-repo-url>
cd medical-chatbot

uv sync

cp .env.example .env
# Edit .env — see Environment Variables below

psql -U postgres -c "CREATE DATABASE medical_chatbot;"

uv run uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the full interactive Swagger UI (supports pasting a Bearer token via the Authorize button for testing protected routes).

---

## 🔐 Authentication

All patient data endpoints require a JWT access token.

1. `POST /users` — sign up (name, email, age, password — password is hashed with bcrypt, never stored in plain text)
2. `POST /users/login` — log in with email + password, returns `{ access_token, user_id }`
3. Pass the token on every subsequent request: `Authorization: Bearer <access_token>`

Every protected endpoint checks both that the token is valid **and** that the token's user matches the resource being requested (e.g. you cannot fetch or modify another patient's chat, history, or documents even with a valid token).

---

## 📡 Endpoints

### 👤 Users
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/users` | — | Register a new patient |
| `POST` | `/users/login` | — | Log in, get a JWT |
| `GET` | `/users/{user_id}` | 🔒 self | Get your own profile |
| `DELETE` | `/users/{user_id}` | 🔒 self | Delete your own account + all data |

### 💬 Chat & Conversations
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/chat` | 🔒 | Send a message within a conversation (requires `conversation_id`) |
| `POST` | `/conversations` | 🔒 | Start a new conversation |
| `GET` | `/conversations` | 🔒 | List your conversations, newest first |
| `GET` | `/conversations/{id}/messages` | 🔒 | Get all messages in one conversation |
| `DELETE` | `/conversations/{id}` | 🔒 | Delete a conversation and all its messages |
| `DELETE` | `/messages/{message_id}` | 🔒 | Delete a single message |

### 📜 History (legacy full-history view)
| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/users/{user_id}/history` | 🔒 self |
| `DELETE` | `/users/{user_id}/history` | 🔒 self |

### 🧠 Smart Analysis
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/users/{user_id}/summarize` | 🔒 self | Summarize the conversation |
| `GET` | `/users/{user_id}/symptoms` | 🔒 self | Extract mentioned symptoms |
| `POST` | `/users/{user_id}/second-opinion` | 🔒 self | Deeper AI analysis |

### 📄 Documents (RAG)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/documents/upload` | 🔒 | Upload a PDF (lab report, prescription, guideline) |
| `GET` | `/documents` | 🔒 | List your own uploaded documents |
| `DELETE` | `/documents/{id}` | 🔒 | Delete your own document |

Documents are private per patient — both the vector store and the metadata tracker tag every chunk/document with the uploading patient's `user_id`, and RAG search is filtered accordingly, so Dr. Aria never surfaces one patient's documents to another.

---

## 🗄️ Database Schema

```
users
  id, name, email, age, hashed_password, created_at

conversations
  id, user_id → users.id, title, created_at

messages
  id, user_id → users.id, conversation_id → conversations.id (nullable, legacy),
  role ("human" | "ai"), content, created_at
```

One user → many conversations → many messages. Deleting a user or conversation cascades to delete its dependents.

---

## 🧠 AI / RAG Architecture

```
Uploaded PDF  ──►  PyPDFLoader  ──►  Text Splitter  ──►  Ollama Embeddings  ──►  ChromaDB
                                                          (tagged with user_id)

User Question ──►  Hybrid Search (Vector + BM25, filtered to user_id)  ──►  RRF re-ranking
                                                                          ──►  Context injected
                                                                              into Dr. Aria's prompt
```

- **Chat LLM:** [Groq](https://console.groq.com) (`langchain-groq`, model `llama-3.3-70b-versatile`) — fast, free-tier cloud inference. Swapped in from an initial Ollama-based setup for speed; Ollama config is retained as a fallback (see Environment Variables).
- **Embeddings:** Ollama `nomic-embed-text` / `qwen3-embedding` (still used for RAG regardless of chat LLM choice)
- **Vector DB:** ChromaDB (local, `chroma_db/`)
- **Search:** Hybrid — vector similarity + BM25 keyword search, combined via Reciprocal Rank Fusion
- **Chunking:** RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
- **Prompt safety:** user/document text is brace-escaped before insertion into the LangChain prompt template, to prevent crashes from stray `{`/`}` characters in uploaded PDFs
- **System prompt rules:** stays in medical scope (declines fully unrelated requests, still answers health-adjacent ones like diet questions), only references uploaded documents when relevant, adds a disclaimer when answering from general knowledge, urges emergency care for serious symptoms, never diagnoses definitively, responds warmly and concisely

---

## 🔧 Environment Variables

| Variable | Default | Description |
|----------|---------|--------------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:yourpassword@localhost:5432/medical_chatbot` | PostgreSQL connection |
| `GROQ_API_KEY` | — | Your Groq API key (get one free at console.groq.com) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq chat model |
| `OLLAMA_BASE_URL` | — | Ollama server URL (fallback; only used if you switch `ai_service.py` back to `ChatOllama`) |
| `OLLAMA_MODEL` | `llama3.1:latest` | Ollama model (fallback) |

**JWT settings** (currently hardcoded in `app/utils/security.py`, recommended to move into `.env` before any real deployment):
- `SECRET_KEY` — signing key for tokens (**must** be changed from the placeholder before production use)
- Token expiry: 24 hours

---

## ⚠️ Disclaimer
Dr. Aria is for **informational purposes only**. It does not replace professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.