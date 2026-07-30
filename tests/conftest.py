import os

# Set test database URL BEFORE importing the app
TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres1b9@localhost:5432/medical_chatbot_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.database.database import engine, create_tables, settings

# ── SAFETY CHECK ──────────────────────────────────────────────────────
# Refuse to run ANY test if the database URL doesn't contain "test"
if "test" not in settings.database_url:
    raise RuntimeError(
        f"\n\n🚨 DANGER: Tests are about to run against a NON-TEST database!\n"
        f"Current DATABASE_URL: {settings.database_url}\n"
        f"Database name must contain 'test' to proceed.\n"
        f"Tests aborted to protect your real data.\n"
    )

create_tables()


@pytest.fixture(autouse=True)
def clean_database():
    """Wipes all data before every test so each test starts clean."""
    with engine.connect() as conn:
        conn.execute(text(
            "TRUNCATE TABLE messages, conversations, documents, users RESTART IDENTITY CASCADE;"
        ))
        conn.commit()
    yield


@pytest.fixture
def client():
    return TestClient(app)