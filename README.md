# 🏥 Medical Assistant Chatbot API — Dr. Aria

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-000000?style=flat&logo=chainlink&logoColor=white)

> Meet **Dr. Aria** — a warm, friendly AI medical assistant who remembers every patient's full conversation history.

> ⚠️ *For informational purposes only. Always consult a real doctor for medical decisions.*

---

## ⚙️ Setup with `uv`

```bash
# 1. Clone the repository
git clone https://github.com/YourUsername/medical-chatbot.git
cd medical-chatbot

# 2. Install dependencies
uv sync

# 3. Configure environment variables
cp .env.example .env
# Edit .env and set your PostgreSQL credentials

# 4. Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE medical_chatbot;"

# 5. Run the server
uv run uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000/docs** for the full interactive Swagger UI.

---

## 📡 All Endpoints

### 👤 Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users` | Register a new patient |
| `GET` | `/users` | List all patients |
| `GET` | `/users/{user_id}` | Get a patient's profile |
| `DELETE` | `/users/{user_id}` | Delete patient and all history |

### 💬 Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Chat with Dr. Aria (history auto-loaded from PostgreSQL) |

### 📜 History
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/{user_id}/history` | Get full conversation history |
| `DELETE` | `/users/{user_id}/history` | Clear history (keep account) |

### 🧠 Smart Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/users/{user_id}/summarize` | Summarize the medical conversation |
| `GET` | `/users/{user_id}/symptoms` | Extract all symptoms mentioned |
| `POST` | `/users/{user_id}/second-opinion` | Get a deeper AI analysis |

---

## 🔄 Example Usage

### 1. Register a Patient
```json
// POST /users
{
  "name": "zainab",
  "email": "zainab@email.com",
  "age": 28
}

// Response 201
{
  "id": 3,
  "name": "zainab",
  "email": "zainab@email.com",
  "age": 28,
  "created_at": "2026-06-17T10:00:00Z"
}
```

### 2. Chat with Dr. Aria
```json
// POST /chat
{
  "user_id": 1,
  "message": "I have a headache and fever since 2 days"
}

// Response 200
{
  "user_id": 1,
  "message": "I have a headache and fever since 2 days",
  "response": "I'm sorry to hear that! A headache with fever lasting 2 days could be due to a viral infection. Please rest, stay hydrated, and monitor your temperature. Are you experiencing any other symptoms like body aches or sore throat?",
  "turn": 1
}
```

### 3. Extract Symptoms
```json
// GET /users/1/symptoms

// Response 200
{
  "user_id": 3,
  "username": "zainab",
  "symptoms_mentioned": "• Headache\n• Fever (since 2 days)"
}
```

### 4. Get Second Opinion
```json
// POST /users/1/second-opinion

// Response 200
{
  "user_id": 3,
  "username": "zainab",
  "second_opinion": "Based on your symptoms...\n\n🔍 Possible conditions:\n- Viral fever\n- Flu\n\n🥗 Lifestyle suggestions:\n- Rest and hydrate\n- Light meals\n\n🚨 Go to ER if:\n- Fever crosses 103°F\n- Difficulty breathing",
  "reminder": "This is AI-generated. Always consult a licensed doctor."
}
```

---

## 🗄️ Database Schema

```
users
  id          → Primary key
  name        → Patient name
  email       → Unique email
  age         → Optional age
  created_at  → Registration time

messages
  id          → Primary key
  user_id     → Foreign key → users.id
  role        → "human" or "ai"
  content     → Message text
  created_at  → Message time
```

---

## 🔧 Configure Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+psycopg2://postgres:yourpassword@localhost:5432/medical_chatbot | PostgreSQL connection |
| OLLAMA_BASE_URL | http://your-ollama-server:11434 | Ollama server URL |
| OLLAMA_MODEL | llama3.1:latest | Model to use |

---

## ⚠️ Disclaimer
Dr. Aria is for **informational purposes only**. It does not replace professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.