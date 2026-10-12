from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

class Receipt(Base):
    __tablename__ = "receipt"
    __table_args__ = {"schema": "payment_statistic"}

    period: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )
    id_user: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("payment_statistic.users.id"),
    )
    qrraw: Mapped[str | None] = mapped_column(Text)
    retail_place: Mapped[str | None] = mapped_column(Text)
    retail_place_address: Mapped[str | None] = mapped_column(Text)
    total_sum: Mapped[float] = mapped_column(Float)

    def __repr__(self) -> str:
        return (
            f"Receipt(id={self.id!r}, "
            f"period={self.period!r}, "
            f"id_user={self.id_user!r}, "
            f"total_sum={self.total_sum!r})"
        )

class ReceiptCompound(Base):
    __tablename__ = "receipt_compound"
    __table_args__ = {"schema": "payment_statistic"}

    receipt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("payment_statistic.receipts.id"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("payment_statistic.users.id"),
        primary_key=True,
    )
    vat: Mapped[float] = mapped_column(Float)
    vat_sum: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    sum: Mapped[float] = mapped_column(Float)

    def __repr__(self) -> str:
        return (
            f"ReceiptCompound(receipt_id={self.receipt_id!r}, "
            f"user_id={self.user_id!r}, "
            f"price={self.price!r}, "
            f"quantity={self.quantity!r}, "
            f"sum={self.sum!r})"
        )