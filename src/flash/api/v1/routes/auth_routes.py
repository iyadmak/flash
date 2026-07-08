from typing import Annotated
from fastapi import APIRouter, status, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from flash.core.security import limiter
from flash.api.deps import UserServiceDep, AuthServiceDep
from flash.schemas.auth_schemas import TokenResponse
from flash.schemas.user_schema import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_service: UserServiceDep, data: UserCreate) -> UserRead:
    user = await user_service.create(data)
    return UserRead.model_validate(user)


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    auth_service: AuthServiceDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    acces_token = await auth_service.login(form_data.username, form_data.password)
    return TokenResponse(access_token=acces_token)
