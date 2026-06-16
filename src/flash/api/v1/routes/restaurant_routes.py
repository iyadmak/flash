from fastapi import APIRouter, status

from flash.api.deps import RestaurantServiceDep, DBSessionDep
from flash.schemas.restaurant_schema import (
    RestaurantRead,
    RestaurantCreate,
    RestaurantUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("/")
async def list_restaurants(
    session: DBSessionDep, restaurant_service: RestaurantServiceDep
) -> list[RestaurantRead]:
    restaurants = await restaurant_service.list(session)
    return [RestaurantRead.model_validate(restaurant) for restaurant in restaurants]


@router.get("/{restaurant_id}")
async def get(
    session: DBSessionDep, restaurant_service: RestaurantServiceDep, restaurant_id: int
) -> RestaurantRead:
    restaurant = await restaurant_service.get(session, restaurant_id)
    return RestaurantRead.model_validate(restaurant)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(
    session: DBSessionDep,
    restaurant_service: RestaurantServiceDep,
    data: RestaurantCreate,
) -> RestaurantRead:
    restaurant = await restaurant_service.create(session, data)
    return RestaurantRead.model_validate(restaurant)


@router.put("/{restaurant_id}")
async def update(
    session: DBSessionDep,
    restaurant_service: RestaurantServiceDep,
    restaurant_id: int,
    data: RestaurantUpdate,
) -> RestaurantRead:
    restaurant = await restaurant_service.update(session, restaurant_id, data)
    return RestaurantRead.model_validate(restaurant)


@router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    session: DBSessionDep, restaurant_service: RestaurantServiceDep, restaurant_id: int
) -> None:
    await restaurant_service.delete(session, restaurant_id)
