from fastapi import APIRouter, status
from flash.api.deps import UserServiceDep
from flash.schemas.user_schema import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_service: UserServiceDep, data: UserCreate) -> UserRead:
    user = await user_service.create(data)
    return UserRead.model_validate(user)
