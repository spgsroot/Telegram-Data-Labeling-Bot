#!/bin/sh
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting bot..."
exec uv run python -m bot
