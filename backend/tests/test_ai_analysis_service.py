"""Tests for AIAnalysisService — Gemini integration (mocked)."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestAIAnalysisServiceInit:
    """Test service initialization."""

    def test_raises_without_api_key(self):
        """AIAnalysisService must raise ValueError if no API key."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3

            from app.services.ai_analysis_service import AIAnalysisService
            mock_session = AsyncMock()
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                AIAnalysisService(mock_session)


class TestPromptBuilding:
    """Test prompt generation (no API call needed)."""

    def test_technical_prompt_includes_ticker_symbols(self):
        """Technical prompt must contain the ticker symbols."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3
            with patch("app.services.ai_analysis_service.genai"):
                from app.services.ai_analysis_service import AIAnalysisService
                mock_session = AsyncMock()
                svc = AIAnalysisService(mock_session, api_key="test-key")
                prompt = svc._build_technical_prompt({
                    "VNM": {"rsi_14": [45.2, 46.1, 47.3, 48.0, 49.1],
                            "rsi_zone": "neutral", "macd_line": [0.1, 0.2, 0.3, 0.4, 0.5],
                            "macd_signal": [0.05, 0.1, 0.15, 0.2, 0.25],
                            "macd_histogram": [0.05, 0.1, 0.15, 0.2, 0.25],
                            "macd_crossover": "none",
                            "sma_20": 100.0, "sma_50": 98.0, "sma_200": 95.0,
                            "ema_12": 101.0, "ema_26": 99.0,
                            "bb_upper": 110.0, "bb_middle": 100.0, "bb_lower": 90.0},
                    "FPT": {"rsi_14": [55.0, 56.2, 57.1, 58.3, 59.0],
                            "rsi_zone": "neutral", "macd_line": [0.5, 0.6, 0.7, 0.8, 0.9],
                            "macd_signal": [0.3, 0.4, 0.5, 0.6, 0.7],
                            "macd_histogram": [0.2, 0.2, 0.2, 0.2, 0.2],
                            "macd_crossover": "none",
                            "sma_20": 200.0, "sma_50": 195.0, "sma_200": 190.0,
                            "ema_12": 201.0, "ema_26": 198.0,
                            "bb_upper": 210.0, "bb_middle": 200.0, "bb_lower": 190.0},
                })
                assert "VNM" in prompt
                assert "FPT" in prompt

    def test_fundamental_prompt_includes_financial_data(self):
        """Fundamental prompt must contain financial metric names."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3
            with patch("app.services.ai_analysis_service.genai"):
                from app.services.ai_analysis_service import AIAnalysisService
                mock_session = AsyncMock()
                svc = AIAnalysisService(mock_session, api_key="test-key")
                prompt = svc._build_fundamental_prompt({
                    "VNM": {"period": "Q4/2024", "pe": 15.2, "pb": 3.1, "eps": 5000.0,
                            "roe": 0.25, "roa": 0.12,
                            "revenue_growth": 0.08, "profit_growth": 0.05,
                            "current_ratio": 1.5, "debt_to_equity": 0.3},
                })
                assert "VNM" in prompt
                # Should mention financial concepts
                assert any(term in prompt.lower() for term in ["p/e", "pe", "financial", "fundamental"])


class TestSentimentPrompt:
    """Test sentiment prompt generation."""

    def test_sentiment_prompt_includes_ticker_and_titles(self):
        """Sentiment prompt must contain ticker symbols and news titles."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3
            mock_settings.cafef_delay_seconds = 1.0
            mock_settings.cafef_news_days = 7
            with patch("app.services.ai_analysis_service.genai"):
                from app.services.ai_analysis_service import AIAnalysisService
                mock_session = AsyncMock()
                svc = AIAnalysisService(mock_session, api_key="test-key")
                prompt = svc._build_sentiment_prompt({
                    "VNM": {
                        "news_titles": ["Vinamilk lên kế hoạch mở rộng", "VNM báo lãi quý 2"],
                        "news_count": 2,
                    },
                    "FPT": {
                        "news_titles": [],
                        "news_count": 0,
                    },
                })
                assert "VNM" in prompt
                assert "FPT" in prompt
                assert "Vinamilk" in prompt
                assert "Không có tin tức" in prompt  # FPT has no news

    def test_sentiment_prompt_handles_empty_news(self):
        """Sentiment prompt must handle ticker with zero news gracefully."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3
            mock_settings.cafef_delay_seconds = 1.0
            mock_settings.cafef_news_days = 7
            with patch("app.services.ai_analysis_service.genai"):
                from app.services.ai_analysis_service import AIAnalysisService
                mock_session = AsyncMock()
                svc = AIAnalysisService(mock_session, api_key="test-key")
                prompt = svc._build_sentiment_prompt({
                    "ABC": {"news_titles": [], "news_count": 0},
                })
                assert "ABC" in prompt
                assert "0 tin tức" in prompt


class TestCombinedPrompt:
    """Test combined recommendation prompt generation."""

    def test_combined_prompt_includes_all_dimensions(self):
        """Combined prompt must contain tech, fund, and sentiment data."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3
            mock_settings.cafef_delay_seconds = 1.0
            mock_settings.cafef_news_days = 7
            with patch("app.services.ai_analysis_service.genai"):
                from app.services.ai_analysis_service import AIAnalysisService
                mock_session = AsyncMock()
                svc = AIAnalysisService(mock_session, api_key="test-key")
                prompt = svc._build_combined_prompt({
                    "VNM": {
                        "tech_signal": "buy",
                        "tech_score": 7,
                        "fund_signal": "good",
                        "fund_score": 8,
                        "sent_signal": "positive",
                        "sent_score": 7,
                    },
                })
                assert "VNM" in prompt
                assert "buy" in prompt
                assert "good" in prompt
                assert "positive" in prompt
                # Should mention mua/ban/giu (recommendation options)
                assert "mua" in prompt.lower()

    def test_combined_prompt_handles_missing_sentiment(self):
        """Combined prompt must show neutral sentiment when missing."""
        with patch("app.services.ai_analysis_service.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_model = "gemini-2.0-flash"
            mock_settings.gemini_batch_size = 10
            mock_settings.gemini_delay_seconds = 4.0
            mock_settings.gemini_max_retries = 3
            mock_settings.cafef_delay_seconds = 1.0
            mock_settings.cafef_news_days = 7
            with patch("app.services.ai_analysis_service.genai"):
                from app.services.ai_analysis_service import AIAnalysisService
                mock_session = AsyncMock()
                svc = AIAnalysisService(mock_session, api_key="test-key")
                prompt = svc._build_combined_prompt({
                    "VNM": {
                        "tech_signal": "buy",
                        "tech_score": 7,
                        "fund_signal": "good",
                        "fund_score": 8,
                        "sent_signal": "neutral",  # Default when missing
                        "sent_score": 5,
                    },
                })
                assert "neutral" in prompt


class TestSentimentSchema:
    """Test sentiment and combined Pydantic schemas."""

    def test_sentiment_batch_response_validates(self):
        """SentimentBatchResponse must validate with correct data."""
        from app.schemas.analysis import SentimentBatchResponse
        data = {
            "analyses": [
                {"ticker": "VNM", "sentiment": "positive", "score": 7, "reasoning": "Tin tốt"},
                {"ticker": "FPT", "sentiment": "neutral", "score": 5, "reasoning": "Không có tin"},
            ]
        }
        resp = SentimentBatchResponse(**data)
        assert len(resp.analyses) == 2
        assert resp.analyses[0].sentiment.value == "positive"

    def test_combined_batch_response_validates(self):
        """CombinedBatchResponse must validate with correct data."""
        from app.schemas.analysis import CombinedBatchResponse
        data = {
            "analyses": [
                {"ticker": "VNM", "recommendation": "mua", "confidence": 8,
                 "explanation": "Tất cả tín hiệu đồng thuận tích cực."},
            ]
        }
        resp = CombinedBatchResponse(**data)
        assert resp.analyses[0].recommendation.value == "mua"
        assert resp.analyses[0].confidence == 8

    def test_confidence_range_validation(self):
        """Confidence must be between 1 and 10."""
        from app.schemas.analysis import CombinedBatchResponse
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            CombinedBatchResponse(**{
                "analyses": [
                    {"ticker": "VNM", "recommendation": "mua", "confidence": 11,
                     "explanation": "Test"},
                ]
            })

    def test_recommendation_enum_values(self):
        """Recommendation enum must have mua, ban, giu values."""
        from app.schemas.analysis import Recommendation
        assert Recommendation.MUA.value == "mua"
        assert Recommendation.BAN.value == "ban"
        assert Recommendation.GIU.value == "giu"


# ------------------------------------------------------------------
# Helper for service instantiation (DRY)
# ------------------------------------------------------------------

def _make_service(mock_session=None):
    """Create AIAnalysisService with all settings mocked."""
    with patch("app.services.ai_analysis_service.settings") as ms:
        ms.gemini_api_key = "test-key"
        ms.gemini_model = "gemini-2.0-flash"
        ms.gemini_batch_size = 10
        ms.gemini_delay_seconds = 4.0
        ms.gemini_max_retries = 3
        ms.cafef_delay_seconds = 1.0
        ms.cafef_news_days = 7
        with patch("app.services.ai_analysis_service.genai"):
            from app.services.ai_analysis_service import AIAnalysisService
            return AIAnalysisService(mock_session or AsyncMock(), api_key="test-key")


# ------------------------------------------------------------------
# Phase 9 Tests: AI Prompt Improvements (AI-07 through AI-13)
# ------------------------------------------------------------------

import re


class TestSystemInstruction:
    """Tests for AI-07 (system_instruction separation) and AI-09 (scoring rubric)."""

    @pytest.mark.asyncio
    async def test_system_instruction_passed_to_gemini(self):
        """system_instruction must reach GenerateContentConfig."""
        svc = _make_service()
        mock_response = MagicMock()
        mock_response.parsed = MagicMock()
        svc.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        await svc._call_gemini_with_retry(
            "test prompt", dict, temperature=0.1, system_instruction="test instruction"
        )

        call_kwargs = svc.client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.system_instruction == "test instruction"
        assert config.temperature == 0.1

    def test_scoring_rubric_contains_all_anchors(self):
        """SCORING_RUBRIC must contain all 5 anchor ranges."""
        from app.services.ai_analysis_service import SCORING_RUBRIC
        for anchor in ("1-2", "3-4", "5-6", "7-8", "9-10"):
            assert anchor in SCORING_RUBRIC, f"Missing anchor {anchor}"

    def test_all_system_instructions_contain_rubric(self):
        """Each system instruction constant must embed the scoring rubric."""
        from app.services.ai_analysis_service import (
            SCORING_RUBRIC,
            TECHNICAL_SYSTEM_INSTRUCTION,
            FUNDAMENTAL_SYSTEM_INSTRUCTION,
            SENTIMENT_SYSTEM_INSTRUCTION,
            COMBINED_SYSTEM_INSTRUCTION,
        )
        for name, instr in [
            ("TECHNICAL", TECHNICAL_SYSTEM_INSTRUCTION),
            ("FUNDAMENTAL", FUNDAMENTAL_SYSTEM_INSTRUCTION),
            ("SENTIMENT", SENTIMENT_SYSTEM_INSTRUCTION),
            ("COMBINED", COMBINED_SYSTEM_INSTRUCTION),
        ]:
            assert SCORING_RUBRIC in instr, f"{name} missing SCORING_RUBRIC"


class TestTemperatureConfig:
    """Tests for AI-13 (per-type temperature tuning)."""

    def test_temperature_values(self):
        """ANALYSIS_TEMPERATURES must match D-09-06 specification."""
        from app.services.ai_analysis_service import ANALYSIS_TEMPERATURES
        from app.models.ai_analysis import AnalysisType
        assert ANALYSIS_TEMPERATURES[AnalysisType.TECHNICAL] == 0.1
        assert ANALYSIS_TEMPERATURES[AnalysisType.FUNDAMENTAL] == 0.2
        assert ANALYSIS_TEMPERATURES[AnalysisType.SENTIMENT] == 0.3
        assert ANALYSIS_TEMPERATURES[AnalysisType.COMBINED] == 0.2

    def test_temperature_covers_all_types(self):
        """Every AnalysisType must have a temperature entry."""
        from app.services.ai_analysis_service import ANALYSIS_TEMPERATURES
        from app.models.ai_analysis import AnalysisType
        for at in AnalysisType:
            assert at in ANALYSIS_TEMPERATURES, f"Missing temp for {at}"


class TestLanguageConsistency:
    """All AI prompts should be in Vietnamese."""

    _VN_REGEX = re.compile(
        r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]",
        re.IGNORECASE,
    )

    def test_all_prompts_are_vietnamese(self):
        """All system instructions must contain Vietnamese diacritics."""
        from app.services.ai_analysis_service import (
            TECHNICAL_SYSTEM_INSTRUCTION,
            FUNDAMENTAL_SYSTEM_INSTRUCTION,
            SENTIMENT_SYSTEM_INSTRUCTION,
            COMBINED_SYSTEM_INSTRUCTION,
        )
        assert self._VN_REGEX.search(TECHNICAL_SYSTEM_INSTRUCTION), "TECHNICAL missing VN chars"
        assert self._VN_REGEX.search(FUNDAMENTAL_SYSTEM_INSTRUCTION), "FUNDAMENTAL missing VN chars"
        assert self._VN_REGEX.search(SENTIMENT_SYSTEM_INSTRUCTION), "SENTIMENT missing VN chars"
        assert self._VN_REGEX.search(COMBINED_SYSTEM_INSTRUCTION), "COMBINED missing VN chars"


class TestFewShotExamples:
    """Tests for AI-08 (few-shot examples in prompt text)."""

    def _sample_technical_data(self):
        return {
            "VNM": {
                "rsi_14": [42.1, 44.3, 46.8, 49.2, 52.1],
                "rsi_zone": "neutral",
                "macd_line": [0.1, 0.2, 0.3, 0.4, 0.5],
                "macd_signal": [0.1, 0.15, 0.2, 0.25, 0.3],
                "macd_histogram": [-0.1, 0.05, 0.1, 0.15, 0.2],
                "macd_crossover": "bullish",
                "sma_20": 82000, "sma_50": 80500, "sma_200": 78000,
                "ema_12": 81000, "ema_26": 80000,
                "bb_upper": 85000, "bb_middle": 82000, "bb_lower": 79000,
            }
        }

    def test_all_prompt_builders_have_few_shot(self):
        """All 4 prompt builders must include few-shot examples."""
        svc = _make_service()

        tech_prompt = svc._build_technical_prompt(self._sample_technical_data())
        assert "Ví dụ" in tech_prompt or "Kết quả mẫu" in tech_prompt

        fund_prompt = svc._build_fundamental_prompt({
            "VNM": {"period": "Q4/2024", "pe": 15.2, "pb": 3.1, "eps": 5000,
                     "roe": 0.25, "roa": 0.12, "revenue_growth": 0.08,
                     "profit_growth": 0.05, "current_ratio": 1.5, "debt_to_equity": 0.3}
        })
        assert "Ví dụ" in fund_prompt or "Kết quả mẫu" in fund_prompt

        sent_prompt = svc._build_sentiment_prompt({
            "VNM": {"news_titles": ["Tin tốt"]}
        })
        assert "Ví dụ" in sent_prompt or "Kết quả mẫu" in sent_prompt

        comb_prompt = svc._build_combined_prompt({
            "VNM": {"tech_signal": "buy", "tech_score": 7,
                     "fund_signal": "good", "fund_score": 8,
                     "sent_signal": "positive", "sent_score": 7}
        })
        assert "Ví dụ" in comb_prompt or "Kết quả mẫu" in comb_prompt


class TestTechnicalClosePrice:
    """Tests for AI-10 (close price and SMA distances in prompt)."""

    def _base_data(self):
        return {
            "rsi_14": [50.0], "rsi_zone": "neutral",
            "macd_line": [0.1], "macd_signal": [0.05],
            "macd_histogram": [0.05], "macd_crossover": "none",
            "sma_20": 80000, "sma_50": 78000, "sma_200": 75000,
            "ema_12": 81000, "ema_26": 80000,
            "bb_upper": 85000, "bb_middle": 82000, "bb_lower": 79000,
        }

    def test_technical_prompt_includes_close_price(self):
        """Prompt must show formatted close price when available."""
        svc = _make_service()
        data = self._base_data()
        data["latest_close"] = 78500.0
        prompt = svc._build_technical_prompt({"VNM": data})
        assert "78,500" in prompt
        assert "VND" in prompt

    def test_technical_prompt_includes_sma_distances(self):
        """Prompt must show price vs SMA percentages when available."""
        svc = _make_service()
        data = self._base_data()
        data["latest_close"] = 78500.0
        data["price_vs_sma_20_pct"] = 2.3
        data["price_vs_sma_50_pct"] = -1.5
        data["price_vs_sma_200_pct"] = 8.7
        prompt = svc._build_technical_prompt({"VNM": data})
        assert "+2.3%" in prompt
        assert "-1.5" in prompt
        assert "8.7" in prompt

    def test_technical_prompt_handles_missing_close(self):
        """Prompt must not crash or show close when data is absent."""
        svc = _make_service()
        data = self._base_data()
        prompt = svc._build_technical_prompt({"VNM": data})
        assert "Giá đóng cửa gần nhất" not in prompt
        assert "Giá vs SMA" not in prompt


class TestStructuredOutputRetry:
    """Tests for AI-12 (low-temp retry at 0.05 before JSON parse fallback)."""

    _MINIMAL_TECH_DATA = {
        "VNM": {
            "rsi_14": [50.0], "rsi_zone": "neutral",
            "macd_line": [0.1], "macd_signal": [0.05],
            "macd_histogram": [0.05], "macd_crossover": "none",
            "sma_20": 80000, "sma_50": 78000, "sma_200": 75000,
            "ema_12": 81000, "ema_26": 80000,
            "bb_upper": 85000, "bb_middle": 82000, "bb_lower": 79000,
        }
    }

    @pytest.mark.asyncio
    async def test_retry_at_low_temp_on_parsed_none(self):
        """When response.parsed is None, must retry at temperature=0.05."""
        svc = _make_service()

        from app.schemas.analysis import TechnicalBatchResponse
        valid_result = TechnicalBatchResponse(analyses=[])

        first_resp = MagicMock()
        first_resp.parsed = None
        first_resp.text = '{"analyses": []}'
        first_resp.usage_metadata.total_token_count = 100

        second_resp = MagicMock()
        second_resp.parsed = valid_result
        second_resp.usage_metadata.total_token_count = 100

        with patch.object(svc, "_call_gemini", new_callable=AsyncMock, side_effect=[first_resp, second_resp]) as mock_call:
            result = await svc._analyze_technical_batch(self._MINIMAL_TECH_DATA)

        assert result is valid_result
        assert mock_call.call_count == 2
        retry_args = mock_call.call_args_list[1]
        assert retry_args[0][2] == 0.05  # temperature arg

    @pytest.mark.asyncio
    async def test_no_retry_when_parsed_succeeds(self):
        """When response.parsed is valid, no retry should occur."""
        svc = _make_service()

        from app.schemas.analysis import TechnicalBatchResponse
        valid_result = TechnicalBatchResponse(analyses=[])

        resp = MagicMock()
        resp.parsed = valid_result
        resp.usage_metadata.total_token_count = 100

        with patch.object(svc, "_call_gemini", new_callable=AsyncMock, return_value=resp) as mock_call:
            result = await svc._analyze_technical_batch(self._MINIMAL_TECH_DATA)

        assert result is valid_result
        assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_json_fallback_after_retry_fails(self):
        """When both calls return parsed=None, JSON parse fallback must work."""
        svc = _make_service()

        first_resp = MagicMock()
        first_resp.parsed = None
        first_resp.text = '{"analyses": []}'
        first_resp.usage_metadata.total_token_count = 100

        second_resp = MagicMock()
        second_resp.parsed = None
        second_resp.text = '{"analyses": []}'
        second_resp.usage_metadata.total_token_count = 100

        with patch.object(svc, "_call_gemini", new_callable=AsyncMock, side_effect=[first_resp, second_resp]) as mock_call:
            result = await svc._analyze_technical_batch(self._MINIMAL_TECH_DATA)

        assert mock_call.call_count == 2
        assert result is not None
        assert len(result.analyses) == 0
