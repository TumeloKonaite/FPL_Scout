from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.app.api.routes.chat import router as chat_router
from src.app.api.routes.health import router as health_router
from src.app.api.routes.pipeline_runs import router as pipeline_runs_router
from src.app.api.routes.reports import router as reports_router
from src.app.core.config import bootstrap_data_directories
from src.app.core.dependencies import get_app_settings


def load_runtime_environment() -> None:
    """Load .env into os.environ for SDKs that do not use app settings."""
    repo_root = Path(__file__).resolve().parents[3]
    candidates = (Path.cwd() / ".env", repo_root / ".env")

    for env_file in candidates:
        if env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
            return


def create_app() -> FastAPI:
    load_runtime_environment()
    settings = get_app_settings()
    bootstrap_data_directories(settings)
    app = FastAPI(title="FPL Technocrat API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "FPL Technocrat API"}

    app.include_router(health_router)
    app.include_router(reports_router)
    app.include_router(pipeline_runs_router)
    app.include_router(chat_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
