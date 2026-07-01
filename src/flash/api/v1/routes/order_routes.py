from fastapi import APIRouter, status, Query
from flash.api.deps import OrderServiceDep
from flash.schemas.order_schema import OrderCreate, OrderUpdate, OrderRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
async def list_orders(
    order_service: OrderServiceDep,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[OrderRead]:
    orders = await order_service.list(limit, offset)
    return [OrderRead.model_validate(order) for order in orders]


@router.get("/{order_id}")
async def get_order(order_service: OrderServiceDep, order_id: int) -> OrderRead:
    order = await order_service.get(order_id)
    return OrderRead.model_validate(order)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(order_service: OrderServiceDep, data: OrderCreate) -> OrderRead:
    order = await order_service.create(data)
    return OrderRead.model_validate(order)


@router.put("/{order_id}")
async def update_order(
    order_service: OrderServiceDep,
    order_id: int,
    data: OrderUpdate,
) -> OrderRead:
    order = await order_service.update(order_id, data)
    return OrderRead.model_validate(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(order_service: OrderServiceDep, order_id: int) -> None:
    await order_service.delete(order_id)
