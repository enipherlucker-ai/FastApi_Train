from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

RawReceipt = Annotated[str, Field(examples=["t=20261010T2119&s=5099.62&fn=7380440903609803&i=22385&fp=3751356996&n=1"])]


class ReceiptBase(BaseModel):
    name: RawReceipt