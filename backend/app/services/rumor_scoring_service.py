"""Rumor scoring service — Gemini AI credibility/impact assessment of community posts.

Reads unscored Fireant posts from `rumors` table, groups by ticker, sends each
ticker's posts to Gemini in a single prompt, stores results in `rumor_scores`.

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
        tickers = await self._get_tickers_with_unscored_rumors()
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
        """Score all rumors for a single ticker.

        1. Query rumors for this ticker
        2. Build prompt with engagement metrics
        3. Call Gemini (with lock) for credibility/impact scoring
        4. Store result via upsert
        """
        # Fetch rumors for this ticker
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

        if not rumors:
            logger.debug(f"Rumor scoring: no rumors for {ticker_symbol}, skipping")
            return None

        rumor_ids = [r[0] for r in rumors]
        prompt = self._build_prompt(ticker_symbol, rumors)

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

    async def _get_tickers_with_unscored_rumors(self) -> list[tuple[int, str]]:
        """Find tickers with rumors but no score for today."""
        today = date.today()
        result = await self.session.execute(
            text("""
                SELECT DISTINCT r.ticker_id, t.symbol
                FROM rumors r
                JOIN tickers t ON t.id = r.ticker_id
                WHERE NOT EXISTS (
                    SELECT 1 FROM rumor_scores rs
                    WHERE rs.ticker_id = r.ticker_id AND rs.scored_date = :today
                )
            """),
            {"today": today},
        )
        return result.fetchall()

    def _build_prompt(self, ticker_symbol: str, rumors: list) -> str:
        """Build Vietnamese prompt with engagement metrics for Gemini.

        Each post is tagged with verification status, likes, and replies
        per D-5 (all posts in one prompt) and D-15 (engagement context).
        """
        lines = [RUMOR_FEW_SHOT, ""]
        lines.append(f"\n--- {ticker_symbol} ({len(rumors)} bài đăng) ---")

        for i, r in enumerate(rumors, 1):
            # r is a Row: (id, content, author_name, is_authentic,
            #              total_likes, total_replies, posted_at)
            is_authentic = r[3]
            total_likes = r[4]
            total_replies = r[5]
            content = r[1]

            auth_label = "Xác thực ✓" if is_authentic else "Thường"
            # Truncate user content to limit prompt size and mitigate injection risk
            safe_content = self._sanitize_content(content)
            lines.append(
                f"{i}. [{auth_label} | {total_likes} likes | {total_replies} replies] "
                f'"{safe_content}"'
            )

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
