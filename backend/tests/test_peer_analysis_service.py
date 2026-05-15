"""Tests for PeerAnalysisService — Phase 106.

Covers prompt building, error handling, and response parsing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.peer_analysis import PeerAnalysisResponse
from app.services.peer_analysis_service import PeerAnalysisService


# --- Sample peer data matching ScreenerService.get_peer_comparison output ---

SAMPLE_PEER_DATA = {
    "symbol": "VNM",
    "sector": "Hàng tiêu dùng",
    "peers": [
        {
            "symbol": "VNM", "name": "Vinamilk", "close": 72.5, "volume": 1500000,
            "change_1d": 1.2, "pe": 15.0, "market_cap": 150000.0,
            "rank_pe": 2, "rank_volume": 1, "rank_change": 1, "rank_market_cap": 1,
            "is_target": True,
        },
        {
            "symbol": "MCH", "name": "Masan Consumer", "close": 120.0, "volume": 500000,
            "change_1d": -0.5, "pe": 20.0, "market_cap": 80000.0,
            "rank_pe": 3, "rank_volume": 2, "rank_change": 3, "rank_market_cap": 2,
            "is_target": False,
        },
        {
            "symbol": "SAB", "name": "Sabeco", "close": 60.0, "volume": 300000,
            "change_1d": 0.3, "pe": 25.0, "market_cap": 90000.0,
            "rank_pe": 4, "rank_volume": 3, "rank_change": 2, "rank_market_cap": 3,
            "is_target": False,
        },
    ],
}

SAMPLE_AI_RESPONSE = PeerAnalysisResponse(
    symbol="VNM",
    sector="Hàng tiêu dùng",
    overall_verdict="Vượt trội so với ngành",
    strengths=[
        "P/E thấp hơn trung bình ngành (15.0 vs 20.0)",
        "Khối lượng giao dịch cao nhất ngành",
    ],
    weaknesses=[
        "Vốn hóa lớn nên tiềm năng tăng trưởng hạn chế",
    ],
    peer_position="VNM đang dẫn đầu ngành Hàng tiêu dùng về khối lượng giao dịch và định giá hấp dẫn.",
    recommendation="Cân nhắc mua vào khi giá điều chỉnh về vùng hỗ trợ 70-71.",
)


class TestBuildPrompt:
    """Test prompt building produces Vietnamese content with correct data."""

    def setup_method(self):
        self.service = PeerAnalysisService(session=MagicMock())

    def test_prompt_contains_symbol_and_sector(self):
        target = SAMPLE_PEER_DATA["peers"][0]
        prompt = self.service._build_prompt("VNM", "Hàng tiêu dùng", target, SAMPLE_PEER_DATA["peers"])
        assert "VNM" in prompt
        assert "Hàng tiêu dùng" in prompt

    def test_prompt_contains_vietnamese_headers(self):
        target = SAMPLE_PEER_DATA["peers"][0]
        prompt = self.service._build_prompt("VNM", "Hàng tiêu dùng", target, SAMPLE_PEER_DATA["peers"])
        assert "Phân tích so sánh" in prompt
        assert "Mã mục tiêu" in prompt
        assert "Trung bình ngành" in prompt
        assert "Các mã cùng ngành" in prompt

    def test_prompt_contains_target_metrics(self):
        target = SAMPLE_PEER_DATA["peers"][0]
        prompt = self.service._build_prompt("VNM", "Hàng tiêu dùng", target, SAMPLE_PEER_DATA["peers"])
        assert "72.5" in prompt
        assert "1500000" in prompt
        assert "15.0" in prompt

    def test_prompt_contains_sector_averages(self):
        target = SAMPLE_PEER_DATA["peers"][0]
        prompt = self.service._build_prompt("VNM", "Hàng tiêu dùng", target, SAMPLE_PEER_DATA["peers"])
        # avg PE = (15+20+25)/3 = 20.0
        assert "20.0" in prompt
        # avg change_1d = (1.2 + -0.5 + 0.3) / 3 = 0.33
        assert "0.33" in prompt

    def test_prompt_contains_peer_symbols(self):
        target = SAMPLE_PEER_DATA["peers"][0]
        prompt = self.service._build_prompt("VNM", "Hàng tiêu dùng", target, SAMPLE_PEER_DATA["peers"])
        assert "MCH" in prompt
        assert "SAB" in prompt


class TestAnalyzeErrors:
    """Test error handling in analyze()."""

    @pytest.mark.asyncio
    async def test_raises_on_empty_peers(self):
        session = AsyncMock()
        service = PeerAnalysisService(session)

        # Patch ScreenerService to return empty peers
        mock_screener = MagicMock()
        mock_screener.get_peer_comparison = AsyncMock(return_value={
            "symbol": "XYZ", "sector": "", "peers": [],
        })

        with patch("app.services.peer_analysis_service.ScreenerService", return_value=mock_screener):
            with pytest.raises(ValueError, match="Không tìm thấy dữ liệu ngành"):
                await service.analyze("XYZ")

    @pytest.mark.asyncio
    async def test_raises_on_no_sector(self):
        session = AsyncMock()
        service = PeerAnalysisService(session)

        mock_screener = MagicMock()
        mock_screener.get_peer_comparison = AsyncMock(return_value={
            "symbol": "XYZ", "sector": "", "peers": [{"symbol": "A", "is_target": False}],
        })

        with patch("app.services.peer_analysis_service.ScreenerService", return_value=mock_screener):
            with pytest.raises(ValueError, match="Không tìm thấy dữ liệu ngành"):
                await service.analyze("XYZ")


class TestAnalyzeParsing:
    """Test that analyze() correctly parses Gemini response."""

    @pytest.mark.asyncio
    async def test_parses_response_parsed(self):
        session = AsyncMock()
        service = PeerAnalysisService(session)

        mock_screener = MagicMock()
        mock_screener.get_peer_comparison = AsyncMock(return_value=SAMPLE_PEER_DATA)

        # Mock Gemini response with .parsed
        mock_response = MagicMock()
        mock_response.parsed = SAMPLE_AI_RESPONSE
        mock_response.text = None

        mock_gemini = MagicMock()
        mock_gemini._call_gemini = AsyncMock(return_value=mock_response)
        mock_gemini._record_usage = AsyncMock()

        with patch("app.services.peer_analysis_service.ScreenerService", return_value=mock_screener), \
             patch("app.services.peer_analysis_service.genai") as mock_genai, \
             patch("app.services.peer_analysis_service.GeminiClient", return_value=mock_gemini), \
             patch("app.services.peer_analysis_service._gemini_lock", AsyncMock()):

            result = await service.analyze("VNM")

        assert result["symbol"] == "VNM"
        assert result["sector"] == "Hàng tiêu dùng"
        assert result["overall_verdict"] == "Vượt trội so với ngành"
        assert len(result["strengths"]) == 2
        assert len(result["weaknesses"]) == 1
        assert "recommendation" in result
        assert "peer_position" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_text_parse(self):
        session = AsyncMock()
        service = PeerAnalysisService(session)

        mock_screener = MagicMock()
        mock_screener.get_peer_comparison = AsyncMock(return_value=SAMPLE_PEER_DATA)

        # Mock Gemini response with .parsed = None, .text = JSON
        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = SAMPLE_AI_RESPONSE.model_dump_json()

        mock_gemini = MagicMock()
        mock_gemini._call_gemini = AsyncMock(return_value=mock_response)
        mock_gemini._record_usage = AsyncMock()

        with patch("app.services.peer_analysis_service.ScreenerService", return_value=mock_screener), \
             patch("app.services.peer_analysis_service.genai") as mock_genai, \
             patch("app.services.peer_analysis_service.GeminiClient", return_value=mock_gemini), \
             patch("app.services.peer_analysis_service._gemini_lock", AsyncMock()):

            result = await service.analyze("VNM")

        assert result["symbol"] == "VNM"
        assert result["overall_verdict"] == "Vượt trội so với ngành"

    @pytest.mark.asyncio
    async def test_raises_on_empty_gemini_response(self):
        session = AsyncMock()
        service = PeerAnalysisService(session)

        mock_screener = MagicMock()
        mock_screener.get_peer_comparison = AsyncMock(return_value=SAMPLE_PEER_DATA)

        mock_response = MagicMock()
        mock_response.parsed = None
        mock_response.text = None

        mock_gemini = MagicMock()
        mock_gemini._call_gemini = AsyncMock(return_value=mock_response)
        mock_gemini._record_usage = AsyncMock()

        with patch("app.services.peer_analysis_service.ScreenerService", return_value=mock_screener), \
             patch("app.services.peer_analysis_service.genai") as mock_genai, \
             patch("app.services.peer_analysis_service.GeminiClient", return_value=mock_gemini), \
             patch("app.services.peer_analysis_service._gemini_lock", AsyncMock()):

            with pytest.raises(ValueError, match="Gemini returned empty"):
                await service.analyze("VNM")
