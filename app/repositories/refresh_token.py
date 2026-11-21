from datetime import datetime

from sqlalchemy import select, update

from app.core.security import utcnow
from app.models import RefreshToken

from .base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def create(self, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        return await self.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at))

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = utcnow()
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: int) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
