"""System instruction, few-shot example, and temperature for rumor scoring.

Vietnamese prompts for Gemini rumor credibility/impact assessment.
Follows the same pattern as prompts.py for technical/fundamental/sentiment.
"""

RUMOR_TEMPERATURE = 0.2  # Per D-17: low creativity, high consistency

RUMOR_SCORING_RUBRIC = """Thang điểm đánh giá (áp dụng nhất quán):

Độ tin cậy (credibility_score):
- 1-2: Tin đồn vô căn cứ, tài khoản ẩn danh, không có bằng chứng
- 3-4: Tin đồn mơ hồ, nguồn không rõ ràng, ít tương tác
- 5-6: Thông tin trung tính, có một số cơ sở nhưng chưa xác nhận
- 7-8: Nguồn đáng tin (tài khoản xác thực, nhiều likes/replies), thông tin cụ thể
- 9-10: Nguồn uy tín cao, nhiều người xác nhận, dữ liệu cụ thể rõ ràng

Mức tác động (impact_score):
- 1-2: Ảnh hưởng không đáng kể đến giá cổ phiếu
- 3-4: Ảnh hưởng nhỏ, ngắn hạn
- 5-6: Ảnh hưởng trung bình, có thể tạo biến động ngắn hạn
- 7-8: Ảnh hưởng lớn đến giá cổ phiếu trong tuần
- 9-10: Ảnh hưởng rất lớn, có thể thay đổi xu hướng dài hạn

Sử dụng TOÀN BỘ thang điểm. Điểm 1-2 và 9-10 hợp lệ cho trường hợp cực đoan."""

RUMOR_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia phân tích tin tức và tin đồn thị trường chứng khoán Việt Nam (HOSE). "
    "Cho mỗi mã cổ phiếu, đánh giá TẤT CẢ các nguồn thông tin và cho:\n"
    "- credibility_score (1-10): Độ tin cậy tổng hợp của các thông tin\n"
    "- impact_score (1-10): Mức tác động tiềm tàng đến giá cổ phiếu\n"
    "- direction: bullish (tích cực), bearish (tiêu cực), hoặc neutral (trung tính)\n"
    "- key_claims: Danh sách các tuyên bố/thông tin chính được rút trích (tiếng Việt)\n"
    "- reasoning: Giải thích chi tiết bằng tiếng Việt (5-8 câu) — tại sao cho điểm này\n\n"
    "CÁC NGUỒN THÔNG TIN (theo mức độ tin cậy giảm dần):\n"
    "- VnExpress, Vietstock: Tin tức chính thống từ báo chí uy tín — ĐỘ TIN CẬY CAO (9-10)\n"
    "- CafeF: Tin tức tài chính chuyên ngành — ĐỘ TIN CẬY CAO (9-10)\n"
    "- NhaDauTu (ndt:): Báo Nhà Đầu Tư (Bộ Tài Chính) — ĐỘ TIN CẬY CAO (8-9)\n"
    "- TNCK (tnck:): Tin Nhanh Chứng Khoán — TIN CẬY TRUNG BÌNH-CAO (7-8)\n"
    "- Fireant (cộng đồng): Bài đăng từ nhà đầu tư cá nhân — CẦN XÁC MINH (4-6)\n"
    "- F319 (forum): Thảo luận trên diễn đàn chứng khoán — CẦN XÁC MINH (4-6)\n"
    "- Telegram (tg:): Nhóm chat chứng khoán — CẦN XÁC MINH (3-5)\n\n"
    "QUY TẮC ĐÁNH GIÁ ĐA NGUỒN:\n"
    "- Tin tức chính thống (VnExpress/Vietstock/CafeF/NhaDauTu) đáng tin hơn cộng đồng\n"
    "- Tài khoản xác thực (is_authentic=true) đáng tin hơn tài khoản thường\n"
    "- Bài có nhiều likes và replies cho thấy cộng đồng quan tâm/đồng tình\n"
    "- Nội dung có số liệu cụ thể đáng tin hơn nhận định chung chung\n"
    "- **CROSS-SOURCE CORROBORATION**: Nếu ≥2 nguồn ĐỘC LẬP cùng đề cập thông tin tương tự "
    "→ TĂNG credibility_score thêm 1-2 điểm\n"
    "- **MULTI-DIRECTION CONFLICT**: Nếu nguồn tin cậy cao nói bullish nhưng cộng đồng nói bearish "
    "→ ưu tiên nguồn tin cậy hơn, ghi nhận conflict trong reasoning\n"
    "- Phân tích kỹ thuật/ý kiến chuyên gia (Vietstock) có giá trị phân tích cao\n"
    "- Telegram thường có thông tin sớm nhưng chưa xác minh — xem như tín hiệu sớm, "
    "cần xác nhận từ nguồn khác\n\n"
    + RUMOR_SCORING_RUBRIC
)

RUMOR_FEW_SHOT = """Ví dụ phân tích:

--- VNM (3 bài đăng) ---
1. [Xác thực ✓ | 25 likes | 8 replies] "VNM Q4 doanh thu tăng 15%, biên lợi nhuận cải thiện nhờ giá sữa bột giảm. Mục tiêu 2025 tăng trưởng 10%."
2. [Thường | 3 likes | 0 replies] "VNM sắp chia cổ tức tiền mặt 2000đ/cp, ngày GDKHQ cuối tháng"
3. [Thường | 0 likes | 1 reply] "nghe nói VNM sắp mua lại 1 cty sữa nhỏ"

Kết quả mẫu:
{"ticker": "VNM", "credibility_score": 7, "impact_score": 6, "direction": "bullish", "key_claims": ["Doanh thu Q4 tăng 15%", "Biên lợi nhuận cải thiện nhờ giá sữa bột giảm", "Mục tiêu tăng trưởng 2025 là 10%", "Chia cổ tức 2000đ/cp", "Khả năng M&A công ty sữa nhỏ"], "reasoning": "Bài đăng chính từ tài khoản xác thực với 25 likes có thông tin cụ thể về kết quả kinh doanh Q4 — đáng tin. Thông tin cổ tức phổ biến nhưng chưa xác nhận ngày chính xác. Tin M&A từ nguồn ẩn danh không có bằng chứng nên giảm độ tin cậy tổng. Tổng thể xu hướng tích cực với doanh thu và lợi nhuận cải thiện."}

Phân tích tin đồn cộng đồng cho các mã sau:"""
