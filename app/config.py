from pydantic_settings import BaseSettings
from typing import List
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


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
            parts = urlsplit(self.DATABASE_URL)
            scheme = "postgresql+asyncpg" if parts.scheme in {"postgres", "postgresql"} else parts.scheme
            query = urlencode(
                [
                    (key, value)
                    for key, value in parse_qsl(parts.query, keep_blank_values=True)
                    if key not in {"channel_binding", "sslmode"}
                ]
            )
            return urlunsplit((scheme, parts.netloc, parts.path, query, parts.fragment))
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def db_ssl_required(self) -> bool:
        if not self.DATABASE_URL:
            return False
        return dict(parse_qsl(urlsplit(self.DATABASE_URL).query)).get("sslmode") in {
            "require", "verify-ca", "verify-full"
        }

    class Config:
        env_file = ".env"


settings = Settings()
