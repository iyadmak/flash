from fastapi import APIRouter, status

from flash.api.deps import UserServiceDep, CurrentUserDep
from flash.core.exceptions import Forbidden
from flash.schemas.user_schema import UserUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/{user_id}")
async def get(user_service: UserServiceDep, user_id: int) -> UserRead:
    user = await user_service.get(user_id)
    return UserRead.model_validate(user)


@router.put("/{user_id}")
async def update(
    user_service: UserServiceDep,
    user_id: int,
    data: UserUpdate,
    current_user: CurrentUserDep,
) -> UserRead:
    if current_user.id != user_id:
        raise Forbidden()
    user = await user_service.update(user_id, data)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    user_service: UserServiceDep, user_id: int, current_user: CurrentUserDep
) -> None:
    if current_user.id != user_id:
        raise Forbidden()
    return await user_service.delete(user_id)
