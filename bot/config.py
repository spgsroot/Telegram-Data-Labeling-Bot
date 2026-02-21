import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    token: str
    database_url: str = ""
    redis_url: str = "redis://redis:6379/0"
    admin_ids: list[int] = []
    lock_ttl_seconds: int = 900  # 15 min

    model_config = {"env_prefix": "BOT_", "env_file": ".env"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.database_url:
            user = os.getenv("POSTGRES_USER", "bot")
            password = os.getenv("POSTGRES_PASSWORD", "bot")
            db = os.getenv("POSTGRES_DB", "labeling")
            self.database_url = f"postgresql+asyncpg://{user}:{password}@db:5432/{db}"


settings = Settings()  # type: ignore[call-arg]
