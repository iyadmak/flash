from fastapi import APIRouter

from flash.api.deps import UserServiceDep, DBSessionDep
from flash.schemas.user_schema import UserCreate, UserUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
async def get(
    user_id: int, session: DBSessionDep, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.get(session, user_id)
    return UserRead.model_validate(user)


@router.post("/")
async def create_user(
    data: UserCreate, session: DBSessionDep, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.create(session, data)
    return UserRead.model_validate(user)


@router.put("/{user_id}")
async def update(
    user_id: int, data: UserUpdate, session: DBSessionDep, user_service: UserServiceDep
) -> UserRead:
    user = await user_service.update(session, user_id, data)
    return UserRead.model_validate(user)


@router.delete("/{user_id}")
async def delete(
    user_id: int, session: DBSessionDep, user_service: UserServiceDep
) -> None:
    return await user_service.delete(session, user_id)
