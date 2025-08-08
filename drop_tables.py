import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from api import Base, config  # Replace `your_module` with actual path to your models/config

async def drop_all():
    db_url = config.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    print("✅ All tables dropped.")

asyncio.run(drop_all())
