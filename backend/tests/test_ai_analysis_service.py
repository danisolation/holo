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
