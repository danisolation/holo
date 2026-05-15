"""AI-powered simulator review service using Gemini.

Phase 109: Portfolio and trade reviews with Vietnamese structured output.
Uses _gemini_lock from ai_analysis_service for RPM serialization.
"""
import json as json_module

from cachetools import TTLCache
from google import genai
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.simulator_trade import SimulatorTrade
from app.models.ticker import Ticker
from app.schemas.simulator_review import PortfolioReviewResponse, TradeReviewResponse
from app.services.ai_analysis_service import _gemini_lock
from app.services.analysis.gemini_client import GeminiClient
from app.services.simulator_service import SimulatorService

REVIEW_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích giao dịch chứng khoán Việt Nam. "
    "Đánh giá danh mục đầu tư hoặc giao dịch cụ thể. "
    "Đưa ra nhận xét chi tiết, thực tế, dựa trên dữ liệu. "
    "Trả lời hoàn toàn bằng tiếng Việt."
)

# Module-level TTLCache for portfolio reviews — 300s TTL, max 4 entries (ai + user + buffer)
_portfolio_review_cache: TTLCache = TTLCache(maxsize=4, ttl=300)


class SimulatorReviewService:
    """AI-powered portfolio and trade review using Gemini."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def review_portfolio(self, portfolio_name: str = "user") -> dict:
        """Review entire portfolio using Gemini AI.

        Returns dict matching PortfolioReviewResponse fields.
        Cached 300s per portfolio_name via TTLCache.
        """
        # Check cache first
        if portfolio_name in _portfolio_review_cache:
            logger.info(f"Portfolio review cache hit for '{portfolio_name}'")
            return _portfolio_review_cache[portfolio_name]

        sim_service = SimulatorService(self.session)
        portfolio = await sim_service.get_portfolio(portfolio_name)
        stats = await sim_service.get_stats(portfolio_name)
        recent_trades = await sim_service.list_trades(1, 10, None, portfolio_name)

        prompt = self._build_portfolio_prompt(portfolio, stats, recent_trades)

        async with _gemini_lock:
            client = genai.Client(api_key=settings.gemini_api_key)
            model = settings.gemini_model
            gemini = GeminiClient(self.session, client, model)

            response = await gemini._call_gemini(
                prompt=prompt,
                response_schema=PortfolioReviewResponse,
                temperature=0.3,
                system_instruction=REVIEW_SYSTEM_INSTRUCTION,
            )
            await gemini._record_usage("simulator_review", 1, response)

        # Parse response — same pattern as peer_analysis_service
        result = response.parsed
        if result is None and response.text:
            logger.warning("Portfolio review: response.parsed is None, falling back to manual JSON parse")
            try:
                data = json_module.loads(response.text)
                result = PortfolioReviewResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")

        if result is None:
            raise ValueError("Gemini returned empty portfolio review")

        parsed = result.model_dump()
        _portfolio_review_cache[portfolio_name] = parsed
        return parsed

    async def review_trade(self, trade_id: int, portfolio_name: str = "user") -> dict:
        """Review a specific closed trade using Gemini AI.

        Only SELL trades can be reviewed (they have P&L data).
        Validates trade_id belongs to the requested portfolio (T-109-01).
        """
        sim_service = SimulatorService(self.session)
        portfolio = await sim_service.get_or_create_portfolio(portfolio_name)

        # Fetch trade and verify ownership
        trade_result = await self.session.execute(
            select(SimulatorTrade).where(
                SimulatorTrade.id == trade_id,
                SimulatorTrade.portfolio_id == portfolio.id,
            )
        )
        trade = trade_result.scalar_one_or_none()
        if trade is None:
            raise ValueError(f"Trade {trade_id} not found in '{portfolio_name}' portfolio")

        if trade.side != "SELL":
            raise ValueError("Only SELL trades can be reviewed (they have P&L data)")

        # Resolve ticker symbol
        ticker_result = await self.session.execute(
            select(Ticker).where(Ticker.id == trade.ticker_id)
        )
        ticker = ticker_result.scalar_one()

        trade_data = {
            "ticker_symbol": ticker.symbol,
            "ticker_name": ticker.name,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "trade_date": str(trade.trade_date),
            "broker_fee": float(trade.broker_fee),
            "sell_tax": float(trade.sell_tax),
            "total_fee": float(trade.total_fee),
            "gross_pnl": float(trade.gross_pnl) if trade.gross_pnl else None,
            "net_pnl": float(trade.net_pnl) if trade.net_pnl else None,
            "source": trade.source,
            "user_notes": trade.user_notes,
        }

        prompt = self._build_trade_prompt(trade_data)

        async with _gemini_lock:
            client = genai.Client(api_key=settings.gemini_api_key)
            model = settings.gemini_model
            gemini = GeminiClient(self.session, client, model)

            response = await gemini._call_gemini(
                prompt=prompt,
                response_schema=TradeReviewResponse,
                temperature=0.3,
                system_instruction=REVIEW_SYSTEM_INSTRUCTION,
            )
            await gemini._record_usage("simulator_trade_review", 1, response)

        # Parse response
        result = response.parsed
        if result is None and response.text:
            logger.warning("Trade review: response.parsed is None, falling back to manual JSON parse")
            try:
                data = json_module.loads(response.text)
                result = TradeReviewResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")

        if result is None:
            raise ValueError("Gemini returned empty trade review")

        return result.model_dump()

    def _build_portfolio_prompt(self, portfolio: dict, stats: dict, recent_trades: dict) -> str:
        """Build Vietnamese prompt with portfolio data for Gemini review."""
        positions_text = ""
        for pos in portfolio.get("positions", []):
            positions_text += (
                f"- {pos['ticker_symbol']} ({pos['ticker_name']}): "
                f"{pos['quantity']} cổ phiếu, giá TB {pos['avg_price']:,.0f}, "
                f"giá hiện tại {pos.get('current_price', 'N/A')}, "
                f"lãi/lỗ chưa thực hiện: {pos.get('unrealized_pnl', 'N/A')}\n"
            )

        trades_text = ""
        for t in recent_trades.get("trades", []):
            trades_text += (
                f"- {t['trade_date']} | {t['ticker_symbol']} | {t['side']} | "
                f"{t['quantity']} @ {t['price']:,.0f} | P&L: {t.get('net_pnl', 'N/A')}\n"
            )

        lines = [
            "## Đánh giá danh mục đầu tư mô phỏng",
            "",
            "### Tổng quan danh mục:",
            f"- Vốn ban đầu: {portfolio['starting_capital']:,.0f} VND",
            f"- Tiền mặt hiện tại: {portfolio['current_cash']:,.0f} VND",
            f"- Tổng giá trị: {portfolio['total_equity']:,.0f} VND",
            f"- Tổng lãi/lỗ: {portfolio['total_pnl']:,.0f} VND ({portfolio['total_pnl_pct']:.2f}%)",
            f"- Lãi/lỗ đã thực hiện: {portfolio['realized_pnl']:,.0f} VND",
            f"- Lãi/lỗ chưa thực hiện: {portfolio['unrealized_pnl']:,.0f} VND",
            "",
            "### Vị thế đang mở:",
            positions_text if positions_text else "- Không có vị thế nào",
            "",
            "### Thống kê giao dịch:",
            f"- Tổng số giao dịch: {stats['total_trades']}",
            f"- Tỷ lệ thắng AI: {stats['ai_win_rate']}%",
            f"- Tỷ lệ thắng thủ công: {stats['manual_win_rate']}%",
            f"- Lợi nhuận TB AI: {stats['ai_avg_return_pct']}%",
            f"- Lợi nhuận TB thủ công: {stats['manual_avg_return_pct']}%",
            "",
            "### 10 giao dịch gần nhất:",
            trades_text if trades_text else "- Chưa có giao dịch nào",
            "",
            "Hãy đánh giá danh mục đầu tư này:",
            "1. Tổng quan chung (overall_assessment)",
            "2. Điểm mạnh (strengths) — liệt kê dạng bullet",
            "3. Điểm yếu (weaknesses) — liệt kê dạng bullet",
            "4. Gợi ý cải thiện (suggestions) — liệt kê dạng bullet",
            "5. Đánh giá rủi ro (risk_assessment)",
            "6. Điểm số tổng thể 1-10 (score)",
        ]

        return "\n".join(lines)

    def _build_trade_prompt(self, trade_data: dict) -> str:
        """Build Vietnamese prompt with trade data for Gemini review."""
        lines = [
            "## Đánh giá giao dịch cụ thể",
            "",
            f"### Chi tiết giao dịch:",
            f"- Mã: {trade_data['ticker_symbol']} ({trade_data['ticker_name']})",
            f"- Loại: {trade_data['side']}",
            f"- Số lượng: {trade_data['quantity']}",
            f"- Giá: {trade_data['price']:,.0f} VND",
            f"- Ngày: {trade_data['trade_date']}",
            f"- Phí môi giới: {trade_data['broker_fee']:,.0f} VND",
            f"- Thuế bán: {trade_data['sell_tax']:,.0f} VND",
            f"- Tổng phí: {trade_data['total_fee']:,.0f} VND",
            f"- Lãi/lỗ gộp: {trade_data['gross_pnl']:,.0f} VND" if trade_data['gross_pnl'] else "- Lãi/lỗ gộp: N/A",
            f"- Lãi/lỗ ròng: {trade_data['net_pnl']:,.0f} VND" if trade_data['net_pnl'] else "- Lãi/lỗ ròng: N/A",
            f"- Nguồn: {trade_data['source']}",
        ]

        if trade_data.get("user_notes"):
            lines.append(f"- Ghi chú: {trade_data['user_notes']}")

        lines.extend([
            "",
            "Hãy phân tích giao dịch này:",
            "1. Phân tích điểm vào (entry_analysis)",
            "2. Phân tích điểm thoát (exit_analysis)",
            "3. Điểm tốt (what_went_well) — liệt kê dạng bullet",
            "4. Cần cải thiện (what_could_improve) — liệt kê dạng bullet",
            "5. Nhận diện mẫu hình (pattern_identified)",
            '6. Nhận định tổng thể (overall_verdict): "Tốt" / "Trung bình" / "Cần cải thiện"',
        ])

        return "\n".join(lines)
