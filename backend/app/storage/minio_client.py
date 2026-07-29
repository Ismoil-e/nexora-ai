import io
from datetime import timedelta

from minio import Minio

from app.core.config import settings


class MinioClient:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ensure_bucket(settings.minio_bucket)

    def _ensure_bucket(self, bucket: str):
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    async def upload_file(self, bucket: str, file_data: bytes, filename: str,
                           content_type: str = "application/octet-stream") -> str:
        from uuid import uuid4
        from datetime import datetime

        object_name = f"uploads/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4().hex}-{filename}"
        file_size = len(file_data)

        self._ensure_bucket(bucket)

        self.client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=io.BytesIO(file_data),
            length=file_size,
            content_type=content_type,
        )

        return object_name

    async def get_file_url(self, bucket: str, object_name: str, expires: int = 3600) -> str:
        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires),
        )

    async def delete_file(self, object_name: str, bucket: str | None = None):
        bucket = bucket or settings.minio_bucket
        self.client.remove_object(bucket, object_name)

    async def file_exists(self, object_name: str, bucket: str | None = None) -> bool:
        bucket = bucket or settings.minio_bucket
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except Exception:
            return False
