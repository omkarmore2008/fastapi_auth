"""User API endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db_session
from app.models.auth import FileAsset, User
from app.schemas.user import PermissionRead, UploadProfileResponse, UserPermissionsResponse, UserRead
from app.services.rbac_service import RBACService
from app.services.storage_service import S3StorageService

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Return current authenticated user.

    Args:
        current_user: Authenticated user from dependency.
    Returns:
        UserRead: Current user profile.
    """
    return UserRead.model_validate(current_user)


@router.get("/me/permissions", response_model=UserPermissionsResponse)
async def list_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserPermissionsResponse:
    """Return effective permissions for current user.

    Args:
        current_user: Authenticated user from dependency.
        db: Active database session.
    Returns:
        UserPermissionsResponse: Permission list for current user.
    """
    rbac = RBACService()
    permissions = sorted(await rbac.list_permissions_for_user(db=db, user_id=current_user.id))
    return UserPermissionsResponse(
        user_id=current_user.id,
        permissions=[PermissionRead(code=perm) for perm in permissions],
    )


@router.post("/me/profile-picture", response_model=UploadProfileResponse)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("users.profile.upload")),
    db: AsyncSession = Depends(get_db_session),
) -> UploadProfileResponse:
    """Upload and store profile picture to S3.

    Args:
        file: Uploaded image file.
        current_user: Authenticated user from dependency.
        db: Active database session.
    Returns:
        UploadProfileResponse: Stored file metadata.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed")

    storage = S3StorageService()
    uploaded = await storage.upload_profile_asset(current_user.id, file)

    asset = FileAsset(
        owner_id=current_user.id,
        bucket=uploaded["bucket"],
        object_key=uploaded["object_key"],
        url=uploaded["url"],
        mime_type=uploaded["mime_type"],
        file_name=uploaded["file_name"],
        purpose="profile_picture",
    )
    db.add(asset)
    current_user.avatar_url = uploaded["url"]
    await db.commit()
    await db.refresh(asset)

    return UploadProfileResponse(
        file_id=asset.id,
        file_url=asset.url,
        mime_type=asset.mime_type,
        file_name=asset.file_name,
    )
