import re

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,62}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None, extra="ignore", populate_by_name=True, hide_input_in_errors=True
    )

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: SecretStr
    dev_db_name: str
    test_db_name: str
    app_db_name: str
    app_port: int
    uvicorn_port: int
    test_http_port: int
    client_port: int

    @field_validator("postgres_user", "dev_db_name", "test_db_name", "app_db_name")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        if not _NAME_PATTERN.fullmatch(value):
            raise ValueError("Must match [a-z][a-z0-9_]{0,62}")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.app_db_name,
        )

    def assert_test_target(self) -> None:
        if self.app_db_name != self.test_db_name or self.test_db_name == self.dev_db_name:
            raise ValueError("Refusing a database operation outside the test database")
