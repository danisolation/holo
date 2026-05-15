"""AI-powered peer analysis service using Gemini.

Phase 106: Compares a ticker against sector peers on valuation, momentum,
volume, and market cap — producing structured Vietnamese insights.

Uses _gemini_lock from ai_analysis_service for RPM serialization.
"""
import json as json_module

from google import genai
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.peer_analysis import PeerAnalysisResponse
from app.services.ai_analysis_service import _gemini_lock
from app.services.analysis.gemini_client import GeminiClient
from app.services.screener_service import ScreenerService

PEER_ANALYSIS_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích cổ phiếu Việt Nam. "
    "Phân tích so sánh mã cổ phiếu với các cổ phiếu cùng ngành. "
    "Trả lời hoàn toàn bằng tiếng Việt."
)


class PeerAnalysisService:
    """Compare a ticker against its sector peers using Gemini AI."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _build_prompt(self, symbol: str, sector: str, target: dict, peers: list[dict]) -> str:
        """Build Vietnamese prompt with target and peer metrics."""
        # Compute sector averages from peers (excluding None values)
        def _avg(key: str) -> float | None:
            vals = [p[key] for p in peers if p.get(key) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        avg_pe = _avg("pe")
        avg_volume = _avg("volume")
        avg_change = _avg("change_1d")
        avg_market_cap = _avg("market_cap")

        lines = [
            f"## Phân tích so sánh: {symbol} trong ngành {sector}",
            "",
            f"### Mã mục tiêu: {symbol}",
            f"- Giá đóng cửa: {target.get('close')}",
            f"- Khối lượng: {target.get('volume')}",
            f"- Thay đổi 1D: {target.get('change_1d')}%",
            f"- P/E: {target.get('pe')}",
            f"- Vốn hóa: {target.get('market_cap')}",
            f"- Xếp hạng P/E: {target.get('rank_pe')}/{len(peers)}",
            f"- Xếp hạng khối lượng: {target.get('rank_volume')}/{len(peers)}",
            f"- Xếp hạng thay đổi giá: {target.get('rank_change')}/{len(peers)}",
            f"- Xếp hạng vốn hóa: {target.get('rank_market_cap')}/{len(peers)}",
            "",
            f"### Trung bình ngành ({len(peers)} mã):",
            f"- P/E trung bình: {avg_pe}",
            f"- Khối lượng trung bình: {avg_volume}",
            f"- Thay đổi 1D trung bình: {avg_change}%",
            f"- Vốn hóa trung bình: {avg_market_cap}",
            "",
            "### Các mã cùng ngành:",
        ]

        for p in peers:
            lines.append(
                f"- {p['symbol']}: Giá {p.get('close')}, KL {p.get('volume')}, "
                f"Δ1D {p.get('change_1d')}%, P/E {p.get('pe')}, VH {p.get('market_cap')}"
            )

        lines.extend([
            "",
            "Hãy so sánh mã mục tiêu với trung bình ngành trên các chiều:",
            "1. Định giá (P/E so với trung bình ngành)",
            "2. Động lượng (thay đổi giá 1D so với trung bình)",
            "3. Khối lượng giao dịch (so với trung bình ngành)",
            "4. Vốn hóa (quy mô so với ngành)",
            "",
            "Xác định điểm mạnh (outperform) và điểm yếu (underperform).",
            "Đưa ra nhận định tổng thể và khuyến nghị hành động.",
        ])

        return "\n".join(lines)

    async def analyze(self, symbol: str) -> dict:
        """Run AI peer analysis for a ticker.

        Returns dict matching PeerAnalysisResponse fields.
        Raises ValueError if ticker has no peers or no sector.
        """
        screener = ScreenerService(self.session)
        peer_data = await screener.get_peer_comparison(symbol)

        sector = peer_data.get("sector", "")
        peers_list = peer_data.get("peers", [])

        if not peers_list or not sector:
            raise ValueError(f"Không tìm thấy dữ liệu ngành cho mã {symbol}")

        # Find target ticker in peers list
        target = None
        for p in peers_list:
            if p.get("is_target"):
                target = p
                break

        if target is None:
            # Fallback: use symbol match
            for p in peers_list:
                if p.get("symbol", "").upper() == symbol.upper():
                    target = p
                    break

        if target is None:
            raise ValueError(f"Không tìm thấy mã {symbol} trong danh sách so sánh")

        prompt = self._build_prompt(symbol, sector, target, peers_list)

        async with _gemini_lock:
            client = genai.Client(api_key=settings.gemini_api_key)
            model = settings.gemini_model
            gemini = GeminiClient(self.session, client, model)

            response = await gemini._call_gemini(
                prompt=prompt,
                response_schema=PeerAnalysisResponse,
                temperature=0.3,
                system_instruction=PEER_ANALYSIS_SYSTEM_INSTRUCTION,
            )
            await gemini._record_usage("peer_analysis", 1, response)

        # Parse response — same pattern as sector_intelligence_service
        result = response.parsed
        if result is None and response.text:
            logger.warning("Peer analysis: response.parsed is None, falling back to manual JSON parse")
            try:
                data = json_module.loads(response.text)
                result = PeerAnalysisResponse.model_validate(data)
            except Exception as e:
                logger.error(f"Manual parse also failed: {e}")

        if result is None:
            raise ValueError("Gemini returned empty peer analysis")

        parsed = result.model_dump()
        # Ensure symbol and sector are set from our data (not Gemini's output)
        parsed["symbol"] = symbol
        parsed["sector"] = sector
        return parsed
