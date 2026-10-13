from app.models import Receipt, ReceiptCompound
from app.repositories.base import BaseRepository


class ReceiptRepository(BaseRepository[Receipt]):
    model = Receipt

class ReceiptCompoundRepository(BaseRepository[ReceiptCompound]):
    model = ReceiptCompound