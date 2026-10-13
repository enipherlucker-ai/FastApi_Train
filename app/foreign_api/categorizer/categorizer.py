import json

import openai
from openai import AsyncOpenAI

from app.foreign_api.categorizer.errors import CategorizerError
from app.foreign_api.categorizer.schemas import Categorization

SYSTEM_PROMPT = """Ты раскладываешь товары из кассового чека по группам расходов.
Тебе дают JSON с двумя списками: groups (id, name, description) и items (index, name).
Для каждого товара из items выбери ровно одну группу и верни её id вместе с index товара.
Используй только id из списка groups. Если не уверен, выбери группу «Другое»."""

class ReceiptCategorizer:
    def __init__(self, client : AsyncOpenAI, model: str) -> None:
        self.client = client
        self.model = model

    async def categorize(self, names: list[str], groups: list[dict]) -> Categorization:
        user_content = json.dumps(
            {
                "groups": groups,
                "items": [{"index": i, "name": name} for i, name in enumerate(names)],
            },
            ensure_ascii=False
        )
        try:
            completion = await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=Categorization,
            )
        except openai.OpenAIError as exc:
            raise CategorizerError(str(exc)) from exc

        result = completion.choices[0].message.parsed
        if result is None:
            raise CategorizerError("Модель не вернула ответ")
        return result
