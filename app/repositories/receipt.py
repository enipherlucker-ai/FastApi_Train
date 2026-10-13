from sqlalchemy import select

from app.models import Receipt, ReceiptCompound
from app.repositories.base import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    model = Receipt

    async def get_by_qrraw(self, user_id: int, qrraw: str) -> Receipt | None:
        stmt = select(self.model).where(self.model.user_id == user_id, self.model.qrraw == qrraw)
        return await self.session.scalar(stmt)


class ReceiptCompoundRepository(BaseRepository[ReceiptCompound]):
    model = ReceiptCompound
