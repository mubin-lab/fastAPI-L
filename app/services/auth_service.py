"""Authentication use-cases: register, login, refresh (rotation), logout, change password."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.exceptions import Conflict, Forbidden, Unauthorized
from app.models import Role, User
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas.auth import RegisterRequest, TokenPair


class AuthService:
    def __init__(self, session: AsyncSession, users: UserRepository, tokens: RefreshTokenRepository) -> None:
        self.session = session
        self.users = users
        self.tokens = tokens

    async def register(self, data: RegisterRequest, role: Role = Role.USER) -> User:
        if await self.users.get_by_email(data.email):
            raise Conflict("E-mail already registered")
        user = User(email=data.email, full_name=data.full_name,
                    hashed_password=security.hash_password(data.password), role=role.value)
        return await self.users.add(user)

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(email.strip().lower())
        # Always run one bcrypt check so unknown e-mails and wrong passwords take similar time.
        ok = security.verify_password(password, user.hashed_password if user else security.DUMMY_HASH)
        if user is None or not ok:
            raise Unauthorized("Incorrect e-mail or password")
        if not user.is_active:
            raise Forbidden("Account is deactivated")
        return await self._issue_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = security.decode_token(refresh_token, security.REFRESH)
        stored = await self.tokens.get_by_hash(security.hash_token(refresh_token))
        if stored is None:
            raise Unauthorized("Unknown refresh token")
        if stored.revoked_at is not None:
            # A rotated/revoked token came back: assume theft. Kill every session of this user.
            await self.tokens.revoke_all_for_user(stored.user_id)
            await self.session.commit()  # persist the revocation even though we raise below
            raise Unauthorized("Refresh token reuse detected; all sessions revoked")
        if security.ensure_utc(stored.expires_at) <= security.utcnow():
            raise Unauthorized("Refresh token expired")
        user = await self.users.get(int(payload["sub"]))
        if user is None or not user.is_active:
            raise Unauthorized("User not found or deactivated")
        await self.tokens.revoke(stored)  # rotation: the old token is single-use
        return await self._issue_pair(user)

    async def logout(self, refresh_token: str) -> None:
        security.decode_token(refresh_token, security.REFRESH)
        stored = await self.tokens.get_by_hash(security.hash_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            await self.tokens.revoke(stored)

    async def logout_all(self, user: User) -> None:
        await self.tokens.revoke_all_for_user(user.id)

    async def change_password(self, user: User, current: str, new: str) -> None:
        if not security.verify_password(current, user.hashed_password):
            raise Unauthorized("Current password is incorrect")
        user.hashed_password = security.hash_password(new)
        await self.users.save(user)
        await self.tokens.revoke_all_for_user(user.id)  # force re-login everywhere

    async def authenticate_access_token(self, token: str) -> User:
        payload = security.decode_token(token, security.ACCESS)
        user = await self.users.get(int(payload["sub"]))
        if user is None:
            raise Unauthorized("User not found")
        if not user.is_active:
            raise Forbidden("Account is deactivated")
        return user

    async def ensure_admin(self, email: str, password: str) -> None:
        """Bootstrap helper used at startup (FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD)."""
        if await self.users.get_by_email(email.lower()):
            return
        await self.users.add(User(email=email.lower(), full_name="Admin",
                                  hashed_password=security.hash_password(password), role=Role.ADMIN.value))

    async def _issue_pair(self, user: User) -> TokenPair:
        access, expires_in = security.create_access_token(user.id, [user.role])
        refresh = security.create_refresh_token(user.id)
        await self.tokens.create(user.id, security.hash_token(refresh.token), refresh.expires_at)
        return TokenPair(access_token=access, refresh_token=refresh.token, expires_in=expires_in)


__all__ = ["AuthService"]
