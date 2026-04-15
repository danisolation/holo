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
