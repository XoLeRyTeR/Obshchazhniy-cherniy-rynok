from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class Database:
    def __init__(self, url: str, schema: str | None = None):
        connect_args = {"server_settings": {"search_path": schema}} if schema else {}
        self.engine = create_async_engine(url, pool_pre_ping=True, echo=False, connect_args=connect_args)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def close(self):
        await self.engine.dispose()

