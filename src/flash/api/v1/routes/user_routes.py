from fastapi import APIRouter, status, Depends

from flash.api.deps import UserServiceDep, CurrentUserDep, require_self
from flash.schemas.user_schema import UserUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get("/{user_id}", dependencies=[Depends(require_self)])
async def get(user_service: UserServiceDep, user_id: int) -> UserRead:
    user = await user_service.get(user_id)
    return UserRead.model_validate(user)


@router.put("/{user_id}", dependencies=[Depends(require_self)])
async def update(
    user_service: UserServiceDep,
    user_id: int,
    data: UserUpdate,
) -> UserRead:
    user = await user_service.update(user_id, data)
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_self)],
)
async def delete(user_service: UserServiceDep, user_id: int) -> None:
    await user_service.delete(user_id)
