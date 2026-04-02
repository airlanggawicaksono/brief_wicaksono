from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_RELOAD: bool = True

    DB_USER: str = "wpp"
    DB_PASSWORD: str = "wpp_dev_password"
    DB_NAME: str = "wpp_db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
