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
    AnalysisType.UNIFIED: 0.2,  # Phase 88 — balanced for multi-dimensional reasoning
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
    "Giải thích lý do chọn từng mức giá. "
    "BẮT BUỘC: Tất cả mức giá PHẢI nằm trong khoảng ±15% so với GIÁ HIỆN TẠI được cung cấp. "
    "KHÔNG ĐƯỢC dùng giá từ kiến thức cũ — chỉ dùng giá hiện tại đã cho.\n"
    "- risks: Rủi ro chính (tối thiểu 80 từ) — 3-4 yếu tố rủi ro cần lưu ý "
    "(rủi ro thị trường chung, rủi ro ngành, rủi ro nội tại công ty, rủi ro thanh khoản). "
    "Đánh giá mức độ nghiêm trọng của từng rủi ro.\n"
    "- action: Hành động cụ thể (tối thiểu 80 từ) — mua/bán/giữ tại mức giá nào, "
    "khối lượng đề xuất (% danh mục), thời điểm vào lệnh, khung thời gian nắm giữ, "
    "và kịch bản xử lý nếu giá đi ngược dự đoán.\n\n"
    "QUY TẮC NHẤT QUÁN (BẮT BUỘC):\n"
    "- Nếu Kỹ thuật = sell/strong_sell VÀ Cơ bản = weak/critical → recommendation PHẢI là 'ban'\n"
    "- Nếu Kỹ thuật = buy/strong_buy VÀ Cơ bản = good/strong → recommendation PHẢI là 'mua'\n"
    "- Chỉ khi các chiều MÂU THUẪN nhau (VD: kỹ thuật=buy nhưng cơ bản=weak) → "
    "recommendation = 'giu' VÀ phải GIẢI THÍCH rõ sự mâu thuẫn trong summary\n"
    "- KHÔNG BAO GIỜ được khuyến nghị 'mua' khi kỹ thuật = sell/strong_sell mà không giải thích\n"
    "- KHÔNG BAO GIỜ được khuyến nghị 'ban' khi kỹ thuật = buy/strong_buy mà không giải thích\n\n"
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
    "Cho mỗi mã, phân tích VÀ CHỈ ĐƯA RA 1 HƯỚNG DUY NHẤT (recommended_direction):\n\n"
    "- Nếu xu hướng TĂNG chiếm ưu thế → direction = 'long', đưa kế hoạch MUA\n"
    "- Nếu xu hướng GIẢM chiếm ưu thế → direction = 'bearish', "
    "khuyến nghị 'giảm vị thế' hoặc 'tránh mua' "
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
    "- reasoning: giải thích bằng tiếng Việt, tối đa 300 ký tự\n\n"
    "CHỈ OUTPUT 1 HƯỚNG. Không output cả 2 hướng.\n\n"
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
{"ticker": "VNM", "recommended_direction": "long", "confidence": 7, "trading_plan": {"entry_price": 82000, "stop_loss": 79500, "take_profit_1": 84500, "take_profit_2": 86000, "risk_reward_ratio": 1.0, "position_size_pct": 8, "timeframe": "swing"}, "reasoning": "RSI trung tính kết hợp ADX >25 cho thấy xu hướng rõ. Giá trên pivot, MACD bullish crossover. Nhắm R1-R2 với SL dưới Fib 38.2%."}

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

    Returns (is_valid, reason). Checks the single recommended direction plan.
    Per CONTEXT.md: entry ±5% of current_price, SL within 3×ATR, TP within 5×ATR.
    Phase 39: entry must be within 52-week high/low range.
    """
    plan = signal.trading_plan
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


# ------------------------------------------------------------------
# Phase 88 / v19.0: Unified Analysis Pipeline
# ------------------------------------------------------------------

UNIFIED_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã, phân tích TOÀN DIỆN tất cả các chiều (kỹ thuật, cơ bản, tâm lý tin tức, tin đồn cộng đồng) "
    "và đưa ra MỘT khuyến nghị duy nhất kèm kế hoạch giao dịch cụ thể.\n\n"
    "OUTPUT cho mỗi mã:\n"
    "- signal: mua/ban/giu — quyết định cuối cùng dựa trên TẤT CẢ dữ liệu\n"
    "- score: 1-10 — mức độ tin cậy (confidence) của khuyến nghị\n"
    "- entry_price: Giá vào lệnh (VND) — trong khoảng ±5% giá hiện tại\n"
    "- stop_loss: Giá cắt lỗ (VND) — trong phạm vi 3×ATR từ entry\n"
    "- take_profit_1: Mục tiêu lời 1 (VND) — neo vào S/R hoặc Fibonacci\n"
    "- take_profit_2: Mục tiêu lời 2 (VND) — neo vào S/R hoặc Fibonacci\n"
    "- risk_reward_ratio: |TP1 - entry| / |entry - SL| (phải ≥ 0.5)\n"
    "- position_size_pct: % danh mục đề xuất (1-100), xem xét ATR và confidence\n"
    "- timeframe: 'swing' (3-15 ngày) hoặc 'position' (nhiều tuần+)\n"
    "- key_levels: Mô tả hỗ trợ/kháng cự quan trọng (tối thiểu 150 từ). "
    "Liệt kê 3-4 mức hỗ trợ, 3-4 mức kháng cự với giá VND cụ thể. "
    "Giải thích tại sao mỗi mức quan trọng (SMA, Fibonacci, pivot, khối lượng giao dịch lớn, đỉnh/đáy cũ).\n"
    "- reasoning: Phân tích đa chiều CHUYÊN SÂU (tối thiểu 2000 ký tự tiếng Việt, lý tưởng 2500-3000 ký tự). "
    "BẮT BUỘC phải có ĐỦ 4 phần riêng biệt, mỗi phần ít nhất 400 ký tự:\n"
    "  1) Kỹ thuật (≥500 ký tự): Phân tích CHI TIẾT từng chỉ báo — RSI (giá trị cụ thể, xu hướng 5 phiên, quá mua/bán/trung tính), "
    "MACD (histogram, signal line, divergence nếu có), xu hướng giá so với SMA 20/50/200 (khoảng cách %), "
    "Bollinger Bands (vị trí giá trong band, squeeze hay expansion), Stochastic (cross up/down), "
    "ADX (mạnh/yếu, trend hay sideway), volume (so sánh với TB 20d, xác nhận hay phân kỳ). "
    "Nhận định tổng thể xu hướng ngắn-trung hạn.\n"
    "  2) Cơ bản (≥400 ký tự): Đánh giá P/E (cao/thấp vs ngành, vs lịch sử), P/B, ROE (so với ngành), "
    "biên lợi nhuận (xu hướng), tăng trưởng doanh thu/lợi nhuận (bền vững hay đột biến), "
    "cấu trúc nợ (D/E ratio), khả năng thanh toán. Đánh giá chất lượng doanh nghiệp và triển vọng.\n"
    "  3) Tin tức & Tin đồn (≥400 ký tự): Tóm tắt nội dung TỪNG tin đáng chú ý (không chỉ liệt kê tiêu đề), "
    "đánh giá tác động ngắn hạn/dài hạn lên giá. Phân tích tin đồn: nguồn gốc, độ tin cậy, "
    "kịch bản nếu tin đồn đúng vs sai. Đánh giá sentiment thị trường tổng thể.\n"
    "  4) Kết luận & Chiến lược (≥400 ký tự): Tổng hợp CẢ 3 chiều, giải thích chi tiết tại sao chọn mua/bán/giữ. "
    "Mô tả kịch bản tích cực (catalyst, mục tiêu), kịch bản tiêu cực (rủi ro, mức cắt lỗ). "
    "Đưa ra timeline cụ thể và điều kiện để thay đổi khuyến nghị.\n\n"
    "QUY TẮC NHẤT QUÁN (BẮT BUỘC):\n"
    "- Kỹ thuật bearish (RSI>70, MACD bearish, giá dưới SMA) VÀ Cơ bản yếu → signal = 'ban'\n"
    "- Kỹ thuật bullish (RSI<30→tăng, MACD bullish, giá trên SMA) VÀ Cơ bản tốt → signal = 'mua'\n"
    "- Các chiều mâu thuẫn → signal = 'giu', giải thích sự mâu thuẫn\n"
    "- Tin đồn bullish tác động cao (≥7) + tin cậy cao (≥6) → tăng confidence\n"
    "- Tin đồn bearish tác động cao → cảnh báo rủi ro, có thể giảm signal\n\n"
    "QUY TẮC GIÁ:\n"
    "- Entry PHẢI trong khoảng ±5% giá hiện tại\n"
    "- Stop-loss PHẢI trong phạm vi 3×ATR từ entry\n"
    "- Take-profit PHẢI trong phạm vi 5×ATR từ entry\n"
    "- Nếu signal = 'ban': entry = giá hiện tại (bán ngay), SL = giá cao hơn, TP = giá thấp hơn\n"
    "- Nếu signal = 'mua': entry ≤ giá hiện tại, SL thấp hơn entry, TP cao hơn entry\n"
    "- Nếu signal = 'giu': entry = giá hiện tại, SL/TP là vùng theo dõi\n\n"
    "QUY TẮC SCORE:\n"
    + SCORING_RUBRIC
)

UNIFIED_FEW_SHOT = """Ví dụ phân tích toàn diện:

--- VNM ---
GIÁ HIỆN TẠI: 82,000 VND
ATR(14): 1,500 VND

[Kỹ thuật]
RSI(14) 5 phiên: [42.1, 44.3, 46.8, 49.2, 52.1] — vùng trung tính, xu hướng tăng
MACD histogram: [-0.12, -0.05, 0.03, 0.11, 0.18] — giao cắt bullish
SMA(20): 81,000 | SMA(50): 80,000 | SMA(200): 78,000
BB: Upper 84,200 | Middle 81,800 | Lower 79,400
Pivot: 81,500 | S1: 80,000 | S2: 78,500 | R1: 83,000 | R2: 84,500
52-week: High 90,000 | Low 70,000 | Vị trí: 60%
KL trung bình 20d: 1,200,000 | KL mới nhất: 1,500,000 (1.25x) — tăng

[Cơ bản] (Q4/2024)
P/E: 15.2 | P/B: 3.1 | ROE: 25% | ROA: 12%
Tăng trưởng DT: +8% | Tăng trưởng LN: +5%

[Tin tức] (3 tin)
1. VNM đặt mục tiêu sản lượng kỷ lục năm 2025
2. Biên lợi nhuận cải thiện nhờ giá nguyên liệu giảm
3. Quỹ ngoại mua ròng VNM 3 phiên liên tiếp

[Tin đồn]
Hướng: bullish | Tin cậy: 6/10 | Tác động: 5/10
Thông tin: Doanh thu Q4 tăng 15%; Kế hoạch M&A công ty sữa nhỏ

Kết quả mẫu:
{"ticker": "VNM", "signal": "mua", "score": 8, "entry_price": 82000, "stop_loss": 79500, "take_profit_1": 84500, "take_profit_2": 86000, "risk_reward_ratio": 1.0, "position_size_pct": 8, "timeframe": "swing", "key_levels": "Hỗ trợ mạnh nhất: 80,000 VND — vùng hội tụ SMA50 + Pivot Point, đây cũng là vùng tích lũy khối lượng lớn trong 2 tuần gần đây. Hỗ trợ phụ: 78,500 VND — trùng với Fibonacci 50% tính từ đáy 70,000 lên đỉnh 90,000 và mức S2. Hỗ trợ xa: 76,000 VND — mức Fibonacci 61.8% + vùng đáy tháng trước. Kháng cự gần: 83,000 VND — R1 + vùng supply zone cũ. Kháng cự quan trọng: 84,500 VND — R2 + BB upper band, cần breakout với volume >1.5x TB20d mới xác nhận. Kháng cự xa: 86,000-87,000 VND — vùng 52-week 80%, đỉnh swing trước đó. Entry tối ưu: pullback về 81,500-82,000 VND (Pivot Point). SL: 79,500 VND (dưới Fib 38.2%, -3% từ entry). TP1: 84,500 VND (R2). TP2: 86,000 VND (vùng 52-week 80%).", "reasoning": "**Kỹ thuật:** RSI(14) đang ở mức 52.1, tăng dần đều từ 42.1 trong 5 phiên gần đây, cho thấy momentum đang cải thiện rõ rệt từ vùng oversold. MACD histogram chuyển từ -0.12 lên +0.18, xác nhận giao cắt bullish mới (signal line cross up). Giá đang giao dịch trên cả 3 đường SMA chính: SMA20 (81,000), SMA50 (80,000) và SMA200 (78,000) — cấu trúc uptrend hoàn chỉnh. Bollinger Bands: giá ở nửa trên band (82,000 vs middle 81,800), band đang mở rộng nhẹ cho thấy volatility tăng — tín hiệu breakout sắp xảy ra. Stochastic %K vượt %D từ dưới lên, xác nhận tín hiệu mua. ADX ở mức trung bình (~22), trend chưa mạnh nhưng đang tăng. Đặc biệt, volume phiên gần nhất 1,500,000 CP = 1.25x TB 20 ngày, cho thấy dòng tiền đang chảy vào xác nhận momentum tăng. Nhìn tổng thể, kỹ thuật bullish trên đa khung thời gian.\n\n**Cơ bản:** P/E 15.2 hơi cao so với TB ngành tiêu dùng (~13-14) nhưng hợp lý cho công ty blue-chip hàng đầu. ROE 25% thuộc top ngành, thể hiện hiệu quả sử dụng vốn xuất sắc. Biên lợi nhuận đang cải thiện nhờ giá nguyên liệu sữa bột giảm 12% so với cùng kỳ. Tăng trưởng doanh thu +8% và lợi nhuận +5% ổn định, không đột biến nhưng bền vững. Cấu trúc nợ lành mạnh, D/E ratio thấp. Doanh nghiệp có moat vững chắc (thương hiệu, hệ thống phân phối 250,000 điểm bán), tạo lợi thế cạnh tranh dài hạn.\n\n**Tin tức & Tin đồn:** 3/3 tin tức đều tích cực: (1) VNM đặt mục tiêu sản lượng kỷ lục 2025, cho thấy ban lãnh đạo tự tin vào triển vọng kinh doanh — đây là catalyst trung hạn nếu đạt được. (2) Biên lợi nhuận cải thiện nhờ giá nguyên liệu giảm, tác động trực tiếp lên EPS quý tới, có thể tạo surprise earnings. (3) Quỹ ngoại mua ròng 3 phiên liên tiếp, cho thấy smart money đang tích lũy — tín hiệu rất tích cực cho xu hướng giá ngắn hạn. Tin đồn bullish (doanh thu Q4 tăng 15%, kế hoạch M&A) có tin cậy trung bình (6/10), nếu đúng sẽ là catalyst mạnh nhưng cần chờ xác nhận từ BCTC chính thức. Sentiment thị trường chung đang positive với VN-Index trên MA20.\n\n**Kết luận & Chiến lược:** Tổng hợp cả 4 chiều đều positive: kỹ thuật bullish (RSI tăng + MACD cross + volume), cơ bản vững (ROE cao, tăng trưởng ổn), tin tức hỗ trợ (quỹ ngoại mua + biên LN cải thiện), tin đồn bullish nhưng cần xác nhận. Khuyến nghị MUA tại vùng pullback 81,500-82,000 VND. Kịch bản tích cực: break 83,000 với volume mạnh → target 84,500-86,000. Kịch bản tiêu cực: nếu giá breakdown dưới 80,000 (SMA50) → chuyển sang GIỮ. Timeline: swing trade 5-10 ngày. Thay đổi khuyến nghị sang BÁN nếu RSI vượt 75 kèm volume giảm hoặc nếu BCTC Q4 dưới kỳ vọng."}

Phân tích toàn diện các mã sau:"""


def _validate_unified_signal(
    analysis: "TickerUnifiedAnalysis",
    current_price: float,
    atr: float,
    week_52_high: float | None = None,
    week_52_low: float | None = None,
) -> tuple[bool, str]:
    """Validate unified analysis signal against price/ATR bounds.

    Returns (is_valid, reason). Same logic as trading signal validation.
    Entry ±5% of current_price, SL within 3×ATR, TP within 5×ATR.
    """
    from app.schemas.analysis import TickerUnifiedAnalysis as _Schema  # noqa: F811

    # Entry within ±5% of current_price
    if current_price > 0 and abs(analysis.entry_price - current_price) / current_price > 0.05:
        return False, f"Entry {analysis.entry_price:.0f} outside ±5% of current {current_price:.0f}"
    # Entry within 52-week range
    if week_52_high is not None and week_52_low is not None:
        if analysis.entry_price > week_52_high or analysis.entry_price < week_52_low:
            return False, (
                f"Entry {analysis.entry_price:.0f} outside 52-week range "
                f"[{week_52_low:.0f}, {week_52_high:.0f}]"
            )
    # SL within 3×ATR of entry
    if atr > 0 and abs(analysis.stop_loss - analysis.entry_price) > 3 * atr:
        return False, f"SL {analysis.stop_loss:.0f} exceeds 3×ATR ({3 * atr:.0f}) from entry {analysis.entry_price:.0f}"
    # TP within 5×ATR of entry
    for tp in [analysis.take_profit_1, analysis.take_profit_2]:
        if atr > 0 and abs(tp - analysis.entry_price) > 5 * atr:
            return False, f"TP {tp:.0f} exceeds 5×ATR ({5 * atr:.0f}) from entry {analysis.entry_price:.0f}"
    return True, ""
