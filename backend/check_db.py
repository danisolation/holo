import asyncio
from app.database import async_session
from sqlalchemy import text

async def check():
    async with async_session() as session:
        r = await session.execute(text('SELECT version_num FROM alembic_version'))
        print('Current migration:', r.scalar_one_or_none())
        
        r2 = await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name IN "
            "('trading_goals', 'weekly_prompts', 'weekly_reviews', 'behavior_events') "
            "ORDER BY table_name"
        ))
        tables = [row[0] for row in r2.all()]
        print('Tables found:', tables)

asyncio.run(check())
