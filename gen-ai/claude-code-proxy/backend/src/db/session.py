from typing import AsyncGenerator
import ssl
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from ..config import get_settings

settings = get_settings()

# Determine if SSL is needed (AWS RDS/Aurora requires SSL)
connect_args = {}
if settings.database_url_arn or "amazonaws.com" in settings.database_url:
    # Create SSL context for Aurora/RDS connections
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE  # Aurora uses self-signed certs
    connect_args["ssl"] = ssl_context

engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
