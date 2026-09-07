from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.models.user import Role


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or any(c.isspace() for c in value):
            raise ValueError("Enter a valid email address")
        local, domain = value.split("@")
        if not local or not domain or "." not in domain:
            raise ValueError("Enter a valid email address")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc_dates(cls, value):
        # SQLite returns naive timestamps; all writes are UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
