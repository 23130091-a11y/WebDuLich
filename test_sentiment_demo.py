"""
Test Sentiment Analysis Demo
File này chứa 300 câu mẫu để test sentiment analysis
Chạy: python test_sentiment_demo.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.ai_engine import analyze_sentiment
import time
from collections import Counter

# ==================== 300 CÂU TEST MẪU ====================

TEST_SENTENCES = [
    # ===== POSITIVE (100 câu) =====
    # Cảnh đẹp, thiên nhiên
    ("Cảnh đẹp tuyệt vời, không khí trong lành", "positive"),
    ("View biển siêu đẹp, hoàng hôn cực kỳ lãng mạn", "positive"),
    ("Thiên nhiên hoang sơ, yên bình, rất thích hợp nghỉ dưỡng", "positive"),
    ("Núi non hùng vĩ, cảnh sắc nên thơ", "positive"),
    ("Bãi biển cát trắng mịn, nước trong xanh", "positive"),
    ("Rừng nguyên sinh đẹp lắm, nhiều cây cổ thụ", "positive"),
    ("Thác nước hùng vĩ, chụp ảnh đẹp lắm", "positive"),
    ("Hang động kỳ vĩ, thạch nhũ lung linh", "positive"),
    ("Ruộng bậc thang mùa lúa chín vàng óng", "positive"),
    ("Đồi chè xanh mướt, không khí mát mẻ", "positive"),
    ("Hồ nước trong vắt như gương, phản chiếu núi rừng", "positive"),
    ("Vịnh biển đẹp nhất mình từng thấy", "positive"),
    ("Đảo hoang sơ, ít người, rất yên tĩnh", "positive"),
    ("Bình minh trên biển đẹp mê hồn", "positive"),
    ("Cánh đồng hoa rực rỡ sắc màu", "positive"),
    
    # Dịch vụ tốt
    ("Nhân viên phục vụ nhiệt tình, chu đáo", "positive"),
    ("Dịch vụ 5 sao, rất hài lòng", "positive"),
    ("Staff thân thiện, hỗ trợ tận tình", "positive"),
    ("Lễ tân niềm nở, check-in nhanh chóng", "positive"),
    ("Hướng dẫn viên am hiểu, giải thích rõ ràng", "positive"),
    ("Phục vụ chuyên nghiệp, đúng giờ", "positive"),
    ("Nhân viên luôn mỉm cười, rất dễ thương", "positive"),
    ("Dịch vụ đưa đón sân bay rất tiện lợi", "positive"),
    ("Concierge hỗ trợ đặt tour rất nhanh", "positive"),
    ("Room service 24/7, rất tiện", "positive"),
    
    # Ẩm thực ngon
    ("Đồ ăn ngon tuyệt, đậm đà hương vị", "positive"),
    ("Hải sản tươi sống, chế biến ngon", "positive"),
    ("Buffet sáng phong phú, đa dạng món", "positive"),
    ("Món ăn địa phương rất đặc sắc", "positive"),
    ("Nhà hàng view đẹp, đồ ăn ngon", "positive"),
    ("Phở ở đây ngon nhất Việt Nam", "positive"),
    ("Bánh mì giòn tan, nhân đầy đặn", "positive"),
    ("Cà phê thơm ngon, view núi tuyệt đẹp", "positive"),
    ("Ẩm thực đường phố phong phú, giá rẻ", "positive"),
    ("Đặc sản vùng miền rất ngon", "positive"),
    
    # Khách sạn/Resort tốt
    ("Phòng rộng rãi, sạch sẽ, tiện nghi đầy đủ", "positive"),
    ("Resort 5 sao đẳng cấp, đáng đồng tiền", "positive"),
    ("Hồ bơi vô cực view biển tuyệt đẹp", "positive"),
    ("Spa thư giãn, massage rất thoải mái", "positive"),
    ("Giường êm, chăn ga sạch thơm", "positive"),
    ("Phòng tắm rộng, bồn tắm lớn", "positive"),
    ("Ban công view biển, ngắm bình minh", "positive"),
    ("Minibar đầy đủ, wifi mạnh", "positive"),
    ("Phòng gym hiện đại, đầy đủ thiết bị", "positive"),
    ("Khu vườn xanh mát, có ghế ngồi thư giãn", "positive"),
    
    # Giá cả hợp lý
    ("Giá cả phải chăng, chất lượng tốt", "positive"),
    ("Rẻ mà ngon, đáng đồng tiền bát gạo", "positive"),
    ("Giá hợp lý so với chất lượng", "positive"),
    ("Khuyến mãi hấp dẫn, tiết kiệm được nhiều", "positive"),
    ("Giá sinh viên rất rẻ", "positive"),
    ("Combo tour giá tốt, bao gồm nhiều dịch vụ", "positive"),
    ("Giá vé vào cổng rẻ, đáng để tham quan", "positive"),
    ("Homestay giá rẻ mà view đẹp", "positive"),
    ("Ăn uống giá bình dân, ngon miệng", "positive"),
    ("Tour trọn gói giá hời", "positive"),
    
    # Trải nghiệm tuyệt vời
    ("Chuyến đi tuyệt vời, đáng nhớ", "positive"),
    ("Trải nghiệm không thể quên", "positive"),
    ("Kỷ niệm đẹp với gia đình", "positive"),
    ("Honeymoon hoàn hảo", "positive"),
    ("Team building vui vẻ, gắn kết", "positive"),
    ("Chuyến du lịch ý nghĩa nhất", "positive"),
    ("Đáng để quay lại lần nữa", "positive"),
    ("Sẽ giới thiệu cho bạn bè", "positive"),
    ("10 điểm không có nhưng", "positive"),
    ("Recommend mọi người nên đến", "positive"),
    
    # Tiện ích tốt
    ("Giao thông thuận tiện, dễ di chuyển", "positive"),
    ("Bãi đỗ xe rộng rãi, miễn phí", "positive"),
    ("Wifi mạnh, ổn định", "positive"),
    ("Điều hòa mát lạnh, yên tĩnh", "positive"),
    ("Có thang máy, tiện cho người già", "positive"),
    ("Gần trung tâm, đi lại dễ dàng", "positive"),
    ("Có xe đưa đón miễn phí", "positive"),
    ("Cho thuê xe máy giá rẻ", "positive"),
    ("Có tour guide tiếng Việt", "positive"),
    ("Thanh toán đa dạng, tiện lợi", "positive"),
    
    # An toàn, an ninh
    ("An ninh tốt, có bảo vệ 24/7", "positive"),
    ("Khu vực an toàn, yên tâm", "positive"),
    ("Có camera giám sát khắp nơi", "positive"),
    ("Nhân viên bảo vệ thân thiện", "positive"),
    ("Két sắt trong phòng, an tâm", "positive"),
    
    # Sạch sẽ
    ("Vệ sinh sạch sẽ, gọn gàng", "positive"),
    ("Toilet công cộng sạch, có giấy", "positive"),
    ("Bãi biển sạch, không rác", "positive"),
    ("Phòng được dọn hàng ngày", "positive"),
    ("Khăn tắm thơm, trắng tinh", "positive"),
    
    # Positive khác
    ("Đi Đà Lạt lần nào cũng thích", "positive"),
    ("Phú Quốc đẹp quá trời", "positive"),
    ("Hội An cổ kính, lãng mạn", "positive"),
    ("Sapa mùa này đẹp lắm", "positive"),
    ("Nha Trang biển xanh cát trắng", "positive"),
    ("Hạ Long kỳ quan thiên nhiên", "positive"),
    ("Mũi Né gió mát, cát vàng", "positive"),
    ("Côn Đảo hoang sơ, yên bình", "positive"),
    ("Quy Nhơn biển đẹp, ít người", "positive"),
    ("Ninh Bình Tràng An tuyệt đẹp", "positive"),
    
    # ===== NEGATIVE (100 câu) =====
    # Dịch vụ tệ
    ("Nhân viên thái độ kém, không nhiệt tình", "negative"),
    ("Phục vụ chậm chạp, phải chờ đợi lâu", "negative"),
    ("Staff không biết tiếng Anh, khó giao tiếp", "negative"),
    ("Lễ tân mặt lạnh, không thân thiện", "negative"),
    ("Hướng dẫn viên nói nhanh, không rõ ràng", "negative"),
    ("Dịch vụ tệ, không đáng tiền", "negative"),
    ("Nhân viên cáu gắt, thiếu chuyên nghiệp", "negative"),
    ("Check-in chờ 2 tiếng, quá lâu", "negative"),
    ("Không ai hỗ trợ khi cần", "negative"),
    ("Thái độ phục vụ quá tệ", "negative"),
    
    # Giá đắt
    ("Giá quá đắt so với chất lượng", "negative"),
    ("Chặt chém du khách, giá cắt cổ", "negative"),
    ("Đắt đỏ mà không xứng đáng", "negative"),
    ("Giá trên trời, chất lượng dưới đất", "negative"),
    ("Bị hét giá, không có giá niêm yết", "negative"),
    ("Phí dịch vụ ẩn, không minh bạch", "negative"),
    ("Giá cao gấp 3 lần bình thường", "negative"),
    ("Mua đồ bị lừa, giá đắt", "negative"),
    ("Taxi chặt chém, không bật đồng hồ", "negative"),
    ("Giá vé vào cổng quá cao", "negative"),
    
    # Đồ ăn dở
    ("Đồ ăn dở tệ, không ngon", "negative"),
    ("Thức ăn nguội lạnh, không tươi", "negative"),
    ("Hải sản không tươi, có mùi", "negative"),
    ("Buffet ít món, không đa dạng", "negative"),
    ("Phục vụ đồ ăn chậm, phải chờ lâu", "negative"),
    ("Món ăn mặn quá, không hợp khẩu vị", "negative"),
    ("Nhà hàng bẩn, ruồi nhặng", "negative"),
    ("Đồ uống pha loãng, không ngon", "negative"),
    ("Ăn xong bị đau bụng", "negative"),
    ("Thức ăn có tóc, mất vệ sinh", "negative"),
    
    # Phòng/Khách sạn tệ
    ("Phòng bẩn, có gián", "negative"),
    ("Giường cũ, nệm xẹp", "negative"),
    ("Phòng tắm bốc mùi hôi", "negative"),
    ("Điều hòa hỏng, nóng không chịu nổi", "negative"),
    ("Wifi yếu, không kết nối được", "negative"),
    ("Phòng nhỏ hẹp, không như hình", "negative"),
    ("Tường ẩm mốc, có nấm", "negative"),
    ("Nước nóng không có", "negative"),
    ("TV hỏng, remote không hoạt động", "negative"),
    ("Cửa sổ không đóng kín, muỗi vào", "negative"),
    
    # Đông đúc, ồn ào
    ("Quá đông, chen chúc không thở nổi", "negative"),
    ("Ồn ào, không thể nghỉ ngơi", "negative"),
    ("Xếp hàng 2 tiếng mới vào được", "negative"),
    ("Đông nghẹt người, không chụp được ảnh", "negative"),
    ("Nhạc mở to, không ngủ được", "negative"),
    ("Phòng bên cạnh ồn ào suốt đêm", "negative"),
    ("Giao thông tắc nghẽn, di chuyển khó", "negative"),
    ("Bãi biển đông, không có chỗ nằm", "negative"),
    ("Nhà hàng đông, phải chờ bàn", "negative"),
    ("Khu du lịch quá tải, mất trật tự", "negative"),
    
    # Bẩn, mất vệ sinh
    ("Bãi biển đầy rác, bẩn thỉu", "negative"),
    ("Toilet công cộng bẩn, hôi", "negative"),
    ("Nước biển ô nhiễm, không tắm được", "negative"),
    ("Đường phố nhiều rác, bụi bặm", "negative"),
    ("Khách sạn không dọn phòng", "negative"),
    ("Bể bơi nước đục, không sạch", "negative"),
    ("Nhà hàng có chuột chạy", "negative"),
    ("Ga trải giường có vết bẩn", "negative"),
    ("Khăn tắm có mùi hôi", "negative"),
    ("Ly cốc không được rửa sạch", "negative"),
    
    # Lừa đảo, không an toàn
    ("Bị móc túi, mất ví", "negative"),
    ("Bị lừa mua hàng giả", "negative"),
    ("Taxi đi đường vòng, chặt chém", "negative"),
    ("Không an toàn, hay có trộm cắp", "negative"),
    ("Bị ép mua đồ, không mua không cho đi", "negative"),
    ("Tour lừa đảo, không như quảng cáo", "negative"),
    ("Đặt phòng online bị hủy khi đến nơi", "negative"),
    ("Bị tính phí ẩn, không báo trước", "negative"),
    ("Hàng fake, không đúng chất lượng", "negative"),
    ("Bị quấy rối, không thoải mái", "negative"),
    
    # Thời tiết xấu, không thuận lợi
    ("Mưa suốt ngày, không đi đâu được", "negative"),
    ("Nắng nóng quá, không chịu nổi", "negative"),
    ("Gió to, sóng lớn, không tắm biển được", "negative"),
    ("Sương mù dày, không thấy gì", "negative"),
    ("Thời tiết xấu, hủy tour", "negative"),
    
    # Thất vọng chung
    ("Thất vọng hoàn toàn, không như mong đợi", "negative"),
    ("Không bao giờ quay lại", "negative"),
    ("Phí tiền, phí thời gian", "negative"),
    ("Không đáng để đi", "negative"),
    ("Hối hận vì đã chọn nơi này", "negative"),
    ("Tệ nhất từ trước đến nay", "negative"),
    ("Không recommend cho ai", "negative"),
    ("Đánh giá 1 sao là còn nhiều", "negative"),
    ("Chuyến đi thảm họa", "negative"),
    ("Mất hứng hoàn toàn", "negative"),
    
    # ===== NEUTRAL (50 câu) =====
    ("Bình thường, không có gì đặc biệt", "neutral"),
    ("Tạm được, không quá tốt không quá tệ", "neutral"),
    ("Ổn, chấp nhận được", "neutral"),
    ("Cũng được, không có gì phàn nàn", "neutral"),
    ("Trung bình, như mọi nơi khác", "neutral"),
    ("Không có gì nổi bật", "neutral"),
    ("Bình thường thôi", "neutral"),
    ("Tàm tạm, không ấn tượng", "neutral"),
    ("OK, không có vấn đề gì", "neutral"),
    ("Chấp nhận được với giá này", "neutral"),
    
    ("Phòng bình thường, đủ dùng", "neutral"),
    ("Đồ ăn tạm được, không ngon không dở", "neutral"),
    ("Dịch vụ bình thường", "neutral"),
    ("Cảnh quan tầm trung", "neutral"),
    ("Giá cả trung bình", "neutral"),
    ("Không có gì để khen hay chê", "neutral"),
    ("Đi một lần cho biết", "neutral"),
    ("Không quá ấn tượng", "neutral"),
    ("Cũng tạm ổn", "neutral"),
    ("Bình bình thôi", "neutral"),
    
    ("Không tệ nhưng cũng không tốt", "neutral"),
    ("Vừa phải, không quá kỳ vọng", "neutral"),
    ("Đạt yêu cầu cơ bản", "neutral"),
    ("Không có gì đáng nhớ", "neutral"),
    ("Trải nghiệm bình thường", "neutral"),
    ("Không có gì để nói", "neutral"),
    ("Tầm trung, không nổi bật", "neutral"),
    ("Cũng được đi", "neutral"),
    ("Không quá xuất sắc", "neutral"),
    ("Bình thường như bao nơi khác", "neutral"),
    
    # ===== MIXED SENTIMENT (50 câu) =====
    ("Cảnh đẹp nhưng đông quá", "mixed"),
    ("Đồ ăn ngon nhưng giá đắt", "mixed"),
    ("Phòng đẹp nhưng dịch vụ tệ", "mixed"),
    ("View tuyệt vời nhưng xa trung tâm", "mixed"),
    ("Nhân viên thân thiện nhưng phục vụ chậm", "mixed"),
    ("Giá rẻ nhưng chất lượng kém", "mixed"),
    ("Biển đẹp nhưng bẩn", "mixed"),
    ("Resort sang nhưng đồ ăn dở", "mixed"),
    ("Vị trí tốt nhưng ồn ào", "mixed"),
    ("Phòng rộng nhưng cũ kỹ", "mixed"),
    
    ("Cảnh quan tuyệt vời, tiếc là thời tiết xấu", "mixed"),
    ("Đẹp thì đẹp nhưng đắt quá", "mixed"),
    ("Ngon nhưng phải chờ lâu", "mixed"),
    ("Tốt nhưng không xứng với giá", "mixed"),
    ("Sạch sẽ nhưng phòng nhỏ", "mixed"),
    ("Yên tĩnh nhưng buồn tẻ", "mixed"),
    ("Gần biển nhưng không có view", "mixed"),
    ("Rẻ nhưng xa trung tâm", "mixed"),
    ("Đông vui nhưng mệt", "mixed"),
    ("Thú vị nhưng nguy hiểm", "mixed"),
    
    ("Có điểm cộng và điểm trừ", "mixed"),
    ("Một số thứ tốt, một số thứ cần cải thiện", "mixed"),
    ("Không hoàn hảo nhưng chấp nhận được", "mixed"),
    ("Có ưu có nhược", "mixed"),
    ("Vừa thích vừa không thích", "mixed"),
    ("Hài lòng một phần", "mixed"),
    ("Có điều hay có điều dở", "mixed"),
    ("Được cái này mất cái kia", "mixed"),
    ("Tùy người, có thể thích hoặc không", "mixed"),
    ("50/50, không biết nên khen hay chê", "mixed"),
    
    # ===== SPECIAL CASES - Negation (20 câu) =====
    ("Không tệ lắm", "positive"),  # Negation of negative = positive
    ("Không dở", "positive"),
    ("Không chê vào đâu được", "positive"),
    ("Không có gì phàn nàn", "positive"),
    ("Không thất vọng", "positive"),
    ("Không hối hận khi đến đây", "positive"),
    ("Không đắt", "positive"),
    ("Không bẩn", "positive"),
    ("Không ồn", "positive"),
    ("Không đông lắm", "positive"),
    
    ("Không đẹp như mong đợi", "negative"),  # Negation of positive = negative
    ("Không ngon", "negative"),
    ("Không sạch", "negative"),
    ("Không thân thiện", "negative"),
    ("Không đáng tiền", "negative"),
    ("Không như quảng cáo", "negative"),
    ("Không recommend", "negative"),
    ("Không quay lại", "negative"),
    ("Không hài lòng", "negative"),
    ("Không xứng đáng", "negative"),
    
    # ===== SPECIAL CASES - Intensifiers (15 câu) =====
    ("Rất đẹp", "positive"),
    ("Cực kỳ ngon", "positive"),
    ("Siêu tuyệt vời", "positive"),
    ("Vô cùng hài lòng", "positive"),
    ("Quá đẹp luôn", "positive"),
    ("Thật sự ấn tượng", "positive"),
    ("Hoàn toàn xuất sắc", "positive"),
    
    ("Rất tệ", "negative"),
    ("Cực kỳ thất vọng", "negative"),
    ("Siêu dở", "negative"),
    ("Vô cùng bực mình", "negative"),
    ("Quá tệ", "negative"),
    ("Thật sự chán", "negative"),
    ("Hoàn toàn thất vọng", "negative"),
    ("Tệ hết sức", "negative"),
    
    # ===== SPECIAL CASES - Sarcasm indicators (15 câu) =====
    ("Tuyệt vời luôn nhỉ, chờ 3 tiếng", "negative"),  # Sarcasm
    ("Đẹp ghê ha, toàn rác", "negative"),
    ("Ngon lắm nhé, ăn xong đau bụng", "negative"),
    ("Rẻ quá đi haha, mất 5 triệu", "negative"),
    ("Dịch vụ tốt thật đấy :))", "negative"),
    ("Sạch sẽ lắm hihi, có gián", "negative"),
    ("Yên tĩnh ghê nhỉ, nhạc mở hết cỡ", "negative"),
    ("Nhanh lắm nhé, chờ 2 tiếng", "negative"),
    ("Thân thiện quá đi, mặt như đưa đám", "negative"),
    ("Đáng tiền lắm á, phí tiền", "negative"),
    ("Tuyệt vời luôn 😅", "negative"),
    ("Quá đẹp luôn á 🙂🙂", "negative"),
    ("Ngon lắm nha 😏", "negative"),
    ("Rẻ ghê haha", "negative"),
    ("Dịch vụ 5 sao nhỉ =))", "negative"),
]


# ==================== CHẠY TEST ====================

def run_sentiment_test():
    """Chạy test sentiment analysis và hiển thị kết quả"""
    
    print("=" * 80)
    print("🔍 SENTIMENT ANALYSIS DEMO - WebDuLich")
    print("=" * 80)
    print(f"📊 Tổng số câu test: {len(TEST_SENTENCES)}")
    print()
    
    # Thống kê
    results = {
        'correct': 0,
        'incorrect': 0,
        'details': []
    }
    
    category_stats = {
        'positive': {'total': 0, 'correct': 0},
        'negative': {'total': 0, 'correct': 0},
        'neutral': {'total': 0, 'correct': 0},
        'mixed': {'total': 0, 'correct': 0}
    }
    
    start_time = time.time()
    
    print("🚀 Bắt đầu phân tích...\n")
    
    for i, (sentence, expected) in enumerate(TEST_SENTENCES):
        # Phân tích sentiment
        score, pos_kw, neg_kw, metadata = analyze_sentiment(sentence, 3)
        
        # Xác định predicted label - điều chỉnh ngưỡng
        if score > 0.18:
            predicted = 'positive'
        elif score < -0.18:
            predicted = 'negative'
        else:
            predicted = 'neutral'
        
        # Xử lý mixed sentiment
        if expected == 'mixed':
            # Mixed được coi là đúng nếu score gần 0 hoặc có cả pos và neg keywords
            is_correct = (abs(score) < 0.4) or (len(pos_kw) > 0 and len(neg_kw) > 0)
        else:
            is_correct = (predicted == expected)
        
        # Cập nhật thống kê
        category_stats[expected]['total'] += 1
        if is_correct:
            results['correct'] += 1
            category_stats[expected]['correct'] += 1
            status = "✅"
        else:
            results['incorrect'] += 1
            status = "❌"
        
        # Lưu chi tiết
        results['details'].append({
            'sentence': sentence,
            'expected': expected,
            'predicted': predicted,
            'score': score,
            'pos_kw': pos_kw,
            'neg_kw': neg_kw,
            'correct': is_correct,
            'method': metadata.get('method', 'unknown')
        })
        
        # Hiển thị progress mỗi 50 câu
        if (i + 1) % 50 == 0:
            print(f"  Đã xử lý: {i + 1}/{len(TEST_SENTENCES)} câu...")
    
    elapsed_time = time.time() - start_time
    
    # ==================== HIỂN THỊ KẾT QUẢ ====================
    print("\n" + "=" * 80)
    print("📈 KẾT QUẢ TỔNG HỢP")
    print("=" * 80)
    
    accuracy = results['correct'] / len(TEST_SENTENCES) * 100
    print(f"\n🎯 Độ chính xác tổng thể: {accuracy:.1f}% ({results['correct']}/{len(TEST_SENTENCES)})")
    print(f"⏱️  Thời gian xử lý: {elapsed_time:.2f} giây")
    print(f"⚡ Tốc độ: {len(TEST_SENTENCES)/elapsed_time:.1f} câu/giây")
    
    print("\n📊 Chi tiết theo loại:")
    print("-" * 50)
    for category, stats in category_stats.items():
        if stats['total'] > 0:
            cat_accuracy = stats['correct'] / stats['total'] * 100
            print(f"  {category.upper():10} : {cat_accuracy:5.1f}% ({stats['correct']}/{stats['total']})")
    
    # Hiển thị một số ví dụ sai
    print("\n" + "=" * 80)
    print("❌ MỘT SỐ CÂU PHÂN TÍCH SAI (tối đa 20 câu)")
    print("=" * 80)
    
    incorrect_samples = [d for d in results['details'] if not d['correct']][:20]
    for i, sample in enumerate(incorrect_samples, 1):
        print(f"\n{i}. \"{sample['sentence']}\"")
        print(f"   Expected: {sample['expected']} | Predicted: {sample['predicted']} | Score: {sample['score']:.2f}")
        print(f"   Pos: {sample['pos_kw'][:3]} | Neg: {sample['neg_kw'][:3]} | Method: {sample['method']}")
    
    # Hiển thị một số ví dụ đúng
    print("\n" + "=" * 80)
    print("✅ MỘT SỐ CÂU PHÂN TÍCH ĐÚNG (mỗi loại 5 câu)")
    print("=" * 80)
    
    for category in ['positive', 'negative', 'neutral', 'mixed']:
        correct_samples = [d for d in results['details'] if d['correct'] and d['expected'] == category][:5]
        if correct_samples:
            print(f"\n📌 {category.upper()}:")
            for sample in correct_samples:
                print(f"   \"{sample['sentence'][:50]}...\" → Score: {sample['score']:.2f}")
    
    return results


def demo_interactive():
    """Demo tương tác - nhập câu để test"""
    print("\n" + "=" * 80)
    print("🎮 DEMO TƯƠNG TÁC - Nhập câu để phân tích sentiment")
    print("=" * 80)
    print("Gõ 'quit' để thoát\n")
    
    while True:
        sentence = input("📝 Nhập câu review: ").strip()
        if sentence.lower() == 'quit':
            print("👋 Tạm biệt!")
            break
        
        if not sentence:
            continue
        
        score, pos_kw, neg_kw, metadata = analyze_sentiment(sentence, 3)
        
        # Xác định label - điều chỉnh ngưỡng
        if score > 0.18:
            label = "😊 TÍCH CỰC"
            color = "\033[92m"  # Green
        elif score < -0.18:
            label = "😞 TIÊU CỰC"
            color = "\033[91m"  # Red
        else:
            label = "😐 TRUNG LẬP"
            color = "\033[93m"  # Yellow
        
        reset = "\033[0m"
        
        print(f"\n{color}📊 Kết quả: {label}{reset}")
        print(f"   Score: {score:.3f}")
        print(f"   Từ khóa tích cực: {pos_kw}")
        print(f"   Từ khóa tiêu cực: {neg_kw}")
        print(f"   Phương pháp: {metadata.get('method', 'unknown')}")
        if 'aspects' in metadata and metadata['aspects']:
            print(f"   Aspects: {metadata['aspects']}")
        print()


if __name__ == "__main__":
    print("\n🌟 SENTIMENT ANALYSIS TEST - WebDuLich 🌟\n")
    print("Chọn chế độ:")
    print("1. Chạy test 300 câu mẫu")
    print("2. Demo tương tác (nhập câu)")
    print("3. Chạy cả hai")
    
    choice = input("\nNhập lựa chọn (1/2/3): ").strip()
    
    if choice == "1":
        run_sentiment_test()
    elif choice == "2":
        demo_interactive()
    elif choice == "3":
        run_sentiment_test()
        demo_interactive()
    else:
        print("Mặc định: Chạy test 300 câu mẫu")
        run_sentiment_test()
