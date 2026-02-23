"""Shared API dependencies for auth and RBAC."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_jwt
from app.db.session import get_db_session, get_redis
from app.models.auth import User
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> User:
    """Return authenticated user from bearer access token.

    Args:
        credentials: Authorization bearer credentials.
        db: Active database session.
        redis: Redis client for revocation checks.
    Returns:
        User: Authenticated user model.
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    auth_service = AuthService()
    payload = await auth_service.verify_access_token(db=db, redis=redis, token=credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await db.get(User, str(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_permission(permission_code: str):
    """Create dependency that validates a required permission.

    Args:
        permission_code: Permission code to enforce.
    Returns:
        callable: FastAPI dependency function.
    """

    async def dependency(
        db: AsyncSession = Depends(get_db_session),
        user: User = Depends(get_current_user),
    ) -> User:
        rbac = RBACService()
        if not await rbac.has_permission(db=db, user_id=user.id, code=permission_code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return user

    return dependency


async def get_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Decode token claims without DB checks.

    Args:
        credentials: Authorization bearer credentials.
    Returns:
        dict: Decoded JWT claims.
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    payload = decode_jwt(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload
