from app.core.exceptions import Conflict, NotFound
from app.models import User
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas.common import PageParams
from app.schemas.user import UserAdminUpdate, UserUpdateMe


class UserService:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository) -> None:
        self.users = users
        self.tokens = tokens

    async def update_me(self, user: User, data: UserUpdateMe) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(user, field, value)
        return await self.users.save(user)

    async def list_users(self, params: PageParams, q: str | None, role: str | None,
                         is_active: bool | None) -> tuple[list[User], int]:
        return await self.users.list(params.offset, params.size, q, role, is_active)

    async def get(self, user_id: int) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFound("User not found")
        return user

    async def admin_update(self, actor: User, user_id: int, data: UserAdminUpdate) -> User:
        user = await self.get(user_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if user.id == actor.id and (changes.get("is_active") is False or
                                    ("role" in changes and changes["role"] != user.role)):
            raise Conflict("Admins cannot demote or deactivate themselves")
        for field, value in changes.items():
            setattr(user, field, value.value if hasattr(value, "value") else value)
        user = await self.users.save(user)
        if not user.is_active:
            await self.tokens.revoke_all_for_user(user.id)
        return user

    async def deactivate(self, actor: User, user_id: int) -> None:
        await self.admin_update(actor, user_id, UserAdminUpdate(is_active=False))
