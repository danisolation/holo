"""Tests for simulator AI review schemas, service, and comparison endpoint.

Phase 109: Unit tests — no actual Gemini calls.
"""
import pytest
from cachetools import TTLCache


# ── Schema validation tests ─────────────────────────────────────────────────


class TestPortfolioReviewResponseSchema:
    """Validate PortfolioReviewResponse accepts valid data."""

    def test_valid_data(self):
        from app.schemas.simulator_review import PortfolioReviewResponse

        data = {
            "overall_assessment": "Danh mục đầu tư có hiệu suất tốt.",
            "strengths": ["Đa dạng hóa tốt", "Tỷ lệ thắng cao"],
            "weaknesses": ["Tập trung quá nhiều vào ngành ngân hàng"],
            "suggestions": ["Giảm tỷ trọng ngân hàng", "Thêm cổ phiếu công nghệ"],
            "risk_assessment": "Rủi ro trung bình do tập trung ngành.",
            "score": 7,
        }
        result = PortfolioReviewResponse.model_validate(data)
        assert result.score == 7
        assert len(result.strengths) == 2
        assert len(result.weaknesses) == 1
        assert len(result.suggestions) == 2

    def test_empty_lists(self):
        from app.schemas.simulator_review import PortfolioReviewResponse

        data = {
            "overall_assessment": "Chưa có giao dịch.",
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "risk_assessment": "Không có rủi ro.",
            "score": 5,
        }
        result = PortfolioReviewResponse.model_validate(data)
        assert result.strengths == []


class TestTradeReviewResponseSchema:
    """Validate TradeReviewResponse accepts valid data."""

    def test_valid_data(self):
        from app.schemas.simulator_review import TradeReviewResponse

        data = {
            "entry_analysis": "Điểm vào tốt, mua tại vùng hỗ trợ.",
            "exit_analysis": "Bán sớm, có thể giữ thêm.",
            "what_went_well": ["Chọn đúng mã", "Thời điểm mua hợp lý"],
            "what_could_improve": ["Giữ lâu hơn để tối đa lợi nhuận"],
            "pattern_identified": "Mẫu hình hai đáy (double bottom)",
            "overall_verdict": "Tốt",
        }
        result = TradeReviewResponse.model_validate(data)
        assert result.overall_verdict == "Tốt"
        assert len(result.what_went_well) == 2


class TestComparisonResponseSchema:
    """Validate ComparisonResponse accepts valid data with nested types."""

    def test_valid_data(self):
        from app.schemas.simulator import ComparisonResponse

        data = {
            "ai_equity_history": [
                {"date": "2025-01-01", "equity": 100000000.0},
                {"date": "2025-01-15", "equity": 102000000.0},
            ],
            "user_equity_history": [
                {"date": "2025-01-01", "equity": 100000000.0},
                {"date": "2025-01-15", "equity": 99000000.0},
            ],
            "ai_stats": {
                "total_trades": 10,
                "ai_trades": 8,
                "manual_trades": 2,
                "ai_win_rate": 75.0,
                "manual_win_rate": 50.0,
                "ai_avg_return_pct": 3.5,
                "manual_avg_return_pct": 1.2,
                "ai_total_pnl": 5000000.0,
                "manual_total_pnl": 1000000.0,
            },
            "user_stats": {
                "total_trades": 5,
                "ai_trades": 0,
                "manual_trades": 5,
                "ai_win_rate": 0.0,
                "manual_win_rate": 60.0,
                "ai_avg_return_pct": 0.0,
                "manual_avg_return_pct": 2.0,
                "ai_total_pnl": 0.0,
                "manual_total_pnl": 2000000.0,
            },
            "ai_portfolio": {
                "name": "ai",
                "starting_capital": 100000000.0,
                "current_cash": 50000000.0,
                "total_equity": 105000000.0,
                "total_pnl": 5000000.0,
                "total_pnl_pct": 5.0,
                "position_count": 3,
            },
            "user_portfolio": {
                "name": "user",
                "starting_capital": 100000000.0,
                "current_cash": 70000000.0,
                "total_equity": 99000000.0,
                "total_pnl": -1000000.0,
                "total_pnl_pct": -1.0,
                "position_count": 2,
            },
        }
        result = ComparisonResponse.model_validate(data)
        assert len(result.ai_equity_history) == 2
        assert result.ai_portfolio.name == "ai"
        assert result.user_portfolio.name == "user"
        assert result.ai_stats.total_trades == 10


# ── Endpoint validation tests ───────────────────────────────────────────────


class TestPortfolioReviewEndpointValidation:
    """POST /simulator/review/portfolio rejects invalid portfolio_type."""

    def test_validates_portfolio_type(self):
        """Invalid portfolio_type should trigger _validate_portfolio_type."""
        from app.api.simulator import _validate_portfolio_type
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_portfolio_type("invalid")
        assert exc_info.value.status_code == 400
        assert "ai" in exc_info.value.detail or "user" in exc_info.value.detail


class TestTradeReviewEndpointValidation:
    """POST /simulator/review/trade/{id} rejects invalid portfolio_type."""

    def test_validates_portfolio_type(self):
        from app.api.simulator import _validate_portfolio_type
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_portfolio_type("bogus")
        assert exc_info.value.status_code == 400


# ── Service-level tests ─────────────────────────────────────────────────────


class TestReviewSystemInstruction:
    """Verify system instruction is Vietnamese."""

    def test_is_vietnamese(self):
        from app.services.simulator_review_service import REVIEW_SYSTEM_INSTRUCTION

        assert "tiếng Việt" in REVIEW_SYSTEM_INSTRUCTION


class TestTTLCacheExists:
    """Verify module-level TTLCache for portfolio reviews."""

    def test_cache_is_ttl_cache(self):
        from app.services.simulator_review_service import _portfolio_review_cache

        assert isinstance(_portfolio_review_cache, TTLCache)
        assert _portfolio_review_cache.maxsize == 4
        assert _portfolio_review_cache.ttl == 300


class TestRouteRegistration:
    """Verify new routes are registered on the router."""

    def test_review_portfolio_route_exists(self):
        from app.api.simulator import router

        paths = [r.path for r in router.routes]
        assert "/simulator/review/portfolio" in paths

    def test_review_trade_route_exists(self):
        from app.api.simulator import router

        paths = [r.path for r in router.routes]
        assert "/simulator/review/trade/{trade_id}" in paths

    def test_comparison_route_exists(self):
        from app.api.simulator import router

        paths = [r.path for r in router.routes]
        assert "/simulator/comparison" in paths
