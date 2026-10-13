from fastapi import APIRouter
from datetime import datetime
from decimal import Decimal

from app.api.dependencies import ApiCheckReceiptDep, SessionDep, ApiLogsDep, ReceiptDep, ReceiptCompoundDep
from app.schemas import ReceiptBase

temp_const_admin_user = 20260308
router = APIRouter(tags=["receipt"])


@router.post("/create_receipt", status_code=201)
async def create_receipt(
        data: ReceiptBase,
        api_receipt: ApiCheckReceiptDep,
        api_logs: ApiLogsDep,
        session: SessionDep,
        receipt: ReceiptDep,
        receipt_compound: ReceiptCompoundDep,
) -> str:
    response = await api_receipt.check(raw_receipt=data.raw_receipt)
    await api_logs.logs_add(
        user_id=temp_const_admin_user,
        service="proverka_cheka_api",
        method="[POST]/api/v1/check/get",
        comment="Проверка чека",
        input_data=str(data.raw_receipt),
        output_data=str(response),
    )
    main_data = response["data"]["json"]
    receipt_object = await receipt.create(
        period=datetime.fromisoformat(main_data["dateTime"]),
        user_id=temp_const_admin_user,
        qrraw=data.raw_receipt,
        retail_place=main_data.get("retailPlace"),
        retail_place_address=main_data.get("retailPlaceAddress"),
        total_sum=Decimal(main_data.get("totalSum") / 100),
    )
    for item in main_data.get("items"):
        await receipt_compound.create(
            name=item["name"],
            receipt_id=receipt_object.id,
            user_id=temp_const_admin_user,
            group_id=44,
            vat=item["nds"],
            vat_sum=Decimal(item["ndsSum"]) / 100,
            price=Decimal(item["price"]) / 100,
            quantity=Decimal(item["quantity"]),
            sum=Decimal(item["sum"]) / 100,
        )
    await session.commit()

    return f"Чек успешно добавлен {receipt_object.id}"
