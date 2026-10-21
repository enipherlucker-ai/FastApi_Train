from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.user import router as users_router
from app.api.receipt import router as receipt_router
from app.api.auth import router as auth_router
from app.database import engine

from app.api.dependencies import get_openai_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
    if get_openai_client.cache_info().currsize:
        await get_openai_client().close()


app = FastAPI(lifespan=lifespan)
app.include_router(users_router)
app.include_router(receipt_router)
app.include_router(auth_router)