from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


class Database:
    def __init__(self, settings: Settings):
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            echo=False,
            hide_parameters=True,
            pool_pre_ping=True,
            connect_args={"timeout": 2, "command_timeout": 5},
        )
        self.sessions: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def close(self) -> None:
        await self._engine.dispose()
