from fastapi import APIRouter, Depends, Query, status
from flash.schemas.item_schema import ItemRead, ItemCreate, ItemUpdate, ItemPage
from flash.api.deps import ItemServiceDep, get_current_user

router = APIRouter(
    prefix="/items", tags=["items"], dependencies=[Depends(get_current_user)]
)


@router.get("/")
async def list_items(
    service: ItemServiceDep,
    limit: int = Query(50, le=100),
    cursor: str | None = Query(None),
) -> ItemPage:
    items, next_cursor = await service.list_with_cursor(limit, cursor)
    return ItemPage(
        items=[ItemRead.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )


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
