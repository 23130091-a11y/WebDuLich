# Module AI đơn giản cho phân tích và gợi ý
# Sử dụng keyword extraction + negation handling

import re
from collections import Counter

# ==================== TỪ ĐIỂN TỪ KHÓA ====================

# Từ khóa tích cực
POSITIVE_KEYWORDS = [
    'đẹp', 'tuyệt vời', 'tốt', 'ngon', 'sạch sẽ', 'thân thiện', 'chuyên nghiệp',
    'rẻ', 'hợp lý', 'thoải mái', 'yên tĩnh', 'tiện nghi', 'hiện đại', 'sang trọng',
    'view đẹp', 'phong cảnh', 'nên đi', 'recommend', 'khuyên', 'tuyệt', 'xuất sắc',
    'ấn tượng', 'thích', 'hài lòng', 'ok', 'ổn', 'được', 'hay', 'nice', 'good',
    'tuyệt hảo', 'hoàn hảo', 'chu đáo', 'nhiệt tình', 'nhanh', 'sáng sủa',
    'rộng rãi', 'thoáng mát', 'mát mẻ', 'trong lành', 'hùng vĩ', 'thơ mộng'
]

# Từ khóa tiêu cực
NEGATIVE_KEYWORDS = [
    'tệ', 'xấu', 'bẩn', 'dơ', 'đắt', 'chặt chém', 'lừa đảo', 'kém', 'tồi',
    'thất vọng', 'tránh', 'lãng phí', 'kém chất lượng', 'tệ hại', 'ồn ào',
    'chật chội', 'cũ kỹ', 'hư hỏng', 'thái độ xấu', 'bad', 'poor', 'terrible',
    'chán', 'nhàm', 'buồn', 'sợ', 'nguy hiểm', 'mệt', 'nóng', 'lạnh',
    'đông đúc', 'chen chúc', 'chờ lâu', 'muộn', 'trễ', 'hỏng', 'gãy'
]

# Từ phủ định (negation words) - QUAN TRỌNG cho sentiment analysis
NEGATION_WORDS = [
    'không', 'chẳng', 'chả', 'đừng', 'chưa', 'không phải', 'không hề',
    'không bao giờ', 'chẳng bao giờ', 'không còn', 'chẳng còn', 'không thể',
    'chưa bao giờ', 'chưa từng', 'không được', 'chẳng được', 'không có',
    'thiếu', 'mất', 'hết', 'không thấy', 'chẳng thấy'
]

# Từ tăng cường (intensifiers)
INTENSIFIERS = {
    'rất': 1.5,
    'cực kỳ': 2.0,
    'vô cùng': 2.0,
    'quá': 1.5,
    'siêu': 1.8,
    'hơi': 0.5,
    'khá': 0.8,
    'tương đối': 0.7,
    'cũng': 0.6,
    'thật sự': 1.5,
    'thực sự': 1.5,
    'hoàn toàn': 1.8,
    'tuyệt đối': 2.0
}

# Stopwords tiếng Việt
STOPWORDS = [
    'là', 'của', 'và', 'có', 'được', 'trong', 'với', 'cho', 'từ', 'này', 'đó',
    'một', 'các', 'những', 'để', 'khi', 'đã', 'sẽ', 'bị', 'nếu', 'như', 'thì',
    'mà', 'hay', 'hoặc', 'nhưng', 'vì', 'nên', 'lại', 'còn', 'đang'
]


# ==================== HÀM XỬ LÝ VĂN BẢN ====================

def preprocess_text(text):
    """Tiền xử lý văn bản: chuyển thường, loại bỏ ký tự đặc biệt"""
    if not text:
        return ""
    text = text.lower()
    # Giữ lại chữ cái tiếng Việt, số và khoảng trắng
    text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def split_sentences(text):
    """Tách văn bản thành các câu"""
    # Tách theo dấu chấm, chấm hỏi, chấm than, dấu phẩy (cho câu ngắn)
    sentences = re.split(r'[.!?;,]', text)
    return [s.strip() for s in sentences if s.strip()]


def check_negation(sentence, keyword, window_size=3):
    """
    Kiểm tra xem từ khóa có bị phủ định không
    
    Thuật toán:
    1. Tìm vị trí của keyword trong câu
    2. Kiểm tra window_size từ phía trước keyword
    3. Nếu có từ phủ định trong window -> keyword bị phủ định
    
    VD: "không đẹp" -> "đẹp" bị phủ định
        "cảnh đẹp" -> "đẹp" không bị phủ định
    """
    words = sentence.lower().split()
    
    # Tìm vị trí keyword (có thể là cụm từ)
    keyword_lower = keyword.lower()
    sentence_lower = sentence.lower()
    
    if keyword_lower not in sentence_lower:
        return False
    
    # Tìm index của keyword trong danh sách từ
    keyword_start_idx = -1
    for i, word in enumerate(words):
        # Kiểm tra từ đơn hoặc bắt đầu của cụm từ
        remaining = ' '.join(words[i:])
        if remaining.startswith(keyword_lower):
            keyword_start_idx = i
            break
    
    if keyword_start_idx == -1:
        return False
    
    # Kiểm tra window phía trước
    start_idx = max(0, keyword_start_idx - window_size)
    window_words = words[start_idx:keyword_start_idx]
    window_text = ' '.join(window_words)
    
    # Kiểm tra từ phủ định trong window
    for neg_word in NEGATION_WORDS:
        if neg_word in window_text:
            return True
    
    return False


def get_intensifier_score(sentence, keyword):
    """
    Lấy hệ số tăng cường cho keyword
    
    VD: "rất đẹp" -> hệ số 1.5
        "cực kỳ tốt" -> hệ số 2.0
    """
    words = sentence.lower().split()
    keyword_lower = keyword.lower()
    
    # Tìm vị trí keyword
    keyword_idx = -1
    for i, word in enumerate(words):
        if keyword_lower in ' '.join(words[i:i+3]):  # Cho phép cụm từ
            keyword_idx = i
            break
    
    if keyword_idx == -1:
        return 1.0
    
    # Kiểm tra 2 từ phía trước
    for i in range(max(0, keyword_idx - 2), keyword_idx):
        word = words[i]
        for intensifier, score in INTENSIFIERS.items():
            if intensifier in word or word in intensifier:
                return score
    
    return 1.0


def extract_keywords_with_context(text, keyword_list, is_positive=True):
    """
    Trích xuất từ khóa với xử lý ngữ cảnh (phủ định + tăng cường)
    
    Returns:
        - found_keywords: danh sách từ khóa tìm thấy
        - negated_keywords: danh sách từ khóa bị phủ định
        - total_score: điểm tổng (có tính hệ số)
    """
    text = preprocess_text(text)
    sentences = split_sentences(text)
    
    found_keywords = []
    negated_keywords = []
    total_score = 0.0
    
    for keyword in keyword_list:
        keyword_lower = keyword.lower()
        
        if keyword_lower not in text:
            continue
        
        # Kiểm tra trong từng câu
        for sentence in sentences:
            if keyword_lower not in sentence.lower():
                continue
            
            # Kiểm tra phủ định
            is_negated = check_negation(sentence, keyword)
            
            # Lấy hệ số tăng cường
            intensifier = get_intensifier_score(sentence, keyword)
            
            if is_negated:
                negated_keywords.append(keyword)
                # Từ tích cực bị phủ định -> tiêu cực (và ngược lại)
                if is_positive:
                    total_score -= 1.0 * intensifier
                else:
                    total_score += 1.0 * intensifier
            else:
                found_keywords.append(keyword)
                if is_positive:
                    total_score += 1.0 * intensifier
                else:
                    total_score -= 1.0 * intensifier
            
            break  # Chỉ tính 1 lần cho mỗi keyword
    
    return found_keywords, negated_keywords, total_score


def analyze_sentiment(text):
    """
    Phân tích cảm xúc nâng cao với xử lý phủ định (negation handling)
    
    Thuật toán:
    1. Tách văn bản thành các câu
    2. Với mỗi từ khóa, kiểm tra ngữ cảnh:
       - Có bị phủ định không? (không, chẳng, chưa...)
       - Có từ tăng cường không? (rất, cực kỳ, hơi...)
    3. Tính điểm sentiment dựa trên:
       - Từ tích cực: +1 (hoặc -1 nếu bị phủ định)
       - Từ tiêu cực: -1 (hoặc +1 nếu bị phủ định)
       - Nhân với hệ số tăng cường
    
    Returns:
        - sentiment_score: điểm từ -1 (tiêu cực) đến 1 (tích cực)
        - positive_keywords: từ khóa tích cực tìm thấy
        - negative_keywords: từ khóa tiêu cực tìm thấy
    
    Ví dụ:
        "Cảnh đẹp, dịch vụ tốt" -> score > 0
        "Cảnh không đẹp, dịch vụ tệ" -> score < 0
        "Không tệ, khá ổn" -> score > 0 (phủ định của tiêu cực = tích cực)
    """
    if not text:
        return 0.0, [], []
    
    # Phân tích từ khóa tích cực
    pos_found, pos_negated, pos_score = extract_keywords_with_context(
        text, POSITIVE_KEYWORDS, is_positive=True
    )
    
    # Phân tích từ khóa tiêu cực
    neg_found, neg_negated, neg_score = extract_keywords_with_context(
        text, NEGATIVE_KEYWORDS, is_positive=False
    )
    
    # Tổng điểm
    total_score = pos_score + neg_score
    
    # Chuẩn hóa về [-1, 1]
    # Sử dụng tanh để giới hạn giá trị
    import math
    if total_score != 0:
        sentiment_score = math.tanh(total_score / 3)  # Chia 3 để làm mềm
    else:
        sentiment_score = 0.0
    
    # Gộp từ khóa
    # Từ tích cực = tìm thấy + tiêu cực bị phủ định
    all_positive = pos_found + neg_negated
    # Từ tiêu cực = tìm thấy + tích cực bị phủ định
    all_negative = neg_found + pos_negated
    
    return sentiment_score, list(set(all_positive)), list(set(all_negative))


def calculate_destination_score(destination):
    """
    Tính điểm gợi ý cho một địa điểm
    Dựa trên: đánh giá, sentiment, số lượng review
    """
    from .models import Review, RecommendationScore
    
    reviews = Review.objects.filter(destination=destination)
    total_reviews = reviews.count()
    
    if total_reviews == 0:
        # Không có đánh giá -> điểm mặc định
        score_data = {
            'overall_score': 50.0,
            'review_score': 0.0,
            'sentiment_score': 0.0,
            'popularity_score': 0.0,
            'total_reviews': 0,
            'avg_rating': 0.0,
            'positive_review_ratio': 0.0
        }
    else:
        # Tính điểm từ rating (0-100)
        avg_rating = sum(r.rating for r in reviews) / total_reviews
        review_score = (avg_rating / 5.0) * 100
        
        # Tính điểm sentiment (0-100)
        avg_sentiment = sum(r.sentiment_score for r in reviews) / total_reviews
        sentiment_score = ((avg_sentiment + 1) / 2) * 100  # Chuyển từ [-1,1] sang [0,100]
        
        # Tính điểm phổ biến (dựa trên số lượng review)
        # Sử dụng log scale để tránh bias quá nhiều
        import math
        popularity_score = min(100, math.log(total_reviews + 1) * 20)
        
        # Tỷ lệ review tích cực (sentiment > 0)
        positive_reviews = sum(1 for r in reviews if r.sentiment_score > 0)
        positive_ratio = positive_reviews / total_reviews
        
        # Điểm tổng thể (weighted average)
        overall_score = (
            review_score * 0.5 +      # 50% từ rating
            sentiment_score * 0.3 +   # 30% từ sentiment
            popularity_score * 0.2    # 20% từ popularity
        )
        
        score_data = {
            'overall_score': round(overall_score, 2),
            'review_score': round(review_score, 2),
            'sentiment_score': round(sentiment_score, 2),
            'popularity_score': round(popularity_score, 2),
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 2),
            'positive_review_ratio': round(positive_ratio, 2)
        }
    
    # Lưu hoặc cập nhật điểm
    rec_score, created = RecommendationScore.objects.update_or_create(
        destination=destination,
        defaults=score_data
    )
    
    return rec_score


def recalculate_all_scores():
    """
    Tính toán lại điểm cho tất cả địa điểm
    Chạy script này vào ban đêm hoặc khi có dữ liệu mới
    """
    from .models import Destination
    
    destinations = Destination.objects.all()
    results = []
    
    for dest in destinations:
        score = calculate_destination_score(dest)
        results.append({
            'destination': dest.name,
            'score': score.overall_score
        })
    
    return results


def search_destinations(query, filters=None):
    """
    Tìm kiếm địa điểm thông minh với AI
    - query: từ khóa tìm kiếm
    - filters: dict chứa các bộ lọc (location, travel_type, price_range, etc.)
    - Ưu tiên địa điểm nổi tiếng (điểm cao, nhiều review)
    """
    from django.db.models import Q, F, Case, When, IntegerField
    from .models import Destination, RecommendationScore
    from .utils_helpers import normalize_search_text
    
    # Bắt đầu với tất cả địa điểm
    destinations = Destination.objects.all()
    
    # Tìm kiếm theo query
    if query and query.strip():
        query = query.strip()
        query_normalized = normalize_search_text(query)
        
        # Tìm kiếm chính xác trước
        exact_match = destinations.filter(
            Q(name__iexact=query) | Q(location__iexact=query)
        )
        
        # Tìm kiếm gần đúng
        partial_match = destinations.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query) |
            Q(travel_type__icontains=query)
        )
        
        # Tìm kiếm không dấu (fallback)
        if not partial_match.exists():
            # Tìm kiếm thủ công với normalize
            matching_ids = []
            for dest in Destination.objects.all():
                name_norm = normalize_search_text(dest.name)
                location_norm = normalize_search_text(dest.location)
                desc_norm = normalize_search_text(dest.description)
                
                if (query_normalized in name_norm or 
                    query_normalized in location_norm or 
                    query_normalized in desc_norm):
                    matching_ids.append(dest.id)
            
            destinations = Destination.objects.filter(id__in=matching_ids)
        else:
            # Kết hợp exact và partial
            all_ids = list(exact_match.values_list('id', flat=True)) + \
                     list(partial_match.values_list('id', flat=True))
            destinations = Destination.objects.filter(id__in=all_ids)
    
    # Áp dụng filters
    if filters:
        if filters.get('location'):
            destinations = destinations.filter(location__icontains=filters['location'])
        
        if filters.get('travel_type'):
            destinations = destinations.filter(travel_type=filters['travel_type'])
        
        if filters.get('max_price'):
            destinations = destinations.filter(
                Q(avg_price__lte=filters['max_price']) | Q(avg_price__isnull=True)
            )
        
        if filters.get('min_rating'):
            # Lọc theo rating tối thiểu
            dest_ids = RecommendationScore.objects.filter(
                avg_rating__gte=filters['min_rating']
            ).values_list('destination_id', flat=True)
            destinations = destinations.filter(id__in=dest_ids)
    
    # Sắp xếp thông minh: Ưu tiên địa điểm nổi tiếng
    try:
        destinations = destinations.select_related('recommendation').annotate(
            # Tính điểm ưu tiên
            priority_score=Case(
                # Địa điểm có điểm > 80: ưu tiên cao nhất
                When(recommendation__overall_score__gte=80, then=3),
                # Địa điểm có điểm 70-80: ưu tiên cao
                When(recommendation__overall_score__gte=70, then=2),
                # Địa điểm có điểm < 70: ưu tiên thấp
                default=1,
                output_field=IntegerField()
            )
        ).order_by(
            '-priority_score',  # Ưu tiên theo nhóm điểm
            '-recommendation__overall_score',  # Điểm tổng thể
            '-recommendation__total_reviews',  # Số lượng review
            '-recommendation__avg_rating'  # Rating trung bình
        )
    except:
        # Nếu không có recommendation, sắp xếp theo tên
        destinations = destinations.order_by('name')
    
    return destinations
