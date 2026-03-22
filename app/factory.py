from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.persistence.factory import build_repository
from app.services.integrations import (
    IntegrationRouter,
    RecordedEmailGateway,
    RecordedSlackGateway,
)
from app.services.jobs import RecordedJobDispatcher
from app.routes import install_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    repository, persistence_status = build_repository(settings)
    app.state.intake_repository = repository
    app.state.persistence_status = persistence_status
    app.state.job_dispatcher = RecordedJobDispatcher()
    app.state.delivery_gateway = IntegrationRouter(
        email_gateway=RecordedEmailGateway(
            provider_name=f"{settings.delivery_mode}-email"
        ),
        slack_gateway=RecordedSlackGateway(
            provider_name=f"{settings.delivery_mode}-slack"
        ),
        default_channel=settings.default_channel,
        enabled_channels=settings.enabled_channels,
    )
    app.state.templates = Jinja2Templates(directory="app/templates")
    install_routes(app)
    return app
