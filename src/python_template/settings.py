"""Every environment variable the service reads. Add new ones here so startup validates them."""

import sys
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["critical", "error", "warning", "info", "debug"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    port: int = Field(default=8080, ge=1, le=65535)
    log_level: LogLevel = "info"
    shutdown_drain_ms: int = Field(default=0, ge=0, le=60_000)


def problems(error: ValidationError) -> list[str]:
    """One line per invalid variable. Names the variable, never its value."""
    return [
        f"{'.'.join(str(part) for part in issue['loc']).upper()}: {issue['msg']}"
        for issue in error.errors(include_input=False)
    ]


def load_settings() -> Settings:
    """Reads the environment, or prints every problem and exits with status 1."""
    try:
        return Settings()
    except ValidationError as error:
        lines = "\n".join(f"  {line}" for line in problems(error))
        sys.stderr.write(f"Invalid configuration:\n{lines}\n")
        raise SystemExit(1) from None
