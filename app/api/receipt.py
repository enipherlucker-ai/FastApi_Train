import json
from datetime import datetime
from decimal import Decimal
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException

from app.api.dependencies import (
    ApiCheckReceiptDep,
    ApiLogsDep,
    GroupRepoDep,
    ReceiptCompoundDep,
    ReceiptDep,
    SessionDep,
    CategorizerDep
)
from app.constants import ADMIN_USER_ID, DEFAULT_GROUP_NAME
from app.foreign_api.categorizer import ReceiptCategorizer, CategorizerError
from app.foreign_api.check_receipt import CheckReceipt, CheckReceiptUnavailableError, ReceiptNotFoundError
from app.repositories import ReceiptCompoundRepository, ApiLogsRepository
from app.schemas import ReceiptBase, ReceiptCreated
from app.models.groups import Group

router = APIRouter(tags=["receipt"])


def kopecks_to_rubles(value: int) -> Decimal:
    return Decimal(value) / 100

async def assign_groups(
        names: list[str],
        groups: Sequence[Group],
        default_group_id: int,
        receipt_compound: ReceiptCompoundRepository,
        categorizer: ReceiptCategorizer | None,
        api_logs: ApiLogsRepository,
):
    group_ids = [default_group_id] * len(names)

    known = await receipt_compound.known_groups(
        user_id=ADMIN_USER_ID,
        names=names,
        exclude_group_id=default_group_id,
    )
    uknown: list[int] = []
    for i, name in enumerate(names):
        if name in known:
            group_ids[i] = known[name]
        else:
            uknown.append(i)

    if not uknown or categorizer is None:
        return group_ids

    unknown_names = [names[i] for i in uknown]
    groups_for_prompt = [
        {"id": g.id, "name": g.name, "description": g.description} for g in groups
    ]
    try:
        answer = await categorizer.categorize(
            names=unknown_names,
            groups=groups_for_prompt,
        )
        output = answer.model_dump_json()
    except CategorizerError as exc:
        answer = None
        output = f"Ошибка: {exc}"

    await api_logs.logs_add(
        user_id=ADMIN_USER_ID,
        service="openai",
        method="[POST]/chat/completions",
        comment="Определение групп",
        input_data=json.dumps(unknown_names, ensure_ascii=False),
        output_data=output,
    )
    if answer is None:
        return group_ids

    allowed = {g.id for g in groups}
    for item in answer.items:
        if 0 <= item.index < len(uknown) and item.group_id in allowed:
            group_ids[uknown[item.index]] = item.group_id

    return group_ids

@router.post("/create_receipt", response_model=ReceiptCreated, status_code=201)
async def create_receipt(
        data: ReceiptBase,
        api_receipt: ApiCheckReceiptDep,
        api_logs: ApiLogsDep,
        session: SessionDep,
        receipt: ReceiptDep,
        receipt_compound: ReceiptCompoundDep,
        groups: GroupRepoDep,
        categorized: CategorizerDep,
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

    items = main_data["items"]
    group_ids = await assign_groups(
        names=[item["name"] for item in items],
        groups=await groups.list_for_user(ADMIN_USER_ID),
        default_group_id=default_group.id,
        receipt_compound=receipt_compound,
        categorizer=categorized,
        api_logs=api_logs,
    )

    receipt_object = await receipt.create(
        period=datetime.fromisoformat(main_data["dateTime"]),
        user_id=ADMIN_USER_ID,
        qrraw=data.raw_receipt,
        retail_place=main_data.get("retailPlace"),
        retail_place_address=main_data.get("retailPlaceAddress"),
        total_sum=kopecks_to_rubles(main_data["totalSum"]),
    )
    for item, group_id in zip(items, group_ids, strict=True):
        await receipt_compound.create(
            name=item["name"],
            receipt_id=receipt_object.id,
            user_id=ADMIN_USER_ID,
            group_id=group_id,
            vat=item["nds"],
            vat_sum=kopecks_to_rubles(item.get("ndsSum", 0)),
            price=kopecks_to_rubles(item["price"]),
            quantity=Decimal(str(item["quantity"])),
            sum=kopecks_to_rubles(item["sum"]),
        )
    await session.commit()

    return ReceiptCreated(id=receipt_object.id)
