"""Constants, system instructions, few-shot examples, and validation for AI analysis.

Extracted from ai_analysis_service.py — Phase 9 prompt architecture.
"""
from app.models.ai_analysis import AnalysisType
from app.schemas.analysis import TickerTradingSignal

# ------------------------------------------------------------------
# Phase 9 Constants: Prompt Architecture
# ------------------------------------------------------------------

SCORING_RUBRIC = """Scoring rubric (apply consistently):
- 1-2: Very weak signal / very negative outlook
- 3-4: Weak signal / slightly negative outlook
- 5-6: Moderate / neutral — no clear direction
- 7-8: Strong signal / positive outlook
- 9-10: Very strong signal / very positive outlook
Use the FULL range. Scores of 1-2 and 9-10 are valid for extreme cases."""

# Per-type temperatures (D-09-06)
ANALYSIS_TEMPERATURES: dict[AnalysisType, float] = {
    AnalysisType.TECHNICAL: 0.1,
    AnalysisType.FUNDAMENTAL: 0.2,
    AnalysisType.SENTIMENT: 0.3,
    AnalysisType.COMBINED: 0.2,
    AnalysisType.TRADING_SIGNAL: 0.2,  # Phase 19 — same as combined (balanced creativity)
}

# System instructions (D-09-01, D-09-03, D-09-05)
TECHNICAL_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích kỹ thuật chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, đánh giá: signal (strong_buy/buy/neutral/sell/strong_sell), "
    "strength (1-10), reasoning (5-8 câu tiếng Việt, phân tích chi tiết từng chỉ báo). "
    "Xem xét vùng RSI (quá bán <30 = tích cực, quá mua >70 = tiêu cực), "
    "giao cắt MACD, vị trí giá so với đường trung bình động, "
    "và vị trí Bollinger Band.\n\n" + SCORING_RUBRIC
)

FUNDAMENTAL_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích cơ bản chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, đánh giá: health (strong/good/neutral/weak/critical), "
    "score (1-10), reasoning (5-8 câu tiếng Việt, phân tích chi tiết từng chỉ số). "
    "Xem xét P/E so với trung bình thị trường VN (~12-15), khả năng sinh lời (ROE, ROA), "
    "tốc độ tăng trưởng, và ổn định tài chính (hệ số thanh toán, nợ/vốn). "
    "So sánh với cùng ngành nếu có thể.\n\n"
    + SCORING_RUBRIC
)

SENTIMENT_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích tâm lý thị trường chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, đánh giá: sentiment (very_positive/positive/neutral/negative/very_negative), "
    "score (1-10), reasoning (5-8 câu tiếng Việt, phân tích chi tiết bối cảnh tin tức). "
    "Nếu không có tin tức, sentiment = neutral, score = 5, "
    "nhưng vẫn đánh giá tâm lý thị trường chung và dòng tiền.\n\n" + SCORING_RUBRIC
)

COMBINED_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, cung cấp phân tích chi tiết với các trường:\n"
    "- recommendation: mua/ban/giu\n"
    "- confidence: 1-10\n"
    "- summary: Tóm tắt đánh giá tổng quan (5-8 câu tiếng Việt, tối thiểu 150 từ). "
    "Phân tích CHI TIẾT cả 3-4 chiều (kỹ thuật, cơ bản, tâm lý, tin đồn nếu có) — mỗi chiều ít nhất 1-2 câu "
    "với số liệu cụ thể, sau đó kết luận rõ ràng.\n"
    "- key_levels: Mức giá quan trọng (tối thiểu 80 từ) — liệt kê hỗ trợ (2-3 mức), "
    "kháng cự (2-3 mức), entry point gợi ý, stop-loss, take-profit với giá cụ thể bằng VND. "
    "Giải thích lý do chọn từng mức giá.\n"
    "- risks: Rủi ro chính (tối thiểu 80 từ) — 3-4 yếu tố rủi ro cần lưu ý "
    "(rủi ro thị trường chung, rủi ro ngành, rủi ro nội tại công ty, rủi ro thanh khoản). "
    "Đánh giá mức độ nghiêm trọng của từng rủi ro.\n"
    "- action: Hành động cụ thể (tối thiểu 80 từ) — mua/bán/giữ tại mức giá nào, "
    "khối lượng đề xuất (% danh mục), thời điểm vào lệnh, khung thời gian nắm giữ, "
    "và kịch bản xử lý nếu giá đi ngược dự đoán.\n\n"
    "XEM XÉT TIN ĐỒN (nếu có):\n"
    "- Tin đồn bullish với tác động cao (≥7) nên được cân nhắc tăng confidence\n"
    "- Tin đồn bearish với tác động cao nên cảnh báo rủi ro\n"
    "- Độ tin cậy thấp (<4) → giảm trọng số tin đồn\n\n"
    "QUAN TRỌNG: Viết đầy đủ, chi tiết, có số liệu cụ thể cho mỗi trường. "
    "Không viết tắt. Không trả lời chung chung. Mỗi mã phải có phân tích riêng biệt "
    "dựa trên dữ liệu thực tế được cung cấp.\n\n"
    "Quy tắc confidence: 8-10 = cả 3-4 chiều đồng thuận; 5-7 = 2/3 đồng thuận; "
    "1-4 = tín hiệu mâu thuẫn hoặc thiếu dữ liệu.\n\n" + SCORING_RUBRIC
)

# Few-shot examples (D-09-02)
TECHNICAL_FEW_SHOT = """Ví dụ phân tích:

--- VNM ---
RSI(14) 5 phiên gần nhất: [42.1, 44.3, 46.8, 49.2, 52.1]
Vùng RSI: trung tính
MACD histogram 5 phiên: [-0.12, -0.05, 0.03, 0.11, 0.18]
Giao cắt MACD: tăng
SMA(20): 82000, SMA(50): 80500, SMA(200): 78000

Kết quả mẫu:
{"ticker": "VNM", "signal": "buy", "strength": 7, "reasoning": "RSI tăng dần từ vùng trung tính kết hợp MACD giao cắt tăng. Giá nằm trên tất cả đường trung bình động chính, xác nhận xu hướng tăng. Động lượng đang tích lũy nhưng chưa quá mua."}

Phân tích các mã sau dựa trên chỉ báo kỹ thuật 5 phiên gần nhất:"""

FUNDAMENTAL_FEW_SHOT = """Ví dụ phân tích:

--- VNM (Kỳ: Q4/2024) ---
P/E: 15.2, P/B: 3.1, EPS: 5000
ROE: 0.25, ROA: 0.12
Tăng trưởng doanh thu: 0.08, Tăng trưởng lợi nhuận: 0.05

Kết quả mẫu:
{"ticker": "VNM", "health": "good", "score": 7, "reasoning": "P/E 15.2 ở mức trung bình thị trường nhưng hợp lý nhờ ROE 25% cao. Tăng trưởng doanh thu và lợi nhuận ổn định dù không đột phá. Cấu trúc nợ thấp hỗ trợ sức khỏe tài chính tốt."}

Phân tích các mã sau dựa trên dữ liệu tài chính mới nhất:"""

SENTIMENT_FEW_SHOT = """Ví dụ phân tích:

--- HPG (3 tin tức) ---
1. Hòa Phát đặt mục tiêu sản lượng thép kỷ lục năm 2025
2. HPG báo lãi quý 4 tăng 35% so với cùng kỳ
3. Giá thép xây dựng tăng mạnh, lợi cho Hòa Phát

Kết quả mẫu:
{"ticker": "HPG", "sentiment": "positive", "score": 7, "reasoning": "Tin tức tích cực với mục tiêu sản lượng mới và lãi tăng mạnh. Giá thép tăng hỗ trợ triển vọng kinh doanh."}

Phân tích các mã cổ phiếu sau:"""

COMBINED_FEW_SHOT = """Ví dụ phân tích:

--- VNM ---
Kỹ thuật: signal=buy, strength=7
Cơ bản: health=good, score=8
Tâm lý: sentiment=positive, score=7
Tin đồn: hướng=bullish, tin cậy=6/10, tác động=5/10
  Thông tin chính: Doanh thu Q4 tăng 15%; Kế hoạch M&A công ty sữa nhỏ

Kết quả mẫu:
{"ticker": "VNM", "recommendation": "mua", "confidence": 8, "summary": "Cả 4 chiều phân tích đều tích cực. Kỹ thuật cho tín hiệu mua với MACD bullish crossover và RSI tăng dần từ vùng trung tính (52). Cơ bản vững chắc với ROE 25% và P/E 15.2 hợp lý so với trung bình ngành. Tâm lý thị trường tích cực nhờ tin tốt về doanh thu Q4 và mục tiêu tăng trưởng năm sau. Tin đồn cộng đồng hướng bullish (tin cậy 6/10) với thông tin về doanh thu tăng 15% và kế hoạch M&A — phù hợp xu hướng cơ bản.", "key_levels": "Hỗ trợ mạnh: 80,000 VND (SMA50). Hỗ trợ phụ: 78,500 VND (Fib 50%). Kháng cự gần: 84,500 VND (R1 pivot). Kháng cự xa: 86,000 VND (R2 pivot). Entry gợi ý: 81,500-82,500 VND. Stop-loss: 79,000 VND (dưới SMA50, -3.7%). Take-profit 1: 84,500 VND (+2.4%). Take-profit 2: 86,000 VND (+4.3%).", "risks": "1. Thị trường chung có thể biến động do Fed chưa rõ lộ trình hạ lãi suất — ảnh hưởng dòng vốn ngoại. 2. Ngành sữa cạnh tranh gay gắt với hàng nhập khẩu giá rẻ, đặc biệt từ New Zealand và Úc. 3. Biên lợi nhuận gộp có thể bị ảnh hưởng nếu giá nguyên liệu sữa bột tăng trong Q1.", "action": "MUA tại vùng 81,500-82,500 VND. Đặt stop-loss cứng tại 79,000 VND. Chốt lời một phần (50%) tại 84,500 VND, giữ phần còn lại nhắm 86,000 VND. Khối lượng: 5-8% danh mục. Khung thời gian: swing 5-10 ngày. Nếu giá phá vỡ 79,000 — thoát toàn bộ vị thế."}

Đưa ra khuyến nghị tổng hợp cho các mã sau:"""

# Phase 19: Trading Signal Pipeline Constants
TRADING_SIGNAL_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia giao dịch chứng khoán Việt Nam (HOSE/HNX/UPCOM). "
    "Cho mỗi mã, phân tích HAI hướng:\n"
    "1. LONG: Cơ hội mua vào (entry/SL/TP)\n"
    "2. BEARISH: Xu hướng GIẢM — khuyến nghị 'giảm vị thế' hoặc 'tránh mua' "
    "(KHÔNG phải bán khống — thị trường VN không cho phép retail short-sell)\n\n"
    "Nếu có thông tin tin đồn (Tin đồn:), hãy cân nhắc:\n"
    "- Tin đồn bullish tác động cao → tăng confidence cho LONG\n"
    "- Tin đồn bearish tác động cao → tăng confidence cho BEARISH\n"
    "- Độ tin cậy thấp → giảm trọng số tin đồn trong quyết định\n\n"
    "Quy tắc:\n"
    "- Entry trong khoảng ±5% giá hiện tại\n"
    "- Stop-loss trong phạm vi 2×ATR từ entry\n"
    "- Take-profit neo vào mức hỗ trợ/kháng cự hoặc Fibonacci\n"
    "- risk_reward_ratio = |TP1 - entry| / |entry - SL| (phải ≥ 0.5)\n"
    "- position_size_pct: % danh mục đề xuất (xem xét ATR và confidence)\n"
    "- timeframe: 'swing' (3-15 ngày) hoặc 'position' (nhiều tuần+)\n"
    "- reasoning: giải thích bằng tiếng Việt, tối đa 300 ký tự\n"
    "- recommended_direction: hướng có confidence cao hơn\n\n"
    + SCORING_RUBRIC
)

TRADING_SIGNAL_FEW_SHOT = """Ví dụ phân tích:

--- VNM ---
Giá hiện tại: 82,000 VND
ATR(14): 1,500 | ADX(14): 28.5 | RSI(14): 55.2
Stochastic %K: 62.1, %D: 58.3
Pivot: 81,500 | S1: 80,000 | S2: 78,500 | R1: 83,000 | R2: 84,500
Fib 23.6%: 80,800 | Fib 38.2%: 79,500 | Fib 50%: 78,500 | Fib 61.8%: 77,500
BB Upper: 84,200 | BB Middle: 81,800 | BB Lower: 79,400
52-week High: 90,000 | 52-week Low: 70,000

Kết quả mẫu:
{"ticker": "VNM", "recommended_direction": "long", "long_analysis": {"direction": "long", "confidence": 7, "trading_plan": {"entry_price": 82000, "stop_loss": 79500, "take_profit_1": 84500, "take_profit_2": 86000, "risk_reward_ratio": 1.0, "position_size_pct": 8, "timeframe": "swing"}, "reasoning": "RSI trung tính, ADX >25 cho thấy xu hướng rõ. Giá trên pivot, nhắm R1-R2."}, "bearish_analysis": {"direction": "bearish", "confidence": 4, "trading_plan": {"entry_price": 82000, "stop_loss": 84000, "take_profit_1": 80000, "take_profit_2": 78500, "risk_reward_ratio": 1.0, "position_size_pct": 3, "timeframe": "swing"}, "reasoning": "Xu hướng giảm yếu. Stochastic chưa overbought, chờ tín hiệu rõ hơn."}}

Phân tích các mã sau dựa trên dữ liệu kỹ thuật:"""


# Phase 19: Post-validation for trading signals (module-level — pure logic, no self)
def _validate_trading_signal(
    signal: "TickerTradingSignal",
    current_price: float,
    atr: float,
    week_52_high: float | None = None,
    week_52_low: float | None = None,
) -> tuple[bool, str]:
    """Validate a single ticker's trading signal against price/ATR bounds.

    Returns (is_valid, reason). Checks BOTH long and bearish analysis plans.
    Per CONTEXT.md: entry ±5% of current_price, SL within 3×ATR, TP within 5×ATR.
    Phase 39: entry must be within 52-week high/low range.
    """
    for analysis in [signal.long_analysis, signal.bearish_analysis]:
        plan = analysis.trading_plan
        # Entry within ±5% of current_price
        if current_price > 0 and abs(plan.entry_price - current_price) / current_price > 0.05:
            return False, f"Entry {plan.entry_price:.0f} outside ±5% of current {current_price:.0f}"
        # Entry within 52-week range
        if week_52_high is not None and week_52_low is not None:
            if plan.entry_price > week_52_high or plan.entry_price < week_52_low:
                return False, (
                    f"Entry {plan.entry_price:.0f} outside 52-week range "
                    f"[{week_52_low:.0f}, {week_52_high:.0f}]"
                )
        # SL within 3×ATR of entry
        if atr > 0 and abs(plan.stop_loss - plan.entry_price) > 3 * atr:
            return False, f"SL {plan.stop_loss:.0f} exceeds 3×ATR ({3 * atr:.0f}) from entry {plan.entry_price:.0f}"
        # TP within 5×ATR of entry
        for tp in [plan.take_profit_1, plan.take_profit_2]:
            if atr > 0 and abs(tp - plan.entry_price) > 5 * atr:
                return False, f"TP {tp:.0f} exceeds 5×ATR ({5 * atr:.0f}) from entry {plan.entry_price:.0f}"
    return True, ""
