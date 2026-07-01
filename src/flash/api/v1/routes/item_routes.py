from fastapi import APIRouter, Query, status
from flash.schemas.item_schema import ItemRead, ItemCreate, ItemUpdate
from flash.api.deps import ItemServiceDep

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
async def list_items(
    service: ItemServiceDep,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[ItemRead]:
    items = await service.list(limit, offset)
    return [ItemRead.model_validate(item) for item in items]


@router.get("/{item_id}")
async def get_item(service: ItemServiceDep, item_id: int) -> ItemRead:
    return ItemRead.model_validate(await service.get(item_id))


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(service: ItemServiceDep, data: ItemCreate) -> ItemRead:
    return ItemRead.model_validate(await service.create(data))


@router.patch("/{item_id}")
async def update_item(
    service: ItemServiceDep, item_id: int, data: ItemUpdate
) -> ItemRead:
    return ItemRead.model_validate(await service.update(item_id, data))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(service: ItemServiceDep, item_id: int) -> None:
    await service.delete(item_id)
