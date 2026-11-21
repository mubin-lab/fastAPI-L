"""Generic repository: the only layer that talks SQLAlchemy. No commits here (the unit of work commits)."""
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


def like_pattern(q: str) -> str:
    """Escape LIKE wildcards in user input; use with `.ilike(p, escape="\\\\")`."""
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: int) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()  # assigns PK / server defaults
        await self.session.refresh(obj)
        return obj

    async def save(self, obj: ModelT) -> ModelT:
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def paginate(self, stmt: Select[Any], offset: int, limit: int) -> tuple[list[ModelT], int]:
        total = await self.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
        rows = (await self.session.scalars(stmt.offset(offset).limit(limit))).all()
        return list(rows), total or 0
