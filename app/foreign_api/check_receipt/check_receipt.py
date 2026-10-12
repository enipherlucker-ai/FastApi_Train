import httpx

class CheckReceipt:
    def __init__(self, api_token:str, url: str, timeout: int) -> None:
        self.api_token = api_token
        self.url = url
        self.timeout = timeout

    async def check(self, raw_receipt: str) -> dict:
        payload = {"token": self.api_token, "qrraw": raw_receipt}
        url = f"{self.url}/api/v1/check/get"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()



