"""Attachment storage on MinIO (S3 API).

Objects are private; the API hands out short-lived presigned URLs rather than
proxying bytes, so a leaked URL expires on its own.
"""

from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings
from app.core.errors import ServiceUnavailable
from app.core.logging import get_logger

log = get_logger(__name__)

_session = aioboto3.Session()
_config = Config(signature_version="s3v4", retries={"max_attempts": 2})

#: Only formats a claimant plausibly attaches to a telecom complaint.
ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "application/pdf",
    "text/plain",
}


def _client() -> Any:
    return _session.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=_config,
    )


async def ensure_bucket() -> None:
    """Create the bucket on first boot. Safe to call repeatedly."""
    async with _client() as s3:
        try:
            await s3.head_bucket(Bucket=settings.s3_bucket)
        except ClientError:
            await s3.create_bucket(Bucket=settings.s3_bucket)
            log.info("storage.bucket_created", bucket=settings.s3_bucket)


async def put_object(key: str, data: bytes, content_type: str) -> None:
    try:
        async with _client() as s3:
            await s3.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
    except ClientError as exc:
        log.error("storage.put_failed", key=key, error=str(exc))
        raise ServiceUnavailable("Stockage des pieces jointes indisponible") from exc


async def presigned_url(key: str, expires_in: int = 900) -> str:
    async with _client() as s3:
        return await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expires_in,
        )


async def delete_object(key: str) -> None:
    try:
        async with _client() as s3:
            await s3.delete_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:  # deletion is best-effort; never fail the request
        log.warning("storage.delete_failed", key=key, error=str(exc))


async def health() -> bool:
    try:
        async with _client() as s3:
            await s3.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        return False
    return True
