from fastapi import FastAPI

from app.config import get_settings
from app.services.jobs import RecordedJobDispatcher
from app.services.repository import InMemoryIntakeRepository
from app.routes import install_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.intake_repository = InMemoryIntakeRepository()
    app.state.job_dispatcher = RecordedJobDispatcher()
    install_routes(app)
    return app
