from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Общий предок всех моделей. Через него SQLAlchemy знает обо всех таблицах."""

    # У каждой таблицы проекта есть целочисленный первичный ключ id.
    id: Mapped[int] = mapped_column(primary_key=True)
