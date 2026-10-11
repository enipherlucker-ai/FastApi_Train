from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Общие операции для любой таблицы. Наследник задаёт только model.

    Репозиторий не делает commit: он кладёт изменения в сессию и вызывает
    flush, а зафиксировать транзакцию решает тот, кто открыл сессию.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt = select(self.model).order_by(self.model.id).limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return result.all()

    async def create(self, **values: Any) -> ModelT:
        obj = self.model(**values)
        self.session.add(obj)
        await self.session.flush()  # INSERT уходит в базу, у obj появляется id
        return obj

    async def update(self, obj: ModelT, **values: Any) -> ModelT:
        for field, value in values.items():
            setattr(obj, field, value)
        await self.session.flush()  # UPDATE только изменённых колонок
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
