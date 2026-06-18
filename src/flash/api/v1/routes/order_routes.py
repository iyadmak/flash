from fastapi import APIRouter, status
from flash.api.deps import OrderServiceDep, DBSessionDep
from flash.schemas.order_schema import OrderCreate, OrderUpdate, OrderRead

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/")
async def list_orders(
    order_service: OrderServiceDep, session: DBSessionDep
) -> list[OrderRead]:
    orders = await order_service.list(session)
    return [OrderRead.model_validate(order) for order in orders]


@router.get("/{order_id}")
async def get_order(
    order_id: int, order_service: OrderServiceDep, session: DBSessionDep
) -> OrderRead:
    order = await order_service.get(session, order_id)
    return OrderRead.model_validate(order)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate, order_service: OrderServiceDep, session: DBSessionDep
) -> OrderRead:
    order = await order_service.create(session, data)
    return OrderRead.model_validate(order)


@router.put("/{order_id}")
async def update_order(
    order_id: int,
    data: OrderUpdate,
    order_service: OrderServiceDep,
    session: DBSessionDep,
) -> OrderRead:
    order = await order_service.update(session, order_id, data)
    return OrderRead.model_validate(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int, order_service: OrderServiceDep, session: DBSessionDep
) -> None:
    await order_service.delete(session, order_id)
