from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.user import router as users_router
from app.api.receipt import router as receipt_router
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(users_router)
app.include_router(receipt_router)