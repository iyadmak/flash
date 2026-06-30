from fastapi import APIRouter, status, Query

from flash.api.deps import RestaurantServiceDep
from flash.schemas.restaurant_schema import (
    RestaurantRead,
    RestaurantCreate,
    RestaurantUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.get("/")
async def list_restaurants(
    restaurant_service: RestaurantServiceDep,
    limit: int = Query(50, le=100),
    offset: int = Query(ge=0),
) -> list[RestaurantRead]:
    restaurants = await restaurant_service.list(limit, offset)
    return [RestaurantRead.model_validate(restaurant) for restaurant in restaurants]


@router.get("/{restaurant_id}")
async def get(
    restaurant_service: RestaurantServiceDep, restaurant_id: int
) -> RestaurantRead:
    restaurant = await restaurant_service.get(restaurant_id)
    return RestaurantRead.model_validate(restaurant)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(
    restaurant_service: RestaurantServiceDep,
    data: RestaurantCreate,
) -> RestaurantRead:
    restaurant = await restaurant_service.create(data)
    return RestaurantRead.model_validate(restaurant)


@router.put("/{restaurant_id}")
async def update(
    restaurant_service: RestaurantServiceDep,
    restaurant_id: int,
    data: RestaurantUpdate,
) -> RestaurantRead:
    restaurant = await restaurant_service.update(restaurant_id, data)
    return RestaurantRead.model_validate(restaurant)


@router.delete("/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(restaurant_service: RestaurantServiceDep, restaurant_id: int) -> None:
    await restaurant_service.delete(restaurant_id)
