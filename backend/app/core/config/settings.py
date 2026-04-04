from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_HOST: str
    APP_PORT: int
    APP_RELOAD: bool

    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int

    LLM_PROVIDER: Literal["openai", "claude", "gemini"] = "openai"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = ""

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = ""

    GOOGLE_API_KEY: str = ""
    GOOGLE_MODEL: str = ""

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
