import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db",
)

DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
