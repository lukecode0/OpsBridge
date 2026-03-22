from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "OpsBridge"
    environment: str = "dev"


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("OPSBRIDGE_APP_NAME", "OpsBridge"),
        environment=os.getenv("OPSBRIDGE_ENV", "dev"),
    )
