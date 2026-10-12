from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiLogs(Base):
    __tablename__ = "api_logs"
    __table_args__ = {"schema": "logs"},

    service: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey('payment_statistic.users.id'))
    method: Mapped[str] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    input_data: Mapped[str] = mapped_column(Text)
    output_data: Mapped[str] = mapped_column(Text)


    def __repr__(self):
        return (
            f"ApiLogs(id={self.id!r}, "
            f"id_user={self.user_id!r}, method={self.method!r})"
        )
