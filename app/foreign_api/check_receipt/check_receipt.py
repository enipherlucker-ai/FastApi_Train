import httpx

from app.foreign_api.check_receipt.errors import CheckReceiptUnavailableError, ReceiptNotFoundError


class CheckReceipt:
    CHECK_PATH = "/api/v1/check/get"

    def __init__(self, api_token: str, url: str, timeout: int) -> None:
        self.api_token = api_token
        self.url = url
        self.timeout = timeout

    async def check(self, raw_receipt: str) -> dict:
        payload = {"token": self.api_token, "qrraw": raw_receipt}
        url = f"{self.url}{self.CHECK_PATH}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CheckReceiptUnavailableError(str(exc)) from exc

        result = response.json()
        if result.get("code") != 1:
            raise ReceiptNotFoundError(str(result.get("data")))
        return result
