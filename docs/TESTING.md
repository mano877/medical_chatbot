# 🧪 Testing

Tests run against a **separate test database** never the real one.

```bash
# One-time: point the app at a test database before running tests
$env:DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/medical_chatbot_test"

pytest tests/ -v
```

## Safety check

`tests/conftest.py` refuses to run any test if the database name doesn't contain `"test"`:

```python
if "test" not in settings.database_url:
    raise RuntimeError("🚨 DANGER: Tests are about to run against a NON-TEST database!")
```

This exists because an earlier version of the test setup accidentally wiped the real development database when `DATABASE_URL` wasn't overridden correctly before running `pytest`. The check makes that mistake impossible to repeat.

## What's covered

- `tests/test_auth.py` registration (success case, response shape excludes sensitive fields) and login (returns a valid access token)

## Fixtures

- `client` — a `TestClient` instance for making requests against the app
- `clean_database` (autouse)  truncates all tables before every test, so each test starts from a clean slate