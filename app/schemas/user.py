"""User-related pydantic schemas."""

from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema


class UserRead(BaseSchema):
    """User read response schema."""

    id: str
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    is_verified: bool
    avatar_url: str | None = None
    created_at: datetime
    updated_at: datetime


class UploadProfileResponse(BaseSchema):
    """Profile picture upload response schema."""

    file_id: str
    file_url: str
    mime_type: str
    file_name: str


class PermissionRead(BaseSchema):
    """Permission response schema."""

    code: str = Field(min_length=3, max_length=120)


class UserPermissionsResponse(BaseSchema):
    """Effective permissions for current user."""

    user_id: str
    permissions: list[PermissionRead]
