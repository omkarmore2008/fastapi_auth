"""Core authentication service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_token_pair,
    decode_jwt,
    generate_numeric_otp,
    generate_secure_token,
    hash_password,
    hash_token_value,
    verify_password,
)
from app.models.auth import (
    EmailVerificationToken,
    Group,
    LoginOtpCode,
    PasswordResetToken,
    RefreshTokenSession,
    User,
    UserGroup,
)
from app.services.email_service import EmailService


class AuthService:
    """Handles signup, login, reset, OTP, and token verification."""

    def __init__(self) -> None:
        """Initialize auth service with settings.

        Args:
            None
        Returns:
            None: Service with loaded app settings.
        """
        self.settings = get_settings()

    def _is_expired(self, dt_value: datetime) -> bool:
        """Check if datetime is in the past for aware or naive values.

        Args:
            dt_value: Datetime value from database.
        Returns:
            bool: True when datetime has already expired.
        """
        if dt_value.tzinfo is None:
            return dt_value < datetime.now(UTC).replace(tzinfo=None)
        return dt_value < datetime.now(UTC)

    async def signup(self, db: AsyncSession, email: str, password: str, full_name: str | None) -> None:
        """Create inactive user and issue email verification token.

        Args:
            db: Active database session.
            email: New user email.
            password: Plaintext password to hash.
            full_name: Optional user full name.
        Returns:
            None: Persists user and sends verification email.
        """
        email_service = EmailService()
        existing = await db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            return

        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            is_active=False,
            is_verified=False,
        )
        db.add(user)
        await db.flush()

        # Auto-assign the default member group when it exists.
        member_group = await db.scalar(select(Group).where(Group.name == "member"))
        if member_group:
            db.add(UserGroup(user_id=user.id, group_id=member_group.id))

        raw_token = generate_secure_token()
        token_row = EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token_value(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=self.settings.EMAIL_TOKEN_EXPIRE_MINUTES),
        )
        db.add(token_row)
        await db.commit()
        email_service.send_verification_email(user.email, raw_token)

    async def verify_email(self, db: AsyncSession, token: str) -> bool:
        """Verify email token and activate account.

        Args:
            db: Active database session.
            token: Raw email verification token.
        Returns:
            bool: True when account is activated.
        """
        token_hash = hash_token_value(token)
        stmt: Select[tuple[EmailVerificationToken]] = (
            select(EmailVerificationToken)
            .where(EmailVerificationToken.token_hash == token_hash)
            .order_by(desc(EmailVerificationToken.created_at))
        )
        token_row = await db.scalar(stmt)
        if not token_row:
            return False
        if token_row.used_at or self._is_expired(token_row.expires_at):
            return False

        user = await db.get(User, token_row.user_id)
        if not user:
            return False

        token_row.used_at = datetime.now(UTC)
        user.is_verified = True
        user.is_active = True
        await db.commit()
        return True

    async def login(self, db: AsyncSession, redis: Redis, email: str, password: str) -> dict | None:
        """Authenticate user and create token pair.

        Args:
            db: Active database session.
            redis: Redis client used for revoked session checks.
            email: User email.
            password: Plaintext password.
        Returns:
            dict | None: Token payload and user when successful.
        """
        del redis  # Redis reserved here for future login throttling hooks.
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if not user or not verify_password(password, user.password_hash):
            return None
        if not user.is_active or not user.is_verified:
            return None

        session = RefreshTokenSession(
            user_id=user.id,
            refresh_token_hash="pending",
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        await db.flush()

        token_pair = create_token_pair(user.id, session.id)
        session.refresh_token_hash = hash_token_value(token_pair["refresh_token"])
        await db.commit()
        return {"user": user, **token_pair}

    async def logout(self, db: AsyncSession, redis: Redis, refresh_token: str) -> bool:
        """Revoke refresh token session.

        Args:
            db: Active database session.
            redis: Redis client used for revocation cache.
            refresh_token: Raw refresh token to revoke.
        Returns:
            bool: True when session was revoked.
        """
        payload = decode_jwt(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return False

        session_id = str(payload.get("sid"))
        session = await db.get(RefreshTokenSession, session_id)
        if not session:
            return False
        if session.refresh_token_hash != hash_token_value(refresh_token):
            return False

        session.is_revoked = True
        session.revoked_at = datetime.now(UTC)
        await db.commit()

        now_value = (
            datetime.now(UTC).replace(tzinfo=None)
            if session.expires_at.tzinfo is None
            else datetime.now(UTC)
        )
        ttl_seconds = max(1, int((session.expires_at - now_value).total_seconds()))
        await redis.setex(f"session:revoked:{session.id}", ttl_seconds, "1")
        return True

    async def forgot_password(self, db: AsyncSession, email: str) -> None:
        """Create and email password reset token.

        Args:
            db: Active database session.
            email: User email to reset.
        Returns:
            None: Sends password reset email when user exists.
        """
        email_service = EmailService()
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if not user:
            return

        raw_token = generate_secure_token()
        token_row = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token_value(raw_token),
            expires_at=datetime.now(UTC) + timedelta(minutes=self.settings.PASSWORD_RESET_EXPIRE_MINUTES),
        )
        db.add(token_row)
        await db.commit()
        email_service.send_password_reset_email(user.email, raw_token)

    async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> bool:
        """Reset user password with valid reset token.

        Args:
            db: Active database session.
            token: Raw reset token.
            new_password: New plaintext password.
        Returns:
            bool: True when password is updated.
        """
        token_hash = hash_token_value(token)
        stmt: Select[tuple[PasswordResetToken]] = (
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .order_by(desc(PasswordResetToken.created_at))
        )
        token_row = await db.scalar(stmt)
        if not token_row or token_row.used_at or self._is_expired(token_row.expires_at):
            return False

        user = await db.get(User, token_row.user_id)
        if not user:
            return False

        token_row.used_at = datetime.now(UTC)
        user.password_hash = hash_password(new_password)
        await db.commit()
        return True

    async def request_otp(self, db: AsyncSession, email: str) -> None:
        """Issue OTP code and send by email.

        Args:
            db: Active database session.
            email: User email for OTP.
        Returns:
            None: Sends OTP email when eligible user exists.
        """
        email_service = EmailService()
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if not user or not user.is_active:
            return

        otp = generate_numeric_otp(6)
        otp_row = LoginOtpCode(
            user_id=user.id,
            otp_hash=hash_token_value(otp),
            expires_at=datetime.now(UTC) + timedelta(minutes=self.settings.OTP_EXPIRE_MINUTES),
            attempts=0,
        )
        db.add(otp_row)
        await db.commit()
        email_service.send_otp_email(user.email, otp)

    async def login_with_otp(self, db: AsyncSession, redis: Redis, email: str, otp: str) -> dict | None:
        """Authenticate user using email + OTP.

        Args:
            db: Active database session.
            redis: Redis client for future OTP throttling hooks.
            email: User email.
            otp: Raw OTP value.
        Returns:
            dict | None: Token payload and user when successful.
        """
        del redis
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if not user or not user.is_active:
            return None

        stmt: Select[tuple[LoginOtpCode]] = (
            select(LoginOtpCode)
            .where(
                and_(
                    LoginOtpCode.user_id == user.id,
                    LoginOtpCode.used_at.is_(None),
                )
            )
            .order_by(desc(LoginOtpCode.created_at))
        )
        otp_row = await db.scalar(stmt)
        if not otp_row or self._is_expired(otp_row.expires_at):
            return None
        if otp_row.attempts >= self.settings.OTP_MAX_ATTEMPTS:
            return None

        otp_row.attempts += 1
        if otp_row.otp_hash != hash_token_value(otp):
            await db.commit()
            return None

        otp_row.used_at = datetime.now(UTC)
        session = RefreshTokenSession(
            user_id=user.id,
            refresh_token_hash="pending",
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(session)
        await db.flush()

        token_pair = create_token_pair(user.id, session.id)
        session.refresh_token_hash = hash_token_value(token_pair["refresh_token"])
        await db.commit()
        return {"user": user, **token_pair}

    async def verify_access_token(self, db: AsyncSession, redis: Redis, token: str) -> dict | None:
        """Validate access token and ensure active session.

        Args:
            db: Active database session.
            redis: Redis client for revocation checks.
            token: Raw access token.
        Returns:
            dict | None: Token claims when valid.
        """
        payload = decode_jwt(token)
        if not payload or payload.get("type") != "access":
            return None

        session_id = str(payload.get("sid"))
        if await redis.get(f"session:revoked:{session_id}"):
            return None

        session = await db.get(RefreshTokenSession, session_id)
        if not session or session.is_revoked or self._is_expired(session.expires_at):
            return None
        return payload
