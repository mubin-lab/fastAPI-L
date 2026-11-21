from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas.auth import ChangePasswordRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, auth: AuthServiceDep):
    return await auth.register(data)


@router.post("/login", response_model=TokenPair)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], auth: AuthServiceDep):
    """OAuth2 password form: `username` is the e-mail address."""
    return await auth.login(form.username, form.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, auth: AuthServiceDep):
    return await auth.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, auth: AuthServiceDep) -> None:
    await auth.logout(data.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(user: CurrentUser, auth: AuthServiceDep) -> None:
    await auth.logout_all(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: ChangePasswordRequest, user: CurrentUser, auth: AuthServiceDep) -> None:
    await auth.change_password(user, data.current_password, data.new_password)


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user
