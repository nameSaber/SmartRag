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
    file_processing_backend: str = "local"
    file_processing_topic: str = "file-processing"
    minio_endpoint: str = "localhost:19000"
    minio_access_key: str = "admin"
    minio_secret_key: str = "PaiSmart2025"
    minio_secure: bool = False
    minio_bucket: str = "pai-smart"
    object_storage_backend: str = "database"
    search_backend: str = "database"
    es_index_name: str = "pai_smart_documents"
    llm_backend: str = "mock"
    llm_api_base_url: str = ""
    llm_api_key: str = ""
    llm_model_name: str = "gpt-compatible"
    llm_timeout_seconds: int = 30
    embedding_backend: str = "mock"
    embedding_api_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model_name: str = "embedding-compatible"
    embedding_dimension: int = 8
    wx_pay_callback_secret: str = ""
    rate_limit_backend: str = "memory"
    admin_dangerous_operations_enabled: bool = False
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
