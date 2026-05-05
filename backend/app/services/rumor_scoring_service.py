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

        Returns dict mapping ticker symbol to success/failure.
        """
        tickers = await self._get_tickers_with_unscored_data()
        if not tickers:
            logger.info("Rumor scoring: no tickers with unscored rumors")
            return {}

        results: dict[str, bool] = {}
        total = len(tickers)
        scored = 0

        for i, row in enumerate(tickers):
            ticker_id, symbol = row[0], row[1]
            try:
                score = await self.score_ticker(ticker_id, symbol)
                success = score is not None
                results[symbol] = success
                if success:
                    scored += 1
            except Exception as e:
                logger.error(f"Rumor scoring failed for {symbol}: {e}")
                results[symbol] = False

            # Delay between tickers to respect RPM limits
            if i < total - 1:
                await asyncio.sleep(settings.gemini_delay_seconds)

        logger.info(f"Rumor scoring complete: {scored}/{total} tickers scored")
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
        """Build Vietnamese prompt combining Fireant posts + CafeF news.

        Two sections: community posts (with engagement metrics) and news headlines.
        Gemini evaluates both sources for a comprehensive score.
        """
        lines = [RUMOR_FEW_SHOT, ""]
        total_items = len(rumors) + (len(news_articles) if news_articles else 0)
        lines.append(
            f"\n--- {ticker_symbol} ({total_items} nguồn thông tin) ---"
        )

        idx = 1
        # Section 1: Fireant community posts
        if rumors:
            lines.append(f"\n📢 Bài đăng cộng đồng Fireant ({len(rumors)}):")
            for r in rumors:
                is_authentic = r[3]
                total_likes = r[4]
                total_replies = r[5]
                content = r[1]

                auth_label = "Xác thực ✓" if is_authentic else "Thường"
                safe_content = self._sanitize_content(content)
                lines.append(
                    f"{idx}. [{auth_label} | {total_likes} likes | "
                    f'{total_replies} replies] "{safe_content}"'
                )
                idx += 1

        # Section 2: CafeF news headlines
        if news_articles:
            lines.append(f"\n📰 Tin tức CafeF ({len(news_articles)}):")
            for na in news_articles:
                title = self._sanitize_content(na[1], max_len=200)
                lines.append(f"{idx}. [Tin tức chính thống] \"{title}\"")
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
