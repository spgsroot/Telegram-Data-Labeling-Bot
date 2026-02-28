#!/bin/sh
set -e

# If the schema tables already exist but Alembic hasn't tracked them yet,
# stamp the initial migration to avoid "relation already exists" errors.
uv run python -c "
import asyncio, os

async def maybe_stamp():
    import asyncpg
    user = os.environ.get('POSTGRES_USER', 'bot')
    password = os.environ.get('POSTGRES_PASSWORD', 'bot')
    db = os.environ.get('POSTGRES_DB', 'labeling')
    dsn = f'postgresql://{user}:{password}@db:5432/{db}'
    conn = await asyncpg.connect(dsn)
    has_alembic = await conn.fetchval(
        \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version')\"
    )
    has_users = await conn.fetchval(
        \"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='users')\"
    )
    await conn.close()
    if not has_alembic and has_users:
        print('Schema exists without alembic tracking, stamping 0001...')
        import subprocess
        subprocess.run(['uv', 'run', 'alembic', 'stamp', '0001'], check=True)
    else:
        print('Alembic state OK, proceeding.')

asyncio.run(maybe_stamp())
"

echo "Running database migrations..."
uv run alembic upgrade head

echo "Starting bot..."
exec uv run python -m bot
