"""Modal deployment entry point for the FastAPI service and pipeline worker."""

from __future__ import annotations

from pathlib import Path

import modal


APP_NAME = "fpl-technocrat"
VOLUME_NAME = "fpl-scout-data"
SECRET_NAME = "fpl-scout-secrets"
DATA_MOUNT = "/data"
PROJECT_ROOT = Path(__file__).parent

runtime_env = {
    "DATA_DIR": DATA_MOUNT,
    "REPORTS_DIR": f"{DATA_MOUNT}/reports",
    "RAW_DATA_DIR": f"{DATA_MOUNT}/raw",
    "PROCESSED_DATA_DIR": f"{DATA_MOUNT}/processed",
    "TRANSCRIPTS_DIR": f"{DATA_MOUNT}/transcripts",
    "RUNS_DIR": f"{DATA_MOUNT}/runs",
    "ENVIRONMENT": "production",
    "TRANSCRIPT_STORE": "postgres",
    "TRANSCRIPT_FILE_FALLBACK_ENABLED": "false",
    "DATABASE_POOL_MODE": "transaction",
    "DATABASE_POOL_SIZE": "2",
    "DATABASE_MAX_OVERFLOW": "1",
    "DATABASE_POOL_TIMEOUT_SECONDS": "10",
    "DATABASE_POOL_RECYCLE_SECONDS": "300",
    "DATABASE_CONNECT_TIMEOUT_SECONDS": "5",
}

app = modal.App(APP_NAME)
data_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
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
    volumes={DATA_MOUNT: data_volume},
)
def pipeline_worker(run_id: str, input_data: dict) -> dict:
    from src.app.core.config import bootstrap_data_directories
    from src.app.domain.pipeline.service import execute_pipeline_run
    from src.app.infrastructure.storage.runtime_volume import configure_runtime_volume
    from src.app.infrastructure.database import require_database_ready

    configure_runtime_volume(commit=data_volume.commit, reload=data_volume.reload)
    bootstrap_data_directories()
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
    volumes={DATA_MOUNT: data_volume},
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def api():
    from src.app.domain.pipeline.service import configure_pipeline_dispatcher
    from src.app.infrastructure.storage.runtime_volume import configure_runtime_volume
    from src.app.main import app as fastapi_app
    from src.app.infrastructure.database import require_database_ready

    configure_runtime_volume(commit=data_volume.commit, reload=data_volume.reload)
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
