"""Dependency wiring: session -> repositories -> services -> current user -> role guards."""
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden
from app.db.session import get_db
from app.models import Role, User
from app.repositories import ProjectRepository, RefreshTokenRepository, TaskRepository, UserRepository
from app.schemas.common import PageParams
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PageParams, Depends()]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db, UserRepository(db), RefreshTokenRepository(db))


def get_user_service(db: DbSession) -> UserService:
    return UserService(UserRepository(db), RefreshTokenRepository(db))


def get_project_service(db: DbSession) -> ProjectService:
    return ProjectService(ProjectRepository(db))


def get_task_service(db: DbSession, projects: Annotated[ProjectService, Depends(get_project_service)]) -> TaskService:
    return TaskService(TaskRepository(db), projects)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], auth: AuthServiceDep) -> User:
    return await auth.authenticate_access_token(token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    """Dependency factory: `Depends(require_roles(Role.ADMIN))`."""
    allowed = {r.value for r in roles}

    async def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise Forbidden("Insufficient permissions")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
