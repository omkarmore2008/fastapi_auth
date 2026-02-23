"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import BaseSchema
from app.schemas.user import UserRead


class SignupRequest(BaseModel):
    """Signup request schema."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class VerifyEmailRequest(BaseModel):
    """Email verification schema."""

    token: str = Field(min_length=20, max_length=300)


class LoginRequest(BaseModel):
    """Email/password login schema."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LogoutRequest(BaseModel):
    """Logout request schema."""

    refresh_token: str = Field(min_length=20, max_length=700)


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""

    token: str = Field(min_length=20, max_length=300)
    new_password: str = Field(min_length=8, max_length=128)


class RequestOtpRequest(BaseModel):
    """Request OTP request schema."""

    email: EmailStr


class LoginOtpRequest(BaseModel):
    """OTP login request schema."""

    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class TokenPairResponse(BaseSchema):
    """Login success response with token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenVerifyResponse(BaseSchema):
    """Token validation response schema."""

    is_valid: bool
    user_id: str | None = None
    token_type: str | None = None
