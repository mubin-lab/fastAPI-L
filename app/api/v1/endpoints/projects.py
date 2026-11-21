from fastapi import APIRouter, status

from app.api.deps import CurrentUser, Pagination, ProjectServiceDep
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectCreate, user: CurrentUser, svc: ProjectServiceDep):
    return await svc.create(user, data)


@router.get("", response_model=Page[ProjectRead])
async def list_projects(user: CurrentUser, svc: ProjectServiceDep, params: Pagination,
                        q: str | None = None, archived: bool | None = None):
    items, total = await svc.list(user, params, q, archived)
    return Page[ProjectRead].create(items, total, params)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, user: CurrentUser, svc: ProjectServiceDep):
    return await svc.get(user, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: int, data: ProjectUpdate, user: CurrentUser, svc: ProjectServiceDep):
    return await svc.update(user, project_id, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, user: CurrentUser, svc: ProjectServiceDep) -> None:
    await svc.delete(user, project_id)
