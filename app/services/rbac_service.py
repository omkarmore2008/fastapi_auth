"""RBAC service for resolving and checking user permissions."""

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import GroupPermission, Permission, UserGroup


class RBACService:
    """Service class for permission checks."""

    async def list_permissions_for_user(self, db: AsyncSession, user_id: str) -> set[str]:
        """List effective permission codes for a user.

        Args:
            db: Active database session.
            user_id: User identifier.
        Returns:
            set[str]: Permission code set resolved from user groups.
        """
        stmt: Select[tuple[str]] = (
            select(Permission.code)
            .join(GroupPermission, GroupPermission.permission_id == Permission.id)
            .join(UserGroup, UserGroup.group_id == GroupPermission.group_id)
            .where(UserGroup.user_id == user_id)
        )
        rows = (await db.execute(stmt)).all()
        return {row[0] for row in rows}

    async def has_permission(self, db: AsyncSession, user_id: str, code: str) -> bool:
        """Check whether user has a specific permission code.

        Args:
            db: Active database session.
            user_id: User identifier.
            code: Permission code string.
        Returns:
            bool: True when user has that permission.
        """
        perms = await self.list_permissions_for_user(db, user_id)
        return code in perms
