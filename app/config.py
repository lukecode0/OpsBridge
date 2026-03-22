from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "OpsBridge"
    environment: str = "dev"
    delivery_mode: str = "mock"
    default_channel: str = "email"
    enabled_channels: tuple[str, ...] = ("email", "slack")
    persistence_backend: str = "in_memory"
    database_url: str | None = None
    sqlite_path: str = "./opsbridge-dev.db"


def get_settings() -> Settings:
    default_channel = os.getenv("OPSBRIDGE_DEFAULT_CHANNEL", "email").strip().lower() or "email"
    raw_channels = os.getenv("OPSBRIDGE_ENABLED_CHANNELS", "email,slack")
    parsed_channels = tuple(
        dict.fromkeys(
            channel.strip().lower()
            for channel in raw_channels.split(",")
            if channel.strip()
        )
    )
    enabled_channels = parsed_channels or (default_channel,)
    if default_channel not in enabled_channels:
        enabled_channels = (default_channel, *enabled_channels)

    return Settings(
        app_name=os.getenv("OPSBRIDGE_APP_NAME", "OpsBridge"),
        environment=os.getenv("OPSBRIDGE_ENV", "dev"),
        delivery_mode=os.getenv("OPSBRIDGE_DELIVERY_MODE", "mock").strip().lower() or "mock",
        default_channel=default_channel,
        enabled_channels=enabled_channels,
        persistence_backend=(
            os.getenv("OPSBRIDGE_PERSISTENCE_BACKEND", "in_memory").strip().lower()
            or "in_memory"
        ),
        database_url=os.getenv("OPSBRIDGE_DATABASE_URL") or None,
        sqlite_path=os.getenv("OPSBRIDGE_SQLITE_PATH", "./opsbridge-dev.db"),
    )
