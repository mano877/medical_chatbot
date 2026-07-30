# 🧠 Architecture

## RAG Pipeline

```
Uploaded PDF ──► PyPDFLoader ──► Text Splitter ──► Ollama Embeddings (batched)
                                                              │
                          (background task, non-blocking)    ▼
                                                        Pinecone (tagged with user_id)
                                                        + Postgres `documents` row (status tracking)

User Question ──► Hybrid Search (Vector + BM25, filtered to user_id) ──► RRF re-ranking
                                                                       ──► Context injected
                                                                           into Dr. Aria's prompt
```

- **Chat LLM:** [Groq](https://console.groq.com) (`langchain-groq`, model `llama-3.3-70b-versatile`) — fast, free-tier cloud inference.
- **Embeddings:** Ollama `qwen3-embedding`, embedded in a single batched call per upload (`embed_documents`) rather than one call per chunk.
- **Vector DB:** Pinecone (cloud-hosted, serverless) — chosen over ChromaDB because local file storage doesn't survive restarts/redeploys on platforms with ephemeral filesystems (e.g. Render free tier).
- **Document metadata:** stored in Postgres, not a local JSON file, for the same persistence reason.
- **PDF processing:** runs as a FastAPI background task — upload returns instantly; embedding (the slow step, ~1–1.5 min for a typical document) happens after the response is sent.
- **Search:** Hybrid — vector similarity (Pinecone) + BM25 keyword search over the vector-search candidates, combined via Reciprocal Rank Fusion.
- **Chunking:** RecursiveCharacterTextSplitter (1000 chars, 200 overlap).
- **Prompt safety:** user/document text is brace-escaped before insertion into the LangChain prompt template.
- **System prompt rules:** stays in medical scope, only references uploaded documents when relevant, adds a disclaimer when answering from general knowledge, urges emergency care for serious symptoms, never diagnoses definitively.

---

## Chat Routing

`POST /chat` request body:
```json
{ "message": "...", "conversation_id": 5 }
```

- `user_id` comes from the JWT token — never passed by the client (this was a security fix: previously the client sent its own `user_id`, meaning anyone could type a different user's ID and act as them).
- `conversation_id` is required and must belong to the authenticated user. The frontend manages this explicitly: a "+ New Chat" button calls `POST /conversations` to create one, and a sidebar lets the user pick any past conversation to continue — its `id` is then sent on `/chat` calls.

---

## Database Schema

```
users
  id, name, email, age, hashed_password, created_at

conversations
  id, user_id → users.id, title, created_at

messages
  id, user_id → users.id, conversation_id → conversations.id (nullable, legacy),
  role ("human" | "ai"), content, created_at

documents
  id, doc_id (matches Pinecone vector id prefix), filename, chunks,
  status ("processing" | "ready" | "failed"), user_id → users.id, uploaded_at
```

One user → many conversations → many messages, and → many documents. Deleting a user or conversation cascades to delete its dependents. The `documents` table tracks metadata only — actual vector embeddings live in Pinecone.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|--------------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:yourpassword@localhost:5432/medical_chatbot` | PostgreSQL connection (e.g. Neon for cloud deployment) |
| `GROQ_API_KEY` | — | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq chat model |
| `OLLAMA_BASE_URL` | — | Ollama server URL (used for embeddings) |
| `OLLAMA_MODEL` | `llama3.1:latest` | Ollama model (fallback, unused while Groq is the chat LLM) |
| `PINECONE_API_KEY` | — | Your Pinecone API key |
| `PINECONE_INDEX_NAME` | `medical-chatbot` | Pinecone index name (auto-created if missing) |
| `PINECONE_ENVIRONMENT` | `us-east-1` | Pinecone serverless region |

**JWT settings** (currently hardcoded in `app/utils/security.py`, recommended to move into `.env` before production):
- `SECRET_KEY` — signing key for tokens (must be changed from placeholder)
- Token expiry: 24 hours