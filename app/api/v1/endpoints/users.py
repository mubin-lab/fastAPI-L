from fastapi import APIRouter, status

from app.api.deps import AdminUser, CurrentUser, Pagination, UserServiceDep
from app.models import Role
from app.schemas.common import Page
from app.schemas.user import UserAdminUpdate, UserRead, UserUpdateMe

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdateMe, user: CurrentUser, svc: UserServiceDep):
    return await svc.update_me(user, data)


# Admin-only routes. Declared after /me so "me" is not parsed as a user_id.
@router.get("", response_model=Page[UserRead])
async def list_users(_: AdminUser, svc: UserServiceDep, params: Pagination, q: str | None = None,
                     role: Role | None = None, is_active: bool | None = None):
    items, total = await svc.list_users(params, q, role.value if role else None, is_active)
    return Page[UserRead].create(items, total, params)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, _: AdminUser, svc: UserServiceDep):
    return await svc.get(user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def admin_update_user(user_id: int, data: UserAdminUpdate, admin: AdminUser, svc: UserServiceDep):
    return await svc.admin_update(admin, user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate a user")
async def deactivate_user(user_id: int, admin: AdminUser, svc: UserServiceDep) -> None:
    await svc.deactivate(admin, user_id)
