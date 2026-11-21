from datetime import date

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, Pagination, TaskServiceDep
from app.models import TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import SortOrder, TaskCreate, TaskRead, TaskSortField, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, user: CurrentUser, svc: TaskServiceDep):
    return await svc.create(user, data)


@router.get("", response_model=Page[TaskRead])
async def list_tasks(
    user: CurrentUser, svc: TaskServiceDep, params: Pagination,
    project_id: int | None = None, status: TaskStatus | None = None,
    priority: TaskPriority | None = None, due_before: date | None = None, q: str | None = None,
    sort_by: TaskSortField = TaskSortField.CREATED_AT, order: SortOrder = SortOrder.DESC,
):
    items, total = await svc.list(
        user, params, project_id=project_id, status=status.value if status else None,
        priority=priority.value if priority else None, due_before=due_before, q=q,
        sort_by=sort_by, order=order,
    )
    return Page[TaskRead].create(items, total, params)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, user: CurrentUser, svc: TaskServiceDep):
    return await svc.get(user, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, data: TaskUpdate, user: CurrentUser, svc: TaskServiceDep):
    return await svc.update(user, task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: CurrentUser, svc: TaskServiceDep) -> None:
    await svc.delete(user, task_id)
