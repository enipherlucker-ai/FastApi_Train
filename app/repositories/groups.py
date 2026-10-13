from sqlalchemy import select

from app.models import Group
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    model = Group

    async def get_by_name(self, name: str) -> Group | None:
        stmt = select(self.model).where(self.model.name == name)
        return await self.session.scalar(stmt)
