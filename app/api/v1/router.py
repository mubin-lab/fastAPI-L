from fastapi import APIRouter

from .endpoints import auth, health, projects, tasks, users

api_router = APIRouter()
for module in (health, auth, users, projects, tasks):
    api_router.include_router(module.router)
