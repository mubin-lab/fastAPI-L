from pydantic import BaseModel, Field

from .user import Email, Password


class RegisterRequest(BaseModel):
    email: Email
    password: Password
    full_name: str = Field(default="", max_length=120)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token lifetime in seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Password
