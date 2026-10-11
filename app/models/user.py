from sqlalchemy import CheckConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Строка таблицы payment_statistic.users в виде Python-объекта."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("age >= 0", name="users_age_check"),
        {"schema": "payment_statistic"},
    )

    name: Mapped[str] = mapped_column(Text)
    age: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, age={self.age!r})"
