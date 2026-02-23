"""Initial auth, RBAC, and file schema.

Revision ID: 20260220_0001
Revises:
Create Date: 2026-02-20 00:00:00
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260220_0001"
down_revision = None
branch_labels = None
depends_on = None


def _now() -> datetime:
    """Return timezone-aware UTC now.

    Args:
        None
    Returns:
        datetime: Current UTC datetime.
    """
    return datetime.now(timezone.utc)


def upgrade() -> None:
    """Apply initial auth and RBAC schema migration.

    Args:
        None
    Returns:
        None: Creates tables and baseline RBAC seed data.
    """
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "groups",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_groups_name", "groups", ["name"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    op.create_table(
        "user_groups",
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("group_id", sa.String(length=32), sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "group_id", name="uq_user_group"),
    )

    op.create_table(
        "group_permissions",
        sa.Column(
            "group_id",
            sa.String(length=32),
            sa.ForeignKey("groups.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            sa.String(length=32),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("group_id", "permission_id", name="uq_group_permission"),
    )

    op.create_table(
        "refresh_token_sessions",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_token_sessions_user_id", "refresh_token_sessions", ["user_id"], unique=False)

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"], unique=False)
    op.create_index(
        "ix_email_verification_tokens_token_hash", "email_verification_tokens", ["token_hash"], unique=False
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False)
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=False)

    op.create_table(
        "login_otp_codes",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("otp_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_otp_codes_user_id", "login_otp_codes", ["user_id"], unique=False)
    op.create_index("ix_login_otp_codes_otp_hash", "login_otp_codes", ["otp_hash"], unique=False)

    op.create_table(
        "file_assets",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("owner_id", sa.String(length=32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_file_assets_owner_id", "file_assets", ["owner_id"], unique=False)
    op.create_index("ix_file_assets_object_key", "file_assets", ["object_key"], unique=True)

    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    groups_table = sa.table(
        "groups",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    group_perms_table = sa.table(
        "group_permissions",
        sa.column("group_id", sa.String()),
        sa.column("permission_id", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    now = _now()
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": "PRM_SEED_USERS_READ",
                "code": "users.read",
                "description": "Read user profiles",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "PRM_SEED_USERS_PROFILE_UPLOAD",
                "code": "users.profile.upload",
                "description": "Upload user profile pictures",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    op.bulk_insert(
        groups_table,
        [
            {
                "id": "GRP_SEED_ADMIN",
                "name": "admin",
                "description": "Default administrator group",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "GRP_SEED_MEMBER",
                "name": "member",
                "description": "Default member group for new users",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    op.bulk_insert(
        group_perms_table,
        [
            {
                "group_id": "GRP_SEED_ADMIN",
                "permission_id": "PRM_SEED_USERS_READ",
                "created_at": now,
                "updated_at": now,
            },
            {
                "group_id": "GRP_SEED_ADMIN",
                "permission_id": "PRM_SEED_USERS_PROFILE_UPLOAD",
                "created_at": now,
                "updated_at": now,
            },
            {
                "group_id": "GRP_SEED_MEMBER",
                "permission_id": "PRM_SEED_USERS_PROFILE_UPLOAD",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    """Rollback initial auth and RBAC schema.

    Args:
        None
    Returns:
        None: Drops seeded tables in reverse dependency order.
    """
    op.drop_index("ix_file_assets_object_key", table_name="file_assets")
    op.drop_index("ix_file_assets_owner_id", table_name="file_assets")
    op.drop_table("file_assets")

    op.drop_index("ix_login_otp_codes_otp_hash", table_name="login_otp_codes")
    op.drop_index("ix_login_otp_codes_user_id", table_name="login_otp_codes")
    op.drop_table("login_otp_codes")

    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_email_verification_tokens_token_hash", table_name="email_verification_tokens")
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")

    op.drop_index("ix_refresh_token_sessions_user_id", table_name="refresh_token_sessions")
    op.drop_table("refresh_token_sessions")

    op.drop_table("group_permissions")
    op.drop_table("user_groups")

    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_groups_name", table_name="groups")
    op.drop_table("groups")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
