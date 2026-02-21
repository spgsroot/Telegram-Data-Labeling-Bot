from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    token: str
    database_url: str = "postgresql+asyncpg://bot:bot@db:5432/labeling"
    redis_url: str = "redis://redis:6379/0"
    admin_ids: list[int] = []
    lock_ttl_seconds: int = 900  # 15 min

    model_config = {"env_prefix": "BOT_", "env_file": ".env"}


settings = Settings()  # type: ignore[call-arg]
