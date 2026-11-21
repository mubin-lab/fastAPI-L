import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.user import Role

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Invalid e-mail address")
    return v


def _password_policy(v: str) -> str:
    if len(v.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes (bcrypt limit)")
    if not (re.search(r"[a-z]", v) and re.search(r"[A-Z]", v) and re.search(r"\d", v)):
        raise ValueError("Password must contain a lowercase letter, an uppercase letter and a digit")
    return v


Email = Annotated[str, Field(max_length=255), AfterValidator(_normalize_email)]
Password = Annotated[str, Field(min_length=10), AfterValidator(_password_policy)]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserUpdateMe(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)


class UserAdminUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
