from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.services.integrations import (
    IntegrationRouter,
    RecordedEmailGateway,
    RecordedSlackGateway,
)
from app.services.jobs import RecordedJobDispatcher
from app.services.repository import InMemoryIntakeRepository
from app.routes import install_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.intake_repository = InMemoryIntakeRepository()
    app.state.job_dispatcher = RecordedJobDispatcher()
    app.state.delivery_gateway = IntegrationRouter(
        email_gateway=RecordedEmailGateway(),
        slack_gateway=RecordedSlackGateway(),
    )
    app.state.templates = Jinja2Templates(directory="app/templates")
    install_routes(app)
    return app
