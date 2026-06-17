# 🏥 Medical Assistant Chatbot API

**FastAPI + LangChain + Ollama + PostgreSQL**

> Meet **Dr. Aria** — a warm, friendly AI medical assistant who remembers every patient's conversation history.

---

## ⚙️ Setup with `uv`

```bash
# 1. Create and sync environment
uv sync

# 2. Configure your .env
# Edit .env and set your PostgreSQL credentials

# 3. Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE medical_chatbot;"

# 4. Run the server
uv run uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** to see the full interactive Swagger UI.

---

## 📡 All Endpoints

### 👤 Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users` | Register a new patient |
| `GET` | `/users` | List all patients |
| `GET` | `/users/{user_id}` | Get a patient's profile |
| `DELETE` | `/users/{user_id}` | Delete patient + all history |

### 💬 Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Chat with Dr. Aria (history auto-loaded) |

### 📜 History
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/{user_id}/history` | Get full conversation history |
| `DELETE` | `/users/{user_id}/history` | Clear history (keep account) |

### 🧠 Smart Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users/{user_id}/summarize` | Summarize the medical conversation |
| `GET` | `/users/{user_id}/symptoms` | Extract all symptoms mentioned |
| `POST` | `/users/{user_id}/second-opinion` | Get a deeper AI analysis |

---

## 🔄 Typical Flow

```
1. Register → POST /users
             {"name": "Eman", "email": "eman@email.com", "age": 28}
             ← gets user_id = 1

2. Chat     → POST /chat
             {"user_id": 1, "message": "I have a headache and fever since 2 days"}
             ← Dr. Aria responds warmly with advice

3. Continue → POST /chat
             {"user_id": 1, "message": "The fever is around 101°F"}
             ← Dr. Aria remembers the headache from before!

4. Summary  → POST /users/1/summarize
             ← Bullet-point summary of everything discussed

5. Symptoms → GET /users/1/symptoms
             ← Clean list: headache, fever (101°F)

6. Analysis → POST /users/1/second-opinion
             ← Deeper analysis + when to see a real doctor
```

---

## 🗄️ Database Schema

```
users
  id, name, email, age, created_at

messages
  id, user_id (FK), role (human|ai), content, created_at
```

---

## ⚠️ Disclaimer
Dr. Aria is for **informational purposes only**. It does not replace professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.