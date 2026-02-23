"""AWS S3 storage service for profile pictures and files."""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import get_settings


class S3StorageService:
    """Handles object uploads to S3-compatible storage."""

    def __init__(self) -> None:
        """Initialize S3 client from env config.

        Args:
            None
        Returns:
            None: Creates service with boto3 client.
        """
        self.settings = get_settings()
        self.bucket = self.settings.AWS_S3_BUCKET
        self.endpoint_url = self.settings.AWS_S3_ENDPOINT_URL
        # MinIO/local S3 providers typically need path-style URL routing.
        use_path_style = bool(self.endpoint_url)
        self.client = boto3.client(
            "s3",
            region_name=self.settings.AWS_REGION,
            aws_access_key_id=self.settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=self.endpoint_url or None,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path" if use_path_style else "auto"}),
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the target bucket exists for local MinIO/S3 usage.

        Args:
            None
        Returns:
            None: Creates bucket if it does not already exist.
        """
        if not self.bucket:
            raise ValueError("AWS_S3_BUCKET is required for file storage")

        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code not in {"404", "NoSuchBucket"}:
                raise

        create_kwargs: dict[str, object] = {"Bucket": self.bucket}
        if self.settings.AWS_REGION and self.settings.AWS_REGION != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": self.settings.AWS_REGION
            }
        self.client.create_bucket(**create_kwargs)

    def _build_object_url(self, object_key: str) -> str:
        """Build public URL for uploaded object.

        Args:
            object_key: Key stored in bucket.
        Returns:
            str: URL accessible in local/prod context.
        """
        if self.endpoint_url:
            parsed = urlparse(self.endpoint_url)
            base = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            return f"{base}/{self.bucket}/{object_key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{object_key}"

    async def upload_profile_asset(self, user_id: str, upload: UploadFile) -> dict[str, str]:
        """Upload profile asset to S3 and return metadata.

        Args:
            user_id: Owner user ID.
            upload: Uploaded file object from API.
        Returns:
            dict[str, str]: Uploaded object metadata and public URL.
        """
        content_type = upload.content_type or "application/octet-stream"
        ext = Path(upload.filename or "file.bin").suffix or ".bin"
        object_key = f"users/{user_id}/profile/{token_urlsafe(12)}{ext}"
        file_name = upload.filename or f"profile{ext}"

        self.client.upload_fileobj(
            upload.file,
            self.bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        url = self._build_object_url(object_key)
        return {
            "bucket": self.bucket,
            "object_key": object_key,
            "url": url,
            "mime_type": content_type,
            "file_name": file_name,
        }
