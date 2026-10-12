from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "apivita_db"
    DB_USER: str = "apivita_user"
    DB_PASSWORD: str = ""
    DATABASE_URL: str = ""
    WEBAPP_URL: str = ""
    REDIS_URL: str = ""
    WEBHOOK_SECRET: str = ""
    VERCEL: bool = False
    DEFAULT_LANG: str = "ru"
    LOG_LEVEL: str = "INFO"

    @property
    def admin_ids_list(self) -> List[int]:
        return [int(x.strip()) for x in self.ADMIN_IDS.split(',') if x.strip()]

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
