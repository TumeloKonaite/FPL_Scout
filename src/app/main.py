from __future__ import annotations

from fastapi import FastAPI

from src.app.api.routes.chat import router as chat_router
from src.app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="FPL Technocrat API")

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "FPL Technocrat API"}

    app.include_router(health_router)
    app.include_router(chat_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
