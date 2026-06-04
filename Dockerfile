FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.8.15 /uv /uvx /bin/

COPY . .

RUN uv sync --frozen --no-dev && mkdir -p data/reports data/raw data/processed data/transcripts

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.app.main:app", "--host=0.0.0.0", "--port=8000"]
