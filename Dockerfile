FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic/ alembic/
COPY bot/ bot/
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
