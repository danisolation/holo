"""Quick VIC price check script."""
import asyncio
import json
from app.database import async_session
from sqlalchemy import text


async def check():
    async with async_session() as s:
        r = await s.execute(text("SELECT id, symbol FROM tickers WHERE symbol='VIC'"))
        row = r.fetchone()
        if row:
            print(f"VIC found: id={row[0]}")
            # Get latest price
            p = await s.execute(
                text("SELECT close, date FROM daily_prices WHERE ticker_id=:tid ORDER BY date DESC LIMIT 3"),
                {"tid": row[0]},
            )
            prices = p.fetchall()
            for price in prices:
                print(f"  Price: close={price[0]}, date={price[1]}")

            # Get ALL analysis types
            a = await s.execute(
                text("SELECT analysis_type, raw_response, created_at FROM ai_analyses WHERE ticker_id=:tid ORDER BY created_at DESC LIMIT 10"),
                {"tid": row[0]},
            )
            analyses = a.fetchall()
            for row2 in analyses:
                atype = row2[0]
                raw = json.loads(row2[1]) if isinstance(row2[1], str) else row2[1]
                created = row2[2]
                print(f"\n  Analysis: {atype} (created: {created})")
                if atype == "trading_signal":
                    tp = raw.get("trading_plan", {})
                    print(f"    direction={raw.get('recommended_direction')}, confidence={raw.get('confidence')}")
                    if tp:
                        print(f"    Entry: {tp.get('entry_price')}, SL: {tp.get('stop_loss')}")
                    # Check legacy format
                    long = raw.get("long_analysis", {})
                    if long:
                        ltp = long.get("trading_plan", {})
                        print(f"    [LEGACY] direction=long, confidence={long.get('confidence')}")
                        if ltp:
                            print(f"    [LEGACY] Entry: {ltp.get('entry_price')}, SL: {ltp.get('stop_loss')}")
                elif atype == "technical":
                    print(f"    summary: {str(raw.get('summary', ''))[:200]}")
                elif atype == "combined":
                    print(f"    recommendation: {raw.get('recommendation', '')[:200]}")
                    print(f"    raw keys: {list(raw.keys())}")
        else:
            print("VIC NOT in DB")

        total = await s.execute(text("SELECT COUNT(*) FROM tickers"))
        print(f"Total tickers: {total.scalar()}")


asyncio.run(check())
