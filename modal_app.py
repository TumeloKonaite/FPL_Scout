"""Modal deployment entry point for the FastAPI service and pipeline worker."""

from __future__ import annotations

from pathlib import Path

import modal


APP_NAME = "fpl-technocrat"
SECRET_NAME = "fpl-scout-secrets"
PROJECT_ROOT = Path(__file__).parent

runtime_env = {
    "ENVIRONMENT": "production",
    "DATABASE_POOL_MODE": "transaction",
    "DATABASE_POOL_SIZE": "2",
    "DATABASE_MAX_OVERFLOW": "1",
    "DATABASE_POOL_TIMEOUT_SECONDS": "10",
    "DATABASE_POOL_RECYCLE_SECONDS": "300",
    "DATABASE_CONNECT_TIMEOUT_SECONDS": "5",
}

app = modal.App(APP_NAME)
runtime_secret = modal.Secret.from_name(SECRET_NAME)

backend_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ca-certificates", "ffmpeg")
    .uv_sync(str(PROJECT_ROOT), extra_options="--no-dev")
    .add_local_dir(
        PROJECT_ROOT,
        "/app",
        copy=True,
        ignore=[".env", ".git", ".venv", "data", "frontend", "notebooks", "tests"],
    )
    .workdir("/app")
    .env(runtime_env)
)

@app.function(
    image=backend_image,
    secrets=[runtime_secret],
    timeout=60 * 60,
)
def pipeline_worker(run_id: str, input_data: dict) -> dict:
    from src.app.domain.pipeline.service import execute_pipeline_run
    from src.app.infrastructure.database import require_database_ready

    require_database_ready()
    try:
        return execute_pipeline_run(run_id, input_data)
    finally:
        from src.app.infrastructure.database import dispose_engine

        dispose_engine()


@app.function(
    image=backend_image,
    secrets=[runtime_secret],
    timeout=300,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def api():
    from src.app.domain.pipeline.service import configure_pipeline_dispatcher
    from src.app.main import app as fastapi_app
    from src.app.infrastructure.database import require_database_ready

    configure_pipeline_dispatcher(lambda run_id, payload: pipeline_worker.spawn(run_id, payload))
    require_database_ready()
    return fastapi_app


@app.function(
    image=backend_image,
    secrets=[runtime_secret],
    timeout=10 * 60,
)
def migrate() -> None:
    """Run the controlled production migration and revision checks."""
    from alembic import command
    from alembic.config import Config

    config = Config("/app/alembic.ini")
    command.upgrade(config, "head")
    command.current(config, check_heads=True)
    command.check(config)


@app.function(
    image=backend_image,
    secrets=[runtime_secret],
    timeout=5 * 60,
)
def verify_database() -> dict[str, int]:
    """Verify required tables, indexes, counts, and revision relationships."""
    import json

    from src.scripts.verify_database import verify_database_schema

    result = verify_database_schema()
    print(json.dumps(result, sort_keys=True))
    return result
