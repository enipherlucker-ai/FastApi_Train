from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Receipt(Base):
    __tablename__ = "receipt"
    __table_args__ = {"schema": "payment_statistic"}

    period: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("payment_statistic.users.id"), nullable=False)
    qrraw: Mapped[str | None] = mapped_column(Text)
    retail_place: Mapped[str | None] = mapped_column(Text)
    retail_place_address: Mapped[str | None] = mapped_column(Text)
    total_sum: Mapped[Decimal] = mapped_column(Numeric(8, 2))

    def __repr__(self) -> str:
        return (
            f"Receipt(id={self.id!r}, "
            f"period={self.period!r}, "
            f"id_user={self.user_id!r}, "
            f"total_sum={self.total_sum!r})"
        )


class ReceiptCompound(Base):
    __tablename__ = "receipt_compound"
    __table_args__ = {"schema": "payment_statistic"}

    name: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_id: Mapped[int] = mapped_column(Integer, ForeignKey("payment_statistic.receipt.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("payment_statistic.users.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("payment_statistic.groups.id"), nullable=False)
    vat: Mapped[int] = mapped_column(Integer, nullable=False)
    vat_sum: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    sum: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    def __repr__(self) -> str:
        return (
            f"ReceiptCompound(receipt_id={self.receipt_id!r}, "
            f"name={self.name!r}, "
            f"user_id={self.user_id!r}, "
            f"price={self.price!r}, "
            f"quantity={self.quantity!r}, "
            f"sum={self.sum!r})"
        )
