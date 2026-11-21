from datetime import date

from app.core.exceptions import NotFound
from app.models import Task, User
from app.repositories import TaskRepository
from app.schemas.common import PageParams
from app.schemas.task import SortOrder, TaskCreate, TaskSortField, TaskUpdate

from .project_service import ProjectService, read_scope


class TaskService:
    def __init__(self, tasks: TaskRepository, projects: ProjectService) -> None:
        self.tasks = tasks
        self.projects = projects

    async def create(self, user: User, data: TaskCreate) -> Task:
        project = await self.projects.get_writable(user, data.project_id)  # 404 if not yours
        return await self.tasks.add(Task(owner_id=project.owner_id, **data.model_dump()))

    async def list(self, user: User, params: PageParams, *, project_id: int | None,
                   status: str | None, priority: str | None, due_before: date | None,
                   q: str | None, sort_by: TaskSortField, order: SortOrder) -> tuple[list[Task], int]:
        return await self.tasks.list(
            params.offset, params.size, read_scope(user), project_id=project_id, status=status,
            priority=priority, due_before=due_before, q=q, sort_by=sort_by.value,
            descending=order == SortOrder.DESC,
        )

    async def get(self, user: User, task_id: int) -> Task:
        task = await self.tasks.get_scoped(task_id, read_scope(user))
        if task is None:
            raise NotFound("Task not found")
        return task

    async def _get_writable(self, user: User, task_id: int) -> Task:
        task = await self.tasks.get_scoped(task_id, user.id)
        if task is None:
            raise NotFound("Task not found")
        return task

    async def update(self, user: User, task_id: int, data: TaskUpdate) -> Task:
        task = await self._get_writable(user, task_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        return await self.tasks.save(task)

    async def delete(self, user: User, task_id: int) -> None:
        await self.tasks.delete(await self._get_writable(user, task_id))
