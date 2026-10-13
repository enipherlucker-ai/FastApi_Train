import httpx
from app.foreign_api.check_receipt.errors import STATUS_ERRORS

class CheckReceipt:
    def __init__(self, api_token:str, url: str, timeout: int) -> None:
        self.api_token = api_token
        self.url = url
        self.timeout = timeout

    @staticmethod
    def _check_response(response: httpx.Response) -> httpx.Response:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_class = STATUS_ERRORS.get(exc.response.status_code)

            if error_class is None:
                raise

            raise error_class(
                str(exc),
                request=exc.request,
                response=exc.response,
            ) from exc
        return response

    async def check(self, raw_receipt: str) -> dict:
        payload = {"token": self.api_token, "qrraw": raw_receipt}
        url = f"{self.url}/api/v1/check/get"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=self.timeout)
        self._check_response(response)
        return response.json()



