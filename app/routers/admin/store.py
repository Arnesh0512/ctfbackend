import logging
from decimal import Decimal
from typing import Union

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.db import SessionLocal
from app.deps import DB
from app.models.game import StorePrice
from app.routers.admin.deps import verify_admin
from app.schemas.store import ALLOWED_POWER_UPS, StorePriceOut, StorePriceUpdate

logger = logging.getLogger("app.store")

router = APIRouter(prefix="/store", tags=["admin: /store"], dependencies=[Depends(verify_admin)])


async def init_store_prices() -> None:
    """Ensure standard power-ups exist in store_prices with initial value 0 without overwriting existing ones."""
    try:
        async with SessionLocal() as session:
            async with session.begin():
                # Clean up any non-allowed power-ups to ensure table strictly holds only valid items
                await session.execute(
                    delete(StorePrice).where(~StorePrice.power_up.in_(ALLOWED_POWER_UPS))
                )
                # Seed missing power-ups with initial 0.00 value, leaving existing rows unchanged
                values = [{"power_up": name, "value": Decimal("0.00")} for name in ALLOWED_POWER_UPS]
                stmt = insert(StorePrice).values(values).on_conflict_do_nothing(index_elements=["power_up"])
                await session.execute(stmt)
        logger.info("Store power-ups initialized successfully (%d standard items).", len(ALLOWED_POWER_UPS))
    except Exception as e:
        logger.exception("Failed to initialize store power-ups on startup: %s", e)
        raise


@router.get("", response_model=list[StorePriceOut], summary="Get all store items")
async def get_all_store_items(db: DB) -> list[StorePriceOut]:
    """Fetch all store power-ups and their prices (Requires Admin JWT)."""
    items = (await db.scalars(select(StorePrice).order_by(StorePrice.power_up.asc()))).all()
    return [StorePriceOut.model_validate(item) for item in items]


@router.patch(
    "",
    response_model=Union[StorePriceOut, list[StorePriceOut]],
    summary="Update store power-up price(s)",
    description=(
        "Update store power-up price(s). Accepts either a single object or a list of objects in the request body. "
        "No path parameters."
    ),
)
async def update_store_items(
    body: Union[StorePriceUpdate, list[StorePriceUpdate]] = Body(
        ...,
        description="Single power-up object or list of power-up objects to update",
        openapi_examples={
            "Patch All 9 Power-Ups (List)": {
                "summary": "Update all 9 standard power-ups at once as a list",
                "value": [
                    {"power_up": "RETRY", "value": 0.0},
                    {"power_up": "HINT1", "value": 0.0},
                    {"power_up": "HINT2", "value": 0.0},
                    {"power_up": "HINT12", "value": 0.0},
                    {"power_up": "BLOCK", "value": 0.0},
                    {"power_up": "UNBLOCK", "value": 0.0},
                    {"power_up": "DEVTIME", "value": 0.0},
                    {"power_up": "PATHCHANGEC", "value": 0.0},
                    {"power_up": "PATHCHANGET", "value": 0.0},
                ],
            },
            "Patch Single Power-Up": {
                "summary": "Update a single power-up",
                "value": {"power_up": "RETRY", "value": 50.0},
            },
            "Patch Multiple Select Power-Ups (List)": {
                "summary": "Update a subset of power-ups as a list",
                "value": [
                    {"power_up": "RETRY", "value": 50.0},
                    {"power_up": "HINT1", "value": 20.0},
                ],
            },
        },
    ),
    db: DB = None,
) -> Union[StorePriceOut, list[StorePriceOut]]:
    """Update one or multiple store power-up prices (Requires Admin JWT)."""
    is_single = isinstance(body, StorePriceUpdate)
    items_to_update = [body] if is_single else body

    if not items_to_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body cannot be an empty list.",
        )

    updated_items: list[StorePrice] = []
    for update in items_to_update:
        item = await db.get(StorePrice, update.power_up)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store item '{update.power_up}' not found in store table.",
            )
        item.value = update.value
        updated_items.append(item)

    await db.commit()
    for item in updated_items:
        await db.refresh(item)

    if is_single:
        return StorePriceOut.model_validate(updated_items[0])
    return [StorePriceOut.model_validate(item) for item in updated_items]
