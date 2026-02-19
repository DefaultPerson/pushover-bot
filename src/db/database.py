import asyncpg
import structlog

from src.config import settings

log = structlog.get_logger()


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

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
