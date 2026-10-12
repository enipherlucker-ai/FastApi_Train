from app.models import ApiLogs
from app.repositories.base import BaseRepository


class ApiLogsRepository(BaseRepository[ApiLogs]):
    model = ApiLogs

    async def logs_add(
            self, user_id: int, service: str, method: str, comment: str, input_data: str, output_data: str
    ) -> None:
        obj = self.model(
            user_id=user_id,
            service=service,
            method=method,
            comment=comment,
            input_data=input_data,
            output_data=output_data)
        self.session.add(obj)
        await self.session.flush()
