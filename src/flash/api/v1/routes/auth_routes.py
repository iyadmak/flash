from typing import Annotated
from fastapi import APIRouter, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from flash.core.rate_limit import rate_limit
from flash.api.deps import UserServiceDep, AuthServiceDep
from flash.schemas.auth_schemas import (
    PasswordResetRequest,
    TokenResponse,
    PasswordResetConfirm,
)
from flash.schemas.user_schema import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_service: UserServiceDep, data: UserCreate) -> UserRead:
    user = await user_service.create(data)
    return UserRead.model_validate(user)


@router.post("/login", dependencies=[Depends(rate_limit("5/minute"))])
async def login(
    auth_service: AuthServiceDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    acces_token = await auth_service.login(form_data.username, form_data.password)
    return TokenResponse(access_token=acces_token)


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    auth_service: AuthServiceDep, data: PasswordResetRequest
) -> None:
    token = await auth_service.request_password_reset(data.email)
    if token is not None:
        # TODO: replace with a real email send once there's an email service.
        print(f"[DEV] Password reset link: /reset-password?token={token}")


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    auth_service: AuthServiceDep, data: PasswordResetConfirm
) -> None:
    await auth_service.reset_password(data.token, data.new_password)
