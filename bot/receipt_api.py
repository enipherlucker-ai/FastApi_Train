import httpx


class ReceiptApiError(Exception):
    """Базовая ошибка API чеков. Текст можно показать пользователю."""


class ApiUnavailableError(ReceiptApiError):
    pass


class ReceiptDuplicateError(ReceiptApiError):
    pass


class ReceiptRejectedError(ReceiptApiError):
    pass


class ReceiptApi:
    def __init__(self, url: str, timeout: int, client: httpx.AsyncClient) -> None:
        self.url = url
        self.timeout = timeout
        self.client = client

    async def create_receipt(self, raw_receipt) -> int:
        try:
            response = await self.client.post(
                url=f"{self.url}/create_receipt",
                json={"raw_receipt": raw_receipt},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise ApiUnavailableError(f"API недоступно ({type(exc).__name__})") from exc

        if response.status_code == 201:
            return response.json()["id"]
        if response.status_code == 409:
            raise ReceiptDuplicateError("Этот чек уже добавлен")

        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = response.text
        raise ReceiptRejectedError(f"API ответило {response.status_code}: {detail}")