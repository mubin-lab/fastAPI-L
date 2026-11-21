from sqlalchemy import select

from app.models import User

from .base import BaseRepository, like_pattern


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def list(self, offset: int, limit: int, q: str | None = None,
                   role: str | None = None, is_active: bool | None = None) -> tuple[list[User], int]:
        stmt = select(User).order_by(User.id)
        if q:
            p = like_pattern(q)
            stmt = stmt.where(User.email.ilike(p, escape="\\") | User.full_name.ilike(p, escape="\\"))
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        return await self.paginate(stmt, offset, limit)
