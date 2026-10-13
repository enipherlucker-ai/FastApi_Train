import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app.api.dependencies import (
    ApiCheckReceiptDep,
    ApiLogsDep,
    GroupRepoDep,
    ReceiptCompoundDep,
    ReceiptDep,
    SessionDep,
)
from app.constants import ADMIN_USER_ID, DEFAULT_GROUP_NAME
from app.foreign_api.check_receipt import CheckReceipt, CheckReceiptUnavailableError, ReceiptNotFoundError
from app.schemas import ReceiptBase, ReceiptCreated

router = APIRouter(tags=["receipt"])


def kopecks_to_rubles(value: int) -> Decimal:
    return Decimal(value) / 100


@router.post("/create_receipt", response_model=ReceiptCreated, status_code=201)
async def create_receipt(
        data: ReceiptBase,
        api_receipt: ApiCheckReceiptDep,
        api_logs: ApiLogsDep,
        session: SessionDep,
        receipt: ReceiptDep,
        receipt_compound: ReceiptCompoundDep,
        groups: GroupRepoDep,
) -> ReceiptCreated:
    if await receipt.get_by_qrraw(ADMIN_USER_ID, data.raw_receipt) is not None:
        raise HTTPException(status_code=409, detail="Этот чек уже добавлен")

    try:
        response = await api_receipt.check(raw_receipt=data.raw_receipt)
    except ReceiptNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Чек не найден: {exc}") from exc
    except CheckReceiptUnavailableError as exc:
        raise HTTPException(status_code=502, detail="Сервис проверки чеков недоступен") from exc

    await api_logs.logs_add(
        user_id=ADMIN_USER_ID,
        service="proverka_cheka_api",
        method=f"[POST]{CheckReceipt.CHECK_PATH}",
        comment="Проверка чека",
        input_data=data.raw_receipt,
        output_data=json.dumps(response, ensure_ascii=False),
    )

    default_group = await groups.get_by_name(DEFAULT_GROUP_NAME)
    if default_group is None:
        raise HTTPException(status_code=500, detail=f"Нет группы «{DEFAULT_GROUP_NAME}» в базе")

    main_data = response["data"]["json"]
    receipt_object = await receipt.create(
        period=datetime.fromisoformat(main_data["dateTime"]),
        user_id=ADMIN_USER_ID,
        qrraw=data.raw_receipt,
        retail_place=main_data.get("retailPlace"),
        retail_place_address=main_data.get("retailPlaceAddress"),
        total_sum=kopecks_to_rubles(main_data["totalSum"]),
    )
    for item in main_data["items"]:
        await receipt_compound.create(
            name=item["name"],
            receipt_id=receipt_object.id,
            user_id=ADMIN_USER_ID,
            group_id=default_group.id,
            vat=item["nds"],
            vat_sum=kopecks_to_rubles(item.get("ndsSum", 0)),
            price=kopecks_to_rubles(item["price"]),
            quantity=Decimal(str(item["quantity"])),
            sum=kopecks_to_rubles(item["sum"]),
        )
    await session.commit()

    return ReceiptCreated(id=receipt_object.id)
