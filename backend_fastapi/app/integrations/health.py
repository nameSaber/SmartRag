from dataclasses import dataclass
import socket
from urllib.parse import urlparse

from elasticsearch import Elasticsearch
from minio import Minio
from redis import Redis

from app.core.config import settings


@dataclass
class DependencyStatus:
    name: str
    status: str
    message: str = ""

    def as_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "message": self.message}


def dependency_health() -> dict:
    # 健康检查必须容错：单个依赖不可用不能影响应用进程本身启动。
    statuses = [
        check_mysql_url(),
        check_redis(),
        check_elasticsearch(),
        check_kafka(),
        check_minio(),
    ]
    overall = "UP" if all(item.status == "UP" for item in statuses) else "DEGRADED"
    return {"status": overall, "dependencies": {item.name: item.as_dict() for item in statuses}}


def check_mysql_url() -> DependencyStatus:
    parsed = urlparse(settings.database_url.replace("+pymysql", ""))
    if parsed.scheme.startswith("sqlite"):
        return DependencyStatus("mysql", "SKIPPED", "当前使用 SQLite")
    return _tcp_check("mysql", parsed.hostname or "localhost", parsed.port or 3306)


def check_redis() -> DependencyStatus:
    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1).ping()
        return DependencyStatus("redis", "UP")
    except Exception as exc:  # noqa: BLE001 - 健康检查需要捕获依赖库差异化异常
        return DependencyStatus("redis", "DOWN", str(exc))


def check_elasticsearch() -> DependencyStatus:
    try:
        client = Elasticsearch(settings.es_url, request_timeout=1)
        return DependencyStatus("elasticsearch", "UP" if client.ping() else "DOWN")
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus("elasticsearch", "DOWN", str(exc))


def check_kafka() -> DependencyStatus:
    host, port = _split_host_port(settings.kafka_bootstrap_servers.split(",")[0], 9092)
    return _tcp_check("kafka", host, port)


def check_minio() -> DependencyStatus:
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        client.list_buckets()
        return DependencyStatus("minio", "UP")
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus("minio", "DOWN", str(exc))


def _tcp_check(name: str, host: str, port: int) -> DependencyStatus:
    try:
        with socket.create_connection((host, port), timeout=1):
            return DependencyStatus(name, "UP")
    except Exception as exc:  # noqa: BLE001
        return DependencyStatus(name, "DOWN", str(exc))


def _split_host_port(value: str, default_port: int) -> tuple[str, int]:
    host, _, port_text = value.partition(":")
    return host or "localhost", int(port_text or default_port)
