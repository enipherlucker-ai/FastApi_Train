from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.users import router as users_router
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Приложение останавливается — закрываем все подключения из пула.
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(users_router)
