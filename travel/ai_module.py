# Module AI đơn giản cho phân tích và gợi ý
# Sử dụng keyword extraction thay vì NLP phức tạp (tiết kiệm tài nguyên)

import re
from collections import Counter

# Từ điển từ khóa tiếng Việt (có thể mở rộng)
POSITIVE_KEYWORDS = [
    'đẹp', 'tuyệt vời', 'tốt', 'ngon', 'sạch sẽ', 'thân thiện', 'chuyên nghiệp',
    'rẻ', 'hợp lý', 'thoải mái', 'yên tĩnh', 'tiện nghi', 'hiện đại', 'sang trọng',
    'view đẹp', 'phong cảnh', 'nên đi', 'recommend', 'khuyên', 'tuyệt', 'xuất sắc',
    'ấn tượng', 'thích', 'hài lòng', 'ok', 'ổn', 'được', 'hay', 'nice', 'good'
]

NEGATIVE_KEYWORDS = [
    'tệ', 'xấu', 'bẩn', 'dơ', 'đắt', 'chặt chém', 'lừa đảo', 'kém', 'tồi',
    'không tốt', 'thất vọng', 'không nên', 'tránh', 'không đáng', 'lãng phí',
    'kém chất lượng', 'tệ hại', 'không sạch', 'ồn ào', 'chật chội', 'cũ kỹ',
    'hư hỏng', 'không chuyên nghiệp', 'thái độ', 'bad', 'poor'
]

# Stopwords tiếng Việt (từ phổ biến không mang ý nghĩa)
STOPWORDS = [
    'là', 'của', 'và', 'có', 'được', 'trong', 'với', 'cho', 'từ', 'này', 'đó',
    'một', 'các', 'những', 'để', 'khi', 'đã', 'sẽ', 'bị', 'nếu', 'như', 'thì',
    'mà', 'hay', 'hoặc', 'nhưng', 'vì', 'nên', 'rất', 'lại', 'còn', 'đang'
]


def preprocess_text(text):
    """Tiền xử lý văn bản: chuyển thường, loại bỏ ký tự đặc biệt"""
    if not text:
        return ""
    text = text.lower()
    # Giữ lại chữ cái tiếng Việt, số và khoảng trắng
    text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_keywords(text, keyword_list):
    """Trích xuất từ khóa từ văn bản"""
    text = preprocess_text(text)
    found_keywords = []
    
    for keyword in keyword_list:
        if keyword in text:
            found_keywords.append(keyword)
    
    return found_keywords


def analyze_sentiment(text):
    """
    Phân tích cảm xúc đơn giản dựa trên từ khóa
    Trả về: (sentiment_score, positive_keywords, negative_keywords)
    sentiment_score: -1 (tiêu cực) đến 1 (tích cực)
    """
    positive_found = extract_keywords(text, POSITIVE_KEYWORDS)
    negative_found = extract_keywords(text, NEGATIVE_KEYWORDS)
    
    pos_count = len(positive_found)
    neg_count = len(negative_found)
    
    # Tính điểm cảm xúc
    total = pos_count + neg_count
    if total == 0:
        sentiment_score = 0.0
    else:
        sentiment_score = (pos_count - neg_count) / total
    
    return sentiment_score, positive_found, negative_found


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
    
    # Tiền xử lý query
    query_processed = preprocess_text(query)
    
    # Tìm kiếm cơ bản
    destinations = Destination.objects.all()
    
    # Tìm kiếm với nhiều điều kiện
    if query_processed:
        # Tìm kiếm chính xác (exact match) - ưu tiên cao nhất
        exact_match = destinations.filter(
            Q(name__iexact=query) | Q(location__iexact=query)
        )
        
        # Tìm kiếm gần đúng (contains)
        partial_match = destinations.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query) |
            Q(travel_type__icontains=query)
        ).exclude(id__in=exact_match.values_list('id', flat=True))
        
        # Kết hợp kết quả: exact match trước, partial match sau
        destinations = list(exact_match) + list(partial_match)
        destinations = Destination.objects.filter(
            id__in=[d.id for d in destinations]
        )
    
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
    # 1. Điểm gợi ý cao (overall_score)
    # 2. Số lượng review nhiều (popularity)
    # 3. Rating cao (avg_rating)
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
    
    return destinations
