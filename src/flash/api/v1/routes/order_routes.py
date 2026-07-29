from fastapi import APIRouter, Depends, status, Query
from flash.api.deps import OrderServiceDep, CurrentUserDep, get_current_user
from flash.schemas.order_schema import OrderCreate, OrderStatusUpdate, OrderRead

router = APIRouter(
    prefix="/orders", tags=["orders"], dependencies=[Depends(get_current_user)]
)


@router.get("/")
async def list_orders(
    order_service: OrderServiceDep,
    current_user: CurrentUserDep,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[OrderRead]:
    orders = await order_service.list(limit, offset, current_user.id)
    return [OrderRead.model_validate(order) for order in orders]


@router.get("/{order_id}")
async def get_order(
    order_service: OrderServiceDep, order_id: int, current_user: CurrentUserDep
) -> OrderRead:
    order = await order_service.get(order_id, current_user.id)
    return OrderRead.model_validate(order)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(
    order_service: OrderServiceDep, data: OrderCreate, current_user: CurrentUserDep
) -> OrderRead:
    order = await order_service.create(data, current_user.id)
    return OrderRead.model_validate(order)


# A named operation rather than PUT /{order_id}, so permissions can attach to it.
@router.patch("/{order_id}/status")
async def change_order_status(
    order_service: OrderServiceDep,
    order_id: int,
    current_user: CurrentUserDep,
    data: OrderStatusUpdate,
) -> OrderRead:
    order = await order_service.change_status(order_id, data.status, current_user.id)
    return OrderRead.model_validate(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_service: OrderServiceDep, order_id: int, current_user: CurrentUserDep
) -> None:
    await order_service.delete(order_id, current_user.id)
