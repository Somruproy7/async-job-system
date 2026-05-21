from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from app.core.config import settings


def _build_url(raw: str, driver: str) -> str:
    """
    Parse the raw DATABASE_URL (any scheme variant Railway might provide),
    swap the driver, and strip any empty port so SQLAlchemy doesn't choke.
    """
    # Normalise scheme so make_url can parse it
    normalised = raw
    for prefix in ("postgres://", "postgresql://", "postgresql+asyncpg://", "postgresql+psycopg2://"):
        if normalised.startswith(prefix):
            normalised = "postgresql://" + normalised[len(prefix):]
            break

    u = make_url(normalised)

    # Rebuild with the correct driver and without an empty port
    return str(u.set(
        drivername=f"postgresql+{driver}",
        port=u.port if u.port else None,
    ))


# Async engine for FastAPI
engine = create_async_engine(
    _build_url(settings.DATABASE_URL, "asyncpg"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync engine for Celery tasks
sync_engine = create_engine(
    _build_url(settings.DATABASE_URL, "psycopg2"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
