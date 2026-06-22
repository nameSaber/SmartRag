from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PaiSmart FastAPI"
    database_url: str = "sqlite:///./pai_smart_dev.db"
    jwt_secret_key: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 14
    registration_mode: str = "OPEN"
    redis_url: str = "redis://:PaiSmart2025@localhost:6379/0"
    es_url: str = "http://elastic:PaiSmart2025@localhost:9200"
    kafka_bootstrap_servers: str = "localhost:9092"
    minio_endpoint: str = "localhost:19000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "PaiSmart2025"
    minio_secure: bool = False
    minio_bucket: str = "pai-smart"
    object_storage_backend: str = "database"
    search_backend: str = "database"
    es_index_name: str = "pai_smart_documents"
    default_org_tag: str = "default"
    default_org_name: str = "默认组织"
    initial_llm_tokens: int = 100000
    initial_embedding_tokens: int = 100000
    auto_create_schema: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
