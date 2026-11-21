from app.core.exceptions import NotFound
from app.models import Project, Role, User
from app.repositories import ProjectRepository
from app.schemas.common import PageParams
from app.schemas.project import ProjectCreate, ProjectUpdate


def read_scope(user: User) -> int | None:
    """Admins read everything (None = no owner filter); users only their own rows."""
    return None if user.role == Role.ADMIN else user.id


class ProjectService:
    def __init__(self, projects: ProjectRepository) -> None:
        self.projects = projects

    async def create(self, user: User, data: ProjectCreate) -> Project:
        return await self.projects.add(Project(owner_id=user.id, **data.model_dump()))

    async def list(self, user: User, params: PageParams, q: str | None,
                   archived: bool | None) -> tuple[list[Project], int]:
        return await self.projects.list(params.offset, params.size, read_scope(user), q, archived)

    async def get(self, user: User, project_id: int) -> Project:
        project = await self.projects.get_scoped(project_id, read_scope(user))
        if project is None:
            raise NotFound("Project not found")
        return project

    async def _get_writable(self, user: User, project_id: int) -> Project:
        # Writes are owner-only, even for admins (admins get read-all, not edit-all).
        project = await self.projects.get_scoped(project_id, user.id)
        if project is None:
            raise NotFound("Project not found")
        return project

    async def update(self, user: User, project_id: int, data: ProjectUpdate) -> Project:
        project = await self._get_writable(user, project_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        return await self.projects.save(project)

    async def delete(self, user: User, project_id: int) -> None:
        project = await self._get_writable(user, project_id)
        await self.projects.delete_with_tasks(project)

    async def get_writable(self, user: User, project_id: int) -> Project:
        return await self._get_writable(user, project_id)
