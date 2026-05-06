"""Rumor scoring service — Gemini AI credibility/impact assessment.

Combines Fireant community posts (`rumors` table) and CafeF news headlines
(`news_articles` table) for each ticker, sends to Gemini in a single prompt,
stores results in `rumor_scores`.

Architecture: Standalone service (D-1), NOT embedded in AIAnalysisService.
Uses same GeminiClient pattern + _gemini_lock for RPM serialization (D-2, D-4).
"""
import asyncio
import json
from datetime import date

import google.genai as genai
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.rumor import RumorBatchResponse, TickerRumorScore
from app.services.ai_analysis_service import _gemini_lock
from app.services.analysis.gemini_client import GeminiClient
from app.services.analysis.rumor_prompts import (
    RUMOR_FEW_SHOT,
    RUMOR_SYSTEM_INSTRUCTION,
    RUMOR_TEMPERATURE,
)


class RumorScoringService:
    """Score community rumors per ticker using Gemini AI."""

    def __init__(self, session: AsyncSession, api_key: str | None = None):
        self.session = session
        key = api_key or settings.gemini_api_key
        if not key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=key)
        self.model = settings.gemini_model
        self.gemini_client = GeminiClient(session, self.client, self.model)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def score_all_tickers(self) -> dict[str, bool]:
        """Score all tickers that have unscored rumors today.

        Batches multiple tickers into single Gemini calls to conserve API quota.
        With rumor_batch_size=6, 30 tickers need only 5 calls (vs 30 without batching).

        Returns dict mapping ticker symbol to success/failure.
        """
        tickers = await self._get_tickers_with_unscored_data()
        if not tickers:
            logger.info("Rumor scoring: no tickers with unscored rumors")
            return {}

        batch_size = settings.rumor_batch_size
        batches = [
            tickers[i : i + batch_size]
            for i in range(0, len(tickers), batch_size)
        ]

        results: dict[str, bool] = {}
        total = len(tickers)
        scored = 0

        for batch_idx, batch in enumerate(batches):
            symbols = [row[1] for row in batch]
            logger.info(
                f"Rumor scoring batch {batch_idx + 1}/{len(batches)}: "
                f"{', '.join(symbols)}"
            )
            try:
                batch_results = await self.score_batch(batch)
                for symbol, success in batch_results.items():
                    results[symbol] = success
                    if success:
                        scored += 1
            except Exception as e:
                logger.error(f"Rumor scoring batch {batch_idx + 1} failed: {e}")
                for row in batch:
                    results[row[1]] = False

            # Delay between batches to respect RPM limits
            if batch_idx < len(batches) - 1:
                await asyncio.sleep(settings.gemini_delay_seconds)

        logger.info(
            f"Rumor scoring complete: {scored}/{total} tickers in "
            f"{len(batches)} Gemini calls"
        )
        return results

    async def score_batch(
        self, tickers: list[tuple[int, str]]
    ) -> dict[str, bool]:
        """Score multiple tickers in a single Gemini call.

        1. Fetch rumors + news for each ticker
        2. Build combined multi-ticker prompt
        3. Single Gemini call → RumorBatchResponse with scores per ticker
        4. Store each ticker's score
        """
        # Gather data for all tickers in batch
        ticker_data: list[dict] = []
        for ticker_id, symbol in tickers:
            result = await self.session.execute(
                text("""
                    SELECT id, content, author_name, is_authentic,
                           total_likes, total_replies, posted_at
                    FROM rumors
                    WHERE ticker_id = :tid
                      AND posted_at >= CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY posted_at DESC
                """),
                {"tid": ticker_id},
            )
            rumors = result.fetchall()

            news_result = await self.session.execute(
                text("""
                    SELECT id, title, published_at
                    FROM news_articles
                    WHERE ticker_id = :tid
                      AND published_at >= CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY published_at DESC
                    LIMIT 20
                """),
                {"tid": ticker_id},
            )
            news_articles = news_result.fetchall()

            if rumors or news_articles:
                ticker_data.append({
                    "ticker_id": ticker_id,
                    "symbol": symbol,
                    "rumors": rumors,
                    "news_articles": news_articles,
                    "rumor_ids": [r[0] for r in rumors] if rumors else [],
                })

        if not ticker_data:
            return {row[1]: False for row in tickers}

        # Build combined prompt for all tickers in batch
        prompt = self._build_batch_prompt(ticker_data)

        # Single Gemini call for entire batch
        async with _gemini_lock:
            response = await self.gemini_client._call_gemini(
                prompt, RumorBatchResponse, RUMOR_TEMPERATURE, RUMOR_SYSTEM_INSTRUCTION
            )
            await self.gemini_client._record_usage("rumor_scoring", 1, response)

        batch_result = response.parsed

        if batch_result is None and response.text:
            logger.warning("Rumor batch: response.parsed is None, retrying at temperature=0.05")
            async with _gemini_lock:
                response = await self.gemini_client._call_gemini(
                    prompt, RumorBatchResponse, 0.05, RUMOR_SYSTEM_INSTRUCTION
                )
            batch_result = response.parsed

        if batch_result is None and response.text:
            logger.warning("Low-temp retry failed, falling back to manual JSON parse")
            try:
                data = json.loads(response.text)
                batch_result = RumorBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse failed for batch: {e}")
                return {td["symbol"]: False for td in ticker_data}

        if batch_result is None:
            logger.error("Rumor batch: no parseable response")
            return {td["symbol"]: False for td in ticker_data}

        # Map scores to tickers and store
        results: dict[str, bool] = {}
        score_map = {s.ticker.upper(): s for s in batch_result.scores}

        for td in ticker_data:
            symbol = td["symbol"]
            ticker_score = score_map.get(symbol.upper())
            if ticker_score is None:
                logger.warning(f"Rumor batch: no score returned for {symbol}")
                results[symbol] = False
                continue

            try:
                await self._store_score(td["ticker_id"], ticker_score, td["rumor_ids"])
                logger.info(
                    f"Rumor score: {symbol} — "
                    f"credibility={ticker_score.credibility_score}, "
                    f"impact={ticker_score.impact_score}, "
                    f"direction={ticker_score.direction.value}"
                )
                results[symbol] = True
            except Exception as e:
                logger.error(f"Store score failed for {symbol}: {e}")
                results[symbol] = False

        # Mark tickers with no data as failed
        for row in tickers:
            if row[1] not in results:
                results[row[1]] = False

        return results

    async def score_ticker(
        self, ticker_id: int, ticker_symbol: str
    ) -> TickerRumorScore | None:
        """Score a ticker using both Fireant community posts and CafeF news.

        1. Query rumors + news_articles for this ticker (7-day window)
        2. Build combined prompt with engagement metrics + news headlines
        3. Call Gemini (with lock) for credibility/impact scoring
        4. Store result via upsert
        """
        # Fetch Fireant community posts
        result = await self.session.execute(
            text("""
                SELECT id, content, author_name, is_authentic,
                       total_likes, total_replies, posted_at
                FROM rumors
                WHERE ticker_id = :tid
                  AND posted_at >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY posted_at DESC
            """),
            {"tid": ticker_id},
        )
        rumors = result.fetchall()

        # Fetch CafeF news headlines
        news_result = await self.session.execute(
            text("""
                SELECT id, title, published_at
                FROM news_articles
                WHERE ticker_id = :tid
                  AND published_at >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY published_at DESC
                LIMIT 20
            """),
            {"tid": ticker_id},
        )
        news_articles = news_result.fetchall()

        if not rumors and not news_articles:
            logger.debug(f"Rumor scoring: no data for {ticker_symbol}, skipping")
            return None

        rumor_ids = [r[0] for r in rumors] if rumors else []
        prompt = self._build_prompt(ticker_symbol, rumors, news_articles)

        # Acquire lock to serialize Gemini API access (D-4)
        async with _gemini_lock:
            response = await self.gemini_client._call_gemini(
                prompt, RumorBatchResponse, RUMOR_TEMPERATURE, RUMOR_SYSTEM_INSTRUCTION
            )
            await self.gemini_client._record_usage("rumor_scoring", 1, response)

        # Parse response — same retry pattern as GeminiClient.analyze_technical_batch
        batch_result = response.parsed

        if batch_result is None and response.text:
            logger.warning(
                f"Rumor scoring {ticker_symbol}: response.parsed is None, "
                "retrying at temperature=0.05"
            )
            async with _gemini_lock:
                response = await self.gemini_client._call_gemini(
                    prompt, RumorBatchResponse, 0.05, RUMOR_SYSTEM_INSTRUCTION
                )
            batch_result = response.parsed

        if batch_result is None and response.text:
            logger.warning(
                "Low-temp retry also failed, falling back to manual JSON parse"
            )
            try:
                data = json.loads(response.text)
                batch_result = RumorBatchResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed for {ticker_symbol}: {e}")
                logger.debug(f"Raw response text: {response.text[:500]}")
                return None

        if batch_result is None:
            logger.error(f"Rumor scoring: no parseable response for {ticker_symbol}")
            return None

        # Find the matching ticker score from batch response
        ticker_score = None
        for score in batch_result.scores:
            if score.ticker.upper() == ticker_symbol.upper():
                ticker_score = score
                break

        if ticker_score is None and batch_result.scores:
            # Gemini returned scores but ticker name didn't match — use first
            logger.warning(
                f"Rumor scoring: ticker mismatch for {ticker_symbol}, "
                f"using first score ({batch_result.scores[0].ticker})"
            )
            ticker_score = batch_result.scores[0]

        if ticker_score is None:
            logger.error(f"Rumor scoring: empty scores list for {ticker_symbol}")
            return None

        # Store result
        await self._store_score(ticker_id, ticker_score, rumor_ids)
        logger.info(
            f"Rumor score stored: {ticker_symbol} — "
            f"credibility={ticker_score.credibility_score}, "
            f"impact={ticker_score.impact_score}, "
            f"direction={ticker_score.direction.value}"
        )
        return ticker_score

    # ------------------------------------------------------------------
    # Internal Methods
    # ------------------------------------------------------------------

    async def _get_tickers_with_unscored_data(self) -> list[tuple[int, str]]:
        """Find watchlist tickers with rumors OR news articles but no score for today.

        Limits to watchlist tickers to keep Gemini API usage manageable —
        CafeF has news for all 400 tickers but we only score what the user tracks.
        """
        today = date.today()
        result = await self.session.execute(
            text("""
                SELECT DISTINCT ticker_id, symbol FROM (
                    SELECT r.ticker_id, t.symbol
                    FROM rumors r
                    JOIN tickers t ON t.id = r.ticker_id
                    WHERE r.posted_at >= CURRENT_DATE - INTERVAL '7 days'
                    UNION
                    SELECT na.ticker_id, t.symbol
                    FROM news_articles na
                    JOIN tickers t ON t.id = na.ticker_id
                    WHERE na.published_at >= CURRENT_DATE - INTERVAL '7 days'
                ) combined
                WHERE combined.symbol IN (SELECT symbol FROM user_watchlist)
                AND NOT EXISTS (
                    SELECT 1 FROM rumor_scores rs
                    WHERE rs.ticker_id = combined.ticker_id AND rs.scored_date = :today
                )
            """),
            {"today": today},
        )
        return result.fetchall()

    def _build_prompt(
        self, ticker_symbol: str, rumors: list, news_articles: list | None = None
    ) -> str:
        """Build Vietnamese prompt combining all sources.

        Groups by source type based on author_name prefix:
        - Official news: is_authentic=True OR prefix ndt:/tnck:
        - Community: Fireant, F319, Telegram
        """
        lines = [RUMOR_FEW_SHOT, ""]
        total_items = len(rumors) + (len(news_articles) if news_articles else 0)
        lines.append(
            f"\n--- {ticker_symbol} ({total_items} nguồn thông tin) ---"
        )

        idx = 1
        if rumors:
            # Categorize rumors by source credibility
            official_rumors = []
            community_rumors = []
            for r in rumors:
                author = r[2] or ""
                if r[3] or author.startswith("ndt:") or author.startswith("tnck:"):
                    official_rumors.append(r)
                else:
                    community_rumors.append(r)

            if official_rumors:
                lines.append(f"\n📰 Tin tức chính thống ({len(official_rumors)}):")
                for r in official_rumors:
                    source = r[2]
                    safe_content = self._sanitize_content(r[1])
                    lines.append(f'{idx}. [{source}] "{safe_content}"')
                    idx += 1

            if community_rumors:
                lines.append(f"\n📢 Bài đăng cộng đồng ({len(community_rumors)}):")
                for r in community_rumors:
                    source = r[2]
                    safe_content = self._sanitize_content(r[1])
                    lines.append(
                        f"{idx}. [{source} | {r[4]} likes | "
                        f'{r[5]} replies] "{safe_content}"'
                    )
                    idx += 1

        # CafeF news headlines (separate table)
        if news_articles:
            lines.append(f"\n📰 Tin tức CafeF ({len(news_articles)}):")
            for na in news_articles:
                title = self._sanitize_content(na[1], max_len=200)
                lines.append(f"{idx}. [CafeF] \"{title}\"")
                idx += 1

        return "\n".join(lines)

    def _build_batch_prompt(self, ticker_data: list[dict]) -> str:
        """Build Vietnamese prompt for multiple tickers in one Gemini call.

        Each ticker gets its own section with categorized sources.
        Gemini returns a scores array with one entry per ticker.
        """
        lines = [RUMOR_FEW_SHOT, ""]
        symbols = [td["symbol"] for td in ticker_data]
        lines.append(
            f"Phân tích {len(ticker_data)} mã cổ phiếu: {', '.join(symbols)}"
        )
        lines.append("Trả về scores array với MỘT entry cho MỖI mã bên dưới.\n")

        for td in ticker_data:
            symbol = td["symbol"]
            rumors = td["rumors"]
            news_articles = td["news_articles"]
            total_items = len(rumors) + len(news_articles)

            lines.append(f"\n--- {symbol} ({total_items} nguồn thông tin) ---")

            idx = 1
            if rumors:
                # Categorize by source credibility (prefix-based)
                official_rumors = []
                community_rumors = []
                for r in rumors:
                    author = r[2] or ""
                    if r[3] or author.startswith("ndt:") or author.startswith("tnck:"):
                        official_rumors.append(r)
                    else:
                        community_rumors.append(r)

                if official_rumors:
                    lines.append(f"\n📰 Tin tức chính thống ({len(official_rumors)}):")
                    for r in official_rumors:
                        source = r[2]
                        safe_content = self._sanitize_content(r[1])
                        lines.append(
                            f'{idx}. [{source}] "{safe_content}"'
                        )
                        idx += 1

                if community_rumors:
                    lines.append(f"\n📢 Bài đăng cộng đồng ({len(community_rumors)}):")
                    for r in community_rumors:
                        source = r[2]
                        safe_content = self._sanitize_content(r[1])
                        lines.append(
                            f"{idx}. [{source} | {r[4]} likes | "
                            f'{r[5]} replies] "{safe_content}"'
                        )
                        idx += 1

            if news_articles:
                lines.append(f"\n📰 Tin tức CafeF ({len(news_articles)}):")
                for na in news_articles:
                    title = self._sanitize_content(na[1], max_len=200)
                    lines.append(f'{idx}. [Tin tức chính thống] "{title}"')
                    idx += 1

        return "\n".join(lines)

    def _sanitize_content(self, content: str, max_len: int = 500) -> str:
        """Truncate and basic-sanitize user content for prompt inclusion.

        Mitigates prompt injection risk by limiting content length and stripping
        characters that could break prompt formatting.
        """
        truncated = content[:max_len]
        # Strip characters that could break prompt formatting
        truncated = truncated.replace('"', "'")
        return truncated

    async def _store_score(
        self,
        ticker_id: int,
        score: TickerRumorScore,
        rumor_ids: list[int],
    ) -> None:
        """Store rumor score with upsert (INSERT ... ON CONFLICT DO UPDATE).

        Mirrors AnalysisStorage pattern with raw SQL for asyncpg compatibility.
        """
        await self.session.execute(
            text("""
                INSERT INTO rumor_scores (ticker_id, scored_date, credibility_score,
                    impact_score, direction, key_claims, reasoning, post_ids, model_version)
                VALUES (:tid, :sdate, :cred, :impact, :dir, CAST(:claims AS jsonb),
                    :reasoning, CAST(:pids AS jsonb), :model)
                ON CONFLICT ON CONSTRAINT uq_rumor_scores_ticker_date
                DO UPDATE SET credibility_score = :cred, impact_score = :impact,
                    direction = :dir, key_claims = CAST(:claims AS jsonb),
                    reasoning = :reasoning, post_ids = CAST(:pids AS jsonb),
                    model_version = :model
            """),
            {
                "tid": ticker_id,
                "sdate": date.today(),
                "cred": score.credibility_score,
                "impact": score.impact_score,
                "dir": score.direction.value,
                "claims": json.dumps(score.key_claims, ensure_ascii=False),
                "reasoning": score.reasoning,
                "pids": json.dumps(rumor_ids),
                "model": self.model,
            },
        )
        await self.session.commit()
