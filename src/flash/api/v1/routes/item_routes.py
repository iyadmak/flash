from fastapi import APIRouter, status
from flash.schemas.item_schema import ItemRead, ItemCreate, ItemUpdate
from flash.api.deps import ItemServiceDep, DBSessionDep

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
async def list_items(session: DBSessionDep, service: ItemServiceDep) -> list[ItemRead]:
    items = await service.list(session)
    return [ItemRead.model_validate(item) for item in items]


@router.get("/{item_id}")
async def get_item(
    session: DBSessionDep, service: ItemServiceDep, item_id: int
) -> ItemRead:
    item = await service.get(session, item_id)
    return ItemRead.model_validate(item)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    session: DBSessionDep, service: ItemServiceDep, data: ItemCreate
) -> ItemRead:
    item = await service.create(session, data)
    return ItemRead.model_validate(item)


@router.patch("/{item_id}")
async def update_item(
    session: DBSessionDep, service: ItemServiceDep, item_id: int, data: ItemUpdate
) -> ItemRead:
    item = await service.update(session, item_id, data)
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    session: DBSessionDep, service: ItemServiceDep, item_id: int
) -> None:
    await service.delete(session, item_id)
