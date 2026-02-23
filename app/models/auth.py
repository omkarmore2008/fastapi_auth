"""Authentication and RBAC related SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, PrefixedIDModel, TimestampedModel, prefixed_id


class User(Base, PrefixedIDModel, TimestampedModel):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("USR"))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    groups: Mapped[list[UserGroup]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_sessions: Mapped[list[RefreshTokenSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_tokens: Mapped[list[EmailVerificationToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    otp_codes: Mapped[list[LoginOtpCode]] = relationship(back_populates="user", cascade="all, delete-orphan")
    files: Mapped[list[FileAsset]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Group(Base, PrefixedIDModel, TimestampedModel):
    """Group model for role-style permission assignment."""

    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("GRP"))
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list[UserGroup]] = relationship(back_populates="group", cascade="all, delete-orphan")
    permissions: Mapped[list[GroupPermission]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Permission(Base, PrefixedIDModel, TimestampedModel):
    """Permission model for fine-grained access control."""

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("PRM"))
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    groups: Mapped[list[GroupPermission]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class UserGroup(Base, TimestampedModel):
    """User to group join table."""

    __tablename__ = "user_groups"
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped[User] = relationship(back_populates="groups")
    group: Mapped[Group] = relationship(back_populates="users")


class GroupPermission(Base, TimestampedModel):
    """Group to permission join table."""

    __tablename__ = "group_permissions"
    __table_args__ = (UniqueConstraint("group_id", "permission_id", name="uq_group_permission"),)

    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    group: Mapped[Group] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="groups")


class RefreshTokenSession(Base, PrefixedIDModel, TimestampedModel):
    """Stores refresh token session lifecycle for logout/invalidation."""

    __tablename__ = "refresh_token_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("RTS"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="refresh_sessions")


class EmailVerificationToken(Base, PrefixedIDModel, TimestampedModel):
    """Email verification token model."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("EVT"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="email_tokens")


class PasswordResetToken(Base, PrefixedIDModel, TimestampedModel):
    """Password reset token model."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("PRT"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="reset_tokens")


class LoginOtpCode(Base, PrefixedIDModel, TimestampedModel):
    """One-time password login token model."""

    __tablename__ = "login_otp_codes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("OTP"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="otp_codes")


class FileAsset(Base, PrefixedIDModel, TimestampedModel):
    """Metadata for files stored in AWS S3."""

    __tablename__ = "file_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: prefixed_id("FIL"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), default="profile_picture", nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship(back_populates="files")
