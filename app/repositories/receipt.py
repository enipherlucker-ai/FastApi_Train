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
    async def known_groups(self, user_id: int, names: list[str], exclude_group_id: int) -> dict[str, int]:
        stmt = (
            select(self.model.name, self.model.group_id)
            .where(
                self.model.user_id == user_id,
                self.model.name.in_(names),
                self.model.group_id != exclude_group_id,
            )
            .order_by(self.model.id)
        )
        result = await self.session.execute(stmt)
        return {name: group_id for name, group_id in result}
