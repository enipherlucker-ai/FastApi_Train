from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATABASE_URL, DB_ECHO

# Engine — одно на всё приложение: хранит адрес базы и пул подключений.
engine = create_async_engine(DATABASE_URL, echo=DB_ECHO)

# Фабрика сессий: каждый вызов session_factory() даёт новую сессию.
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Одна сессия на один HTTP-запрос. После ответа сессия закрывается."""
    async with session_factory() as session:
        yield session
