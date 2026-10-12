from fastapi import APIRouter

from app.api.dependencies import ApiCheckReceiptDep, SessionDep, ApiLogsDep
from app.schemas import ReceiptBase

router = APIRouter(tags=["receipt"])

@router.post("/create_receipt", status_code=201)
async def create_receipt(
        data: ReceiptBase,
        api_receipt: ApiCheckReceiptDep,
        api_logs: ApiLogsDep,
        session: SessionDep
)-> None:
    response = api_receipt.check(raw_receipt=data.raw_receipt)
    api_logs.logs_add(
        user_id=20260408,
        service="proverka_cheka_api",
        method="[POST]/api/v1/check/get",
        comment="Проверка чека",
        input_data=str(data.raw_receipt),
        output_data=str(response),
    )
    main_data = response["data"]["json"]
    await session.add(

    )