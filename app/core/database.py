import re
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import create_engine
from app.core.config import settings


def _fix_url(raw: str, driver: str) -> str:
    """
    Convert any postgres URL variant to the correct SQLAlchemy driver URL,
    and remove an empty port (host:/) before any library sees it.
    """
    # Remove empty port: "host:/" -> "host/" but leave "://" alone
    url = re.sub(r'(?<=[^:]):/(?=[^/])', '/', raw)

    # Replace scheme
    for prefix in (
        "postgresql+asyncpg://",
        "postgresql+psycopg2://",
        "postgresql://",
        "postgres://",
    ):
        if url.startswith(prefix):
            url = f"postgresql+{driver}://" + url[len(prefix):]
            break

    return url


# Async engine for FastAPI
engine = create_async_engine(
    _fix_url(settings.DATABASE_URL, "asyncpg"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    connect_args={"timeout": 5},  # asyncpg: fail fast instead of hanging indefinitely
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
    _fix_url(settings.DATABASE_URL, "psycopg2"),
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
