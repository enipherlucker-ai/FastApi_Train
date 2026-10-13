from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = {"schema": "payment_statistic"}

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('payment_statistic.users.id'))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)

    def __repr__(self):
        return f"Group(id={self.id!r}, created_by={self.user_id!r}, name={self.name!r})"
