from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    """Query dependency: ?page=1&size=20 (use as `Annotated[PageParams, Depends()]`)."""

    def __init__(self, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[Any], total: int, params: PageParams) -> "Page[T]":
        pages = (total + params.size - 1) // params.size
        return cls(items=items, total=total, page=params.page, size=params.size, pages=pages)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
