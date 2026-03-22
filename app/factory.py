from fastapi import FastAPI

from app.config import get_settings
from app.routes import install_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    install_routes(app)
    return app
