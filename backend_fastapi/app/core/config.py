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
