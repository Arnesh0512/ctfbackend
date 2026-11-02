from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB
from app.models.game import StorePrice
from app.schemas.store import StorePriceOut

router = APIRouter(prefix="/store", tags=["store: /store"])


@router.get("", response_model=list[StorePriceOut], summary="Get all store items (Public, No JWT)")
async def get_all_store_items(db: DB) -> list[StorePriceOut]:
    """Fetch all store items and their prices for participants/users without requiring a JWT."""
    items = (await db.scalars(select(StorePrice).order_by(StorePrice.power_up.asc()))).all()
    return [StorePriceOut.model_validate(item) for item in items]
