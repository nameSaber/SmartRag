from dataclasses import dataclass
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


@dataclass(frozen=True)
class ObjectRef:
    bucket: str
    key: str


class MinioObjectStorage:
    def __init__(self, client: Minio | None = None, bucket: str | None = None):
        self.client = client or Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = bucket or settings.minio_bucket

    def ensure_bucket(self) -> None:
        # MinIO bucket 是上传链路的持久化边界，首次写入前确保存在。
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_bytes(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> ObjectRef:
        self.ensure_bucket()
        self.client.put_object(self.bucket, key, BytesIO(content), length=len(content), content_type=content_type)
        return ObjectRef(bucket=self.bucket, key=key)

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return False
            raise


def chunk_key(file_md5: str, chunk_index: int) -> str:
    return f"chunks/{file_md5}/{chunk_index}"


def document_key(file_md5: str, file_name: str) -> str:
    return f"documents/{file_md5}/{file_name}"


def get_object_storage() -> MinioObjectStorage:
    return MinioObjectStorage()
