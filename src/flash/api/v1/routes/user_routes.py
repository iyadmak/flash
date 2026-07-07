from fastapi import APIRouter, status

from flash.api.deps import UserServiceDep
from flash.schemas.user_schema import UserUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
async def get(user_service: UserServiceDep, user_id: int) -> UserRead:
    user = await user_service.get(user_id)
    return UserRead.model_validate(user)


@router.put("/{user_id}")
async def update(
    user_service: UserServiceDep, user_id: int, data: UserUpdate
) -> UserRead:
    user = await user_service.update(user_id, data)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(user_service: UserServiceDep, user_id: int) -> None:
    return await user_service.delete(user_id)
