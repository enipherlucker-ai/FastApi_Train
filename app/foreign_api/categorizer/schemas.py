from pydantic import BaseModel


class ItemGroup(BaseModel):
    index: int
    group_id: int


class Categorization(BaseModel):
    items: list[ItemGroup]