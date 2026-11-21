from sqlalchemy import delete, select

from app.models import Project, Task

from .base import BaseRepository, like_pattern


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def get_scoped(self, project_id: int, owner_id: int | None) -> Project | None:
        """owner_id=None means 'no ownership filter' (admin read access)."""
        stmt = select(Project).where(Project.id == project_id)
        if owner_id is not None:
            stmt = stmt.where(Project.owner_id == owner_id)
        return await self.session.scalar(stmt)

    async def list(self, offset: int, limit: int, owner_id: int | None, q: str | None = None,
                   archived: bool | None = None) -> tuple[list[Project], int]:
        stmt = select(Project).order_by(Project.id.desc())
        if owner_id is not None:
            stmt = stmt.where(Project.owner_id == owner_id)
        if q:
            p = like_pattern(q)
            stmt = stmt.where(Project.name.ilike(p, escape="\\") | Project.description.ilike(p, escape="\\"))
        if archived is not None:
            stmt = stmt.where(Project.archived == archived)
        return await self.paginate(stmt, offset, limit)

    async def delete_with_tasks(self, project: Project) -> None:
        await self.session.execute(delete(Task).where(Task.project_id == project.id))
        await self.delete(project)
