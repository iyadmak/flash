from fastapi import APIRouter, Depends, Query, status
from flash.schemas.item_schema import ItemRead, ItemCreate, ItemUpdate, ItemPage
from flash.api.deps import ItemServiceDep, CurrentUserDep, get_current_user

# Items are a subresource of an order, not a top-level collection: an item has
# no meaning apart from its order, and nesting the path is what lets every
# handler derive authorization from the parent instead of re-deriving it.
router = APIRouter(
    prefix="/orders/{order_id}/items",
    tags=["items"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_items(
    service: ItemServiceDep,
    order_id: int,
    current_user: CurrentUserDep,
    limit: int = Query(50, le=100),
    cursor: str | None = Query(None),
) -> ItemPage:
    items, next_cursor = await service.list_for_order(
        order_id, current_user.id, limit, cursor
    )
    return ItemPage(
        items=[ItemRead.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )


@router.get("/{item_id}")
async def get_item(
    service: ItemServiceDep,
    order_id: int,
    item_id: int,
    current_user: CurrentUserDep,
) -> ItemRead:
    item = await service.get(order_id, item_id, current_user.id)
    return ItemRead.model_validate(item)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    service: ItemServiceDep,
    order_id: int,
    data: ItemCreate,
    current_user: CurrentUserDep,
) -> ItemRead:
    item = await service.create(order_id, data, current_user.id)
    return ItemRead.model_validate(item)


@router.patch("/{item_id}")
async def update_item(
    service: ItemServiceDep,
    order_id: int,
    item_id: int,
    data: ItemUpdate,
    current_user: CurrentUserDep,
) -> ItemRead:
    item = await service.update(order_id, item_id, data, current_user.id)
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    service: ItemServiceDep,
    order_id: int,
    item_id: int,
    current_user: CurrentUserDep,
) -> None:
    await service.delete(order_id, item_id, current_user.id)
