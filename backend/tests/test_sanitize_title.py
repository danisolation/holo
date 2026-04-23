"""Unit tests for _sanitize_title (Phase 39: AIQ-03)."""
from app.services.analysis.context_builder import _sanitize_title


class TestSanitizeTitle:
    def test_normal_text_unchanged(self):
        assert _sanitize_title("Cổ phiếu VNM tăng mạnh") == "Cổ phiếu VNM tăng mạnh"

    def test_strips_control_characters(self):
        assert _sanitize_title("Hello\x00World\x0b!") == "HelloWorld!"

    def test_collapses_whitespace(self):
        assert _sanitize_title("  nhiều   khoảng   trắng  ") == "nhiều khoảng trắng"

    def test_truncates_at_300_chars(self):
        long_title = "A" * 400
        result = _sanitize_title(long_title)
        assert len(result) == 301  # 300 + "…"
        assert result.endswith("…")

    def test_empty_string(self):
        assert _sanitize_title("") == ""
