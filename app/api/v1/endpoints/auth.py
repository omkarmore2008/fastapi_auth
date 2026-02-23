"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_claims
from app.db.session import get_db_session, get_redis
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginOtpRequest,
    LoginRequest,
    LogoutRequest,
    RequestOtpRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenPairResponse,
    TokenVerifyResponse,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/signup", response_model=MessageResponse)
async def signup(
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Create user and send verification email.

    Args:
        payload: Signup request body.
        db: Active database session.
    Returns:
        MessageResponse: Confirmation response.
    """
    service = AuthService()
    await service.signup(db=db, email=payload.email, password=payload.password, full_name=payload.full_name)
    return MessageResponse(message="If account is new, verification email has been sent")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Activate account with email verification token.

    Args:
        payload: Verification token payload.
        db: Active database session.
    Returns:
        MessageResponse: Verification result.
    """
    service = AuthService()
    ok = await service.verify_email(db=db, token=payload.token)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return MessageResponse(message="Email verified and account activated")


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> TokenPairResponse:
    """Login with email/password and return token pair.

    Args:
        payload: Login credentials payload.
        db: Active database session.
        redis: Redis client.
    Returns:
        TokenPairResponse: Auth token pair and user profile.
    """
    service = AuthService()
    data = await service.login(db=db, redis=redis, email=payload.email, password=payload.password)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenPairResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        user=UserRead.model_validate(data["user"]),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Revoke refresh token session.

    Args:
        payload: Logout payload with refresh token.
        db: Active database session.
        redis: Redis client.
    Returns:
        MessageResponse: Logout operation result.
    """
    service = AuthService()
    ok = await service.logout(db=db, redis=redis, refresh_token=payload.refresh_token)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to logout with token")
    return MessageResponse(message="Logged out successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Issue password reset token by email.

    Args:
        payload: Forgot password payload.
        db: Active database session.
    Returns:
        MessageResponse: Generic success response.
    """
    service = AuthService()
    await service.forgot_password(db=db, email=payload.email)
    return MessageResponse(message="If account exists, password reset email has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Reset password using token.

    Args:
        payload: Reset password payload.
        db: Active database session.
    Returns:
        MessageResponse: Reset operation response.
    """
    service = AuthService()
    ok = await service.reset_password(db=db, token=payload.token, new_password=payload.new_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return MessageResponse(message="Password reset successful")


@router.post("/request-otp", response_model=MessageResponse)
async def request_otp(
    payload: RequestOtpRequest,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Request OTP login code via email.

    Args:
        payload: Request OTP payload.
        db: Active database session.
    Returns:
        MessageResponse: Generic success response.
    """
    service = AuthService()
    await service.request_otp(db=db, email=payload.email)
    return MessageResponse(message="If account exists, OTP has been sent")


@router.post("/login-otp", response_model=TokenPairResponse)
async def login_otp(
    payload: LoginOtpRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> TokenPairResponse:
    """Login user with email + OTP.

    Args:
        payload: OTP login payload.
        db: Active database session.
        redis: Redis client.
    Returns:
        TokenPairResponse: Auth token pair and user profile.
    """
    service = AuthService()
    data = await service.login_with_otp(db=db, redis=redis, email=payload.email, otp=payload.otp)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP credentials")
    return TokenPairResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        user=UserRead.model_validate(data["user"]),
    )


@router.get("/verify-token", response_model=TokenVerifyResponse)
async def verify_token(claims: dict = Depends(get_claims)) -> TokenVerifyResponse:
    """Return token validity and decoded summary.

    Args:
        claims: Decoded JWT claims from dependency.
    Returns:
        TokenVerifyResponse: Token validity payload.
    """
    return TokenVerifyResponse(
        is_valid=True,
        user_id=str(claims.get("sub")),
        token_type=str(claims.get("type")),
    )
