from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import DB
from app.models.game import StorePrice
from app.routers.admin.deps import verify_admin
from app.schemas.store import StorePriceIn, StorePriceOut

router = APIRouter(prefix="/store", tags=["admin: /store"], dependencies=[Depends(verify_admin)])


@router.get("", response_model=list[StorePriceOut], summary="Get all store items")
async def get_all_store_items(db: DB) -> list[StorePriceOut]:
    """Fetch all store power-ups and their prices (Requires Admin JWT)."""
    items = (await db.scalars(select(StorePrice).order_by(StorePrice.power_up.asc()))).all()
    return [StorePriceOut.model_validate(item) for item in items]


@router.post("", response_model=StorePriceOut, status_code=status.HTTP_201_CREATED, summary="Create a store item")
async def create_store_item(body: StorePriceIn, db: DB) -> StorePriceOut:
    """Create a new store power-up item (Requires Admin JWT)."""
    power_up = body.power_up.strip()
    item = await db.get(StorePrice, power_up)
    if item:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Store item '{power_up}' already exists. Use PATCH to update.",
        )

    new_item = StorePrice(
        power_up=power_up,
        value=body.value,
        multiplier=body.multiplier,
    )
    db.add(new_item)
    await db.commit()
    return StorePriceOut.model_validate(new_item)


@router.patch("", response_model=StorePriceOut, summary="Update a store item")
async def update_store_item(body: StorePriceIn, db: DB) -> StorePriceOut:
    """Update an existing store power-up item (Requires Admin JWT)."""
    power_up = body.power_up.strip()
    item = await db.get(StorePrice, power_up)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store item '{power_up}' not found.",
        )

    if body.value is not None:
        item.value = body.value
    if body.multiplier is not None:
        item.multiplier = body.multiplier

    await db.commit()
    return StorePriceOut.model_validate(item)
