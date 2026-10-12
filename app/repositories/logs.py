from collections.abc import Sequence

from sqlalchemy import select

from app.models import ApiLogs
from app.repositories.base import BaseRepository


class ApiLogsRepository(BaseRepository[ApiLogs]):
    model = ApiLogs

    async def logs_add_user(self, input_data: str, output_data: str) -> None:
        obj = self.model(
            user_id=20260408,
            method="[POST]/create_user",
            comment="Добавление пользователя",
            input_data=input_data,
            output_data=output_data)
        self.session.add(obj)
        await self.session.flush()
