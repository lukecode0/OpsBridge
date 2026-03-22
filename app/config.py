from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "OpsBridge"
    environment: str = "dev"
    delivery_mode: str = "mock"
    default_channel: str = "email"
    enabled_channels: tuple[str, ...] = ("email", "slack")


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
    )
