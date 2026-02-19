from pathlib import Path

import asyncpg
import structlog

from src.config import settings

log = structlog.get_logger()

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def ensure_database(self) -> None:
        """Create the target database if it doesn't exist."""
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database="postgres",
        )
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", settings.db_name
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{settings.db_name}"')
                log.info("Database created", db=settings.db_name)
        finally:
            await conn.close()

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            min_size=2,
            max_size=10,
        )
        log.info("Database connected", host=settings.db_host, db=settings.db_name)

    async def run_migrations(self) -> None:
        """Apply pending SQL migrations from migrations/ directory."""
        await self.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        applied = {
            r["filename"] for r in await self.fetch("SELECT filename FROM schema_migrations")
        }

        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if sql_file.name not in applied:
                sql = sql_file.read_text()
                await self.execute(sql)
                await self.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    sql_file.name,
                )
                log.info("Migration applied", filename=sql_file.name)

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            log.info("Database disconnected")

    async def execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)


db = Database()
