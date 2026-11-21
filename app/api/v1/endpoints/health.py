from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.exceptions import ServiceUnavailable

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe (checks the database)")
async def ready(db: DbSession) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServiceUnavailable("Database unavailable") from exc
    return {"status": "ready", "database": "ok"}
