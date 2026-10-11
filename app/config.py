import os

# Адрес базы. В Docker его задаёт compose.yaml (хост pg_database),
# а при запуске на компьютере берётся значение по умолчанию (хост 127.0.0.1).
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:secret@127.0.0.1:5432/pg_test_db",
)

# DB_ECHO=true — печатать в лог каждый SQL-запрос, который отправляет SQLAlchemy.
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
