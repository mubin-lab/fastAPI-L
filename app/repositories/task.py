from datetime import date

from sqlalchemy import case, select

from app.models import Task

from .base import BaseRepository, like_pattern

_PRIORITY_RANK = case({"low": 1, "medium": 2, "high": 3}, value=Task.priority)


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def get_scoped(self, task_id: int, owner_id: int | None) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        if owner_id is not None:
            stmt = stmt.where(Task.owner_id == owner_id)
        return await self.session.scalar(stmt)

    async def list(self, offset: int, limit: int, owner_id: int | None, *,
                   project_id: int | None = None, status: str | None = None,
                   priority: str | None = None, due_before: date | None = None,
                   q: str | None = None, sort_by: str = "created_at",
                   descending: bool = True) -> tuple[list[Task], int]:
        stmt = select(Task)
        if owner_id is not None:
            stmt = stmt.where(Task.owner_id == owner_id)
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        if status:
            stmt = stmt.where(Task.status == status)
        if priority:
            stmt = stmt.where(Task.priority == priority)
        if due_before is not None:
            stmt = stmt.where(Task.due_date.is_not(None), Task.due_date < due_before)
        if q:
            p = like_pattern(q)
            stmt = stmt.where(Task.title.ilike(p, escape="\\") | Task.description.ilike(p, escape="\\"))
        column = _PRIORITY_RANK if sort_by == "priority" else getattr(Task, sort_by)
        order = column.desc() if descending else column.asc()
        stmt = stmt.order_by(order, Task.id.desc() if descending else Task.id.asc())
        return await self.paginate(stmt, offset, limit)
