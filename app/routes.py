from fastapi import FastAPI


def install_routes(app: FastAPI) -> None:
    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}
