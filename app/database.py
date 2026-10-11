from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import DATABASE_URL, DB_ECHO

engine = create_async_engine(DATABASE_URL, echo=DB_ECHO)

session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session