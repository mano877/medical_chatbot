# 📝 Changelog

## ChromaDB → Pinecone
Local vector storage doesn't survive restarts on ephemeral-filesystem hosts (e.g. Render free tier). Pinecone is cloud-persistent, so documents remain searchable across deploys.

## JSON metadata file → Postgres `documents` table
Same persistence reasoning as above — document listings (filename, upload date, status) now survive restarts too, instead of living in a local JSON file.

## PDF upload → background task
Previously blocked the request for 60–90+ seconds while embedding ran synchronously. Now `POST /documents/upload` returns instantly, and a background task handles embedding + Pinecone upload afterward. A `status` field (`processing` / `ready` / `failed`) tracks progress; chat's RAG lookup only searches documents with `status: "ready"`.

## Embeddings → batched
Switched from one `embed_query()` call per chunk to a single `embed_documents()` call per upload, cutting down redundant round-trips to the Ollama server.

## `/chat` → `user_id` fixed to come from JWT
Previously `user_id` was passed manually in the request body — a security issue, since anyone could type another user's ID and access their chat as them. Now it always comes from the JWT token. `conversation_id` remains a required field, since the frontend already has an explicit conversation switcher (sidebar + "+ New Chat" button) that needs to target a specific conversation, not just "the most recent one."

## Automated tests added
`tests/` with `pytest`, running against an isolated test database. `conftest.py` includes a safety check that refuses to run if the database name doesn't contain `"test"`, preventing accidental data loss against the real database.