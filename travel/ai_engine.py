"""
Unified AI Engine for WebDuLich
Gộp sentiment analysis và recommendation engine thành 1 module duy nhất

Features:
- PhoBERT sentiment analysis với fallback rule-based
- Recommendation scoring algorithm
- Caching system tích hợp
- Search functionality
- Retry mechanism for robustness
"""

import re
import torch
import logging
import hashlib
from decimal import Decimal
from typing import Tuple, List, Dict, Any

from django.db.models import Q, Avg, Count
from django.core.cache import cache
from django.conf import settings
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================

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

# Từ phủ định
NEGATION_WORDS = [
    'không', 'chẳng', 'chả', 'đừng', 'chưa', 'không phải', 'không hề',
    'không bao giờ', 'chẳng bao giờ', 'không còn', 'chẳng còn', 'không thể',
    'chưa bao giờ', 'chưa từng', 'không được', 'chẳng được', 'không có',
    'thiếu', 'mất', 'hết', 'không thấy', 'chẳng thấy'
]

# Từ tăng cường
INTENSIFIERS = {
    'rất': 1.5, 'cực kỳ': 2.0, 'vô cùng': 2.0, 'quá': 1.5, 'siêu': 1.8,
    'hơi': 0.5, 'khá': 0.8, 'tương đối': 0.7, 'cũng': 0.6,
    'thật sự': 1.5, 'thực sự': 1.5, 'hoàn toàn': 1.8, 'tuyệt đối': 2.0
}

# Stopwords tiếng Việt
STOPWORDS = [
    'là', 'của', 'và', 'có', 'được', 'trong', 'với', 'cho', 'từ', 'này', 'đó',
    'một', 'các', 'những', 'để', 'khi', 'đã', 'sẽ', 'bị', 'nếu', 'như', 'thì',
    'mà', 'hay', 'hoặc', 'nhưng', 'vì', 'nên', 'lại', 'còn', 'đang'
]


# ==================== SENTIMENT ANALYZER ====================

class SentimentAnalyzer:
    """
    Unified Sentiment Analyzer với PhoBERT + Rule-based fallback
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_loaded = False
        
    def load_model(self):
        """Load PhoBERT model (lazy loading)"""
        if self.model_loaded:
            return
        
        try:
            logger.info("Loading PhoBERT sentiment model...")
            model_name = "wonrax/phobert-base-vietnamese-sentiment"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            
            self.model_loaded = True
            logger.info(f"PhoBERT model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load PhoBERT model: {e}")
            logger.warning("Will use rule-based sentiment analysis")
            self.model_loaded = False
    
    def analyze(self, text: str) -> Tuple[float, List[str], List[str]]:
        """
        Phân tích sentiment của text
        
        Returns:
            tuple: (sentiment_score, positive_keywords, negative_keywords)
                - sentiment_score: float từ -1 đến 1
                - positive_keywords: list từ khóa tích cực
                - negative_keywords: list từ khóa tiêu cực
        """
        if not text or not text.strip():
            return 0.0, [], []
        
        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        cache_key = f'sentiment:{text_hash}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Load model nếu chưa load
        if not self.model_loaded:
            self.load_model()
        
        # Sử dụng PhoBERT nếu có, fallback về rule-based
        if self.model_loaded:
            result = self._phobert_analysis(text)
        else:
            result = self._rule_based_analysis(text)
        
        # Cache result
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('sentiment', 86400)
        cache.set(cache_key, result, cache_timeout)
        
        return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RuntimeError, torch.cuda.OutOfMemoryError)),
        reraise=True
    )
    def _phobert_analysis(self, text: str) -> Tuple[float, List[str], List[str]]:
        """
        PhoBERT sentiment analysis with retry mechanism.
        
        Retries up to 3 times with exponential backoff on:
        - RuntimeError (model loading issues)
        - CUDA OutOfMemoryError
        """
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=-1)
            
            # Convert to sentiment score
            probs = probabilities.cpu().numpy()[0]
            
            if len(probs) == 2:  # Binary classification
                neg_prob, pos_prob = probs
                sentiment_score = pos_prob - neg_prob
            else:  # 3-class classification
                neg_prob, neu_prob, pos_prob = probs
                sentiment_score = pos_prob - neg_prob
            
            # Extract keywords using rule-based method
            _, pos_keywords, neg_keywords = self._rule_based_analysis(text)
            
            return float(sentiment_score), pos_keywords, neg_keywords
            
        except Exception as e:
            logger.error(f"PhoBERT analysis failed: {e}")
            return self._rule_based_analysis(text)
    
    def _rule_based_analysis(self, text: str) -> Tuple[float, List[str], List[str]]:
        """Rule-based sentiment analysis (fallback)"""
        text_clean = self._preprocess_text(text)
        sentences = self._split_sentences(text_clean)
        
        total_score = 0.0
        positive_keywords = []
        negative_keywords = []
        
        for sentence in sentences:
            # Tìm từ khóa tích cực
            for keyword in POSITIVE_KEYWORDS:
                if keyword in sentence:
                    is_negated = self._check_negation(sentence, keyword)
                    intensity = self._get_intensity(sentence, keyword)
                    
                    if is_negated:
                        total_score -= 0.5 * intensity
                        negative_keywords.append(f"không {keyword}")
                    else:
                        total_score += 0.5 * intensity
                        positive_keywords.append(keyword)
            
            # Tìm từ khóa tiêu cực
            for keyword in NEGATIVE_KEYWORDS:
                if keyword in sentence:
                    is_negated = self._check_negation(sentence, keyword)
                    intensity = self._get_intensity(sentence, keyword)
                    
                    if is_negated:
                        total_score += 0.5 * intensity
                        positive_keywords.append(f"không {keyword}")
                    else:
                        total_score -= 0.5 * intensity
                        negative_keywords.append(keyword)
        
        # Normalize score to [-1, 1]
        sentiment_score = max(-1.0, min(1.0, total_score))
        
        return sentiment_score, list(set(positive_keywords)), list(set(negative_keywords))
    
    def _preprocess_text(self, text: str) -> str:
        """Tiền xử lý văn bản"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _split_sentences(self, text: str) -> List[str]:
        """Tách văn bản thành các câu"""
        sentences = re.split(r'[.!?;,]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _check_negation(self, sentence: str, keyword: str, window_size: int = 3) -> bool:
        """Kiểm tra từ khóa có bị phủ định không"""
        words = sentence.split()
        keyword_pos = -1
        
        # Tìm vị trí keyword
        for i, word in enumerate(words):
            if keyword in word:
                keyword_pos = i
                break
        
        if keyword_pos == -1:
            return False
        
        # Kiểm tra window phía trước
        start = max(0, keyword_pos - window_size)
        window = words[start:keyword_pos]
        
        for negation in NEGATION_WORDS:
            if any(negation in word for word in window):
                return True
        
        return False
    
    def _get_intensity(self, sentence: str, keyword: str) -> float:
        """Tính độ mạnh của từ khóa dựa trên intensifiers"""
        words = sentence.split()
        keyword_pos = -1
        
        for i, word in enumerate(words):
            if keyword in word:
                keyword_pos = i
                break
        
        if keyword_pos == -1:
            return 1.0
        
        # Kiểm tra intensifiers xung quanh keyword
        intensity = 1.0
        for i in range(max(0, keyword_pos - 2), min(len(words), keyword_pos + 3)):
            word = words[i]
            for intensifier, multiplier in INTENSIFIERS.items():
                if intensifier in word:
                    intensity *= multiplier
                    break
        
        return min(intensity, 3.0)  # Cap at 3.0


# ==================== RECOMMENDATION ENGINE ====================

class RecommendationEngine:
    """
    Recommendation Engine cho destinations
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
    
    def search_destinations(self, query: str, filters: Dict[str, Any]) -> List:
        """
        Tìm kiếm destinations với AI scoring
        
        Args:
            query: Search query
            filters: Dict filters (location, travel_type, max_price, etc.)
            
        Returns:
            List of destinations sorted by relevance score
        """
        from .models import Destination
        
        # Build base queryset
        queryset = Destination.objects.select_related('recommendation').prefetch_related('reviews')
        
        # Apply filters
        if filters.get('location'):
            queryset = queryset.filter(location__icontains=filters['location'])
        
        if filters.get('travel_type'):
            queryset = queryset.filter(travel_type__icontains=filters['travel_type'])
        
        if filters.get('max_price'):
            try:
                max_price = Decimal(str(filters['max_price']))
                queryset = queryset.filter(avg_price__lte=max_price)
            except:
                pass
        
        # Text search
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
        
        # Calculate relevance scores
        destinations = list(queryset)
        scored_destinations = []
        
        for dest in destinations:
            relevance_score = self._calculate_relevance_score(dest, query, filters)
            scored_destinations.append((dest, relevance_score))
        
        # Sort by score
        scored_destinations.sort(key=lambda x: x[1], reverse=True)
        
        return [dest for dest, score in scored_destinations]
    
    def calculate_destination_score(self, destination) -> Dict[str, float]:
        """
        Tính toán điểm số tổng hợp cho destination
        
        Returns:
            Dict với các scores: overall, review, sentiment, popularity
        """
        from .models import RecommendationScore
        reviews = destination.reviews.filter(status='approved')

        total_reviews = reviews.count()
        avg_sentiment = reviews.aggregate(avg=Avg('sentiment_score'))['avg'] or 0

        rec, _ = RecommendationScore.objects.get_or_create(destination=destination)

        def clamp(score, min_val=0, max_val=100):
            return max(min_val, min(max_val, score))

        review_score = clamp((float(destination.avg_rating) / 5) * 100 if destination.avg_rating else 0)
        sentiment_score = clamp(((avg_sentiment + 1) / 2) * 100)

        views_score = min(rec.total_views / 1000, 1.0)
        favorite_score = min(rec.total_favorites / 200, 1.0)
        popularity_score = clamp((views_score * 0.6 + favorite_score * 0.4) * 100)

        overall_score = round(
            review_score * 0.5 +
            sentiment_score * 0.3 +
            popularity_score * 0.2,
            2
        )

        rec.review_score = review_score
        rec.sentiment_score = sentiment_score
        rec.popularity_score = popularity_score
        rec.total_reviews = total_reviews
        rec.overall_score = overall_score
        rec.save()

        return {
            "overall_score": overall_score,
            "review_score": review_score,
            "sentiment_score": sentiment_score,
            "popularity_score": popularity_score,
            "total_reviews": total_reviews,
        }

    
    def _calculate_relevance_score(self, destination, query: str, filters: Dict) -> float:
        """Tính điểm relevance cho search results"""
        score = 0.0
        
        # Base recommendation score (50% weight)
        if hasattr(destination, 'recommendation') and destination.recommendation:
            score += (destination.recommendation.overall_score / 100) * 40
        
        # Query relevance (30% weight)
        if query:
            query_lower = query.lower()
            name_match = query_lower in destination.name.lower()
            desc_match = query_lower in (destination.description or '').lower()
            location_match = query_lower in destination.location.lower()
            
            if name_match:
                score += 30
            elif location_match:
                score += 20
            elif desc_match:
                score += 10
        
        # Filter bonus (20% weight)
        if filters.get('travel_type') and filters['travel_type'].lower() in destination.travel_type.lower():
            score += 20
        
        return score
    
    def _calculate_price_score(self, destination) -> float:
        """Tính price competitiveness score"""
        if not destination.avg_price:
            return 5.0  # Neutral score
        
        # Simple price scoring - lower price = higher score
        # This can be improved with market analysis
        price = float(destination.avg_price)
        
        if price < 500000:  # < 500k VND
            return 10.0
        elif price < 1000000:  # < 1M VND
            return 8.0
        elif price < 2000000:  # < 2M VND
            return 6.0
        elif price < 5000000:  # < 5M VND
            return 4.0
        else:
            return 2.0


# ==================== GLOBAL INSTANCES ====================

# Singleton instances
_sentiment_analyzer = None
_recommendation_engine = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get singleton sentiment analyzer instance"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer

def get_recommendation_engine() -> RecommendationEngine:
    """Get singleton recommendation engine instance"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


# ==================== PUBLIC API FUNCTIONS ====================

def analyze_sentiment(text: str) -> Tuple[float, List[str], List[str]]:
    """
    Public API for sentiment analysis
    
    Args:
        text: Text to analyze
        
    Returns:
        tuple: (sentiment_score, positive_keywords, negative_keywords)
    """
    analyzer = get_sentiment_analyzer()
    return analyzer.analyze(text)

def search_destinations(query: str, filters: Dict[str, Any]) -> List:
    """
    Public API for destination search
    
    Args:
        query: Search query
        filters: Search filters
        
    Returns:
        List of destinations sorted by relevance
    """
    engine = get_recommendation_engine()
    return engine.search_destinations(query, filters)

def calculate_destination_score(destination) -> Dict[str, float]:
    """
    Public API for destination scoring
    
    Args:
        destination: Destination model instance
        
    Returns:
        Dict with various scores
    """
    engine = get_recommendation_engine()
    return engine.calculate_destination_score(destination)


def get_similar_destinations(destination, limit: int = 4) -> List:
    """
    Gợi ý địa điểm tương tự dựa trên:
    - Cùng loại hình du lịch
    - Cùng khu vực
    - Mức giá tương đương
    - Điểm đánh giá cao
    
    Args:
        destination: Destination hiện tại
        limit: Số lượng gợi ý tối đa
        
    Returns:
        List các destination tương tự
    """
    from .models import Destination
    from django.db.models import Q, F, Value, FloatField
    from django.db.models.functions import Abs
    
    # Tìm các địa điểm khác (không phải địa điểm hiện tại)
    queryset = Destination.objects.select_related('recommendation').exclude(id=destination.id)
    
    similar = []
    
    # 1. Cùng loại hình du lịch (ưu tiên cao nhất)
    same_type = queryset.filter(travel_type=destination.travel_type)
    
    # 2. Cùng khu vực
    same_location = queryset.filter(location=destination.location)
    
    # 3. Mức giá tương đương (±30%)
    if destination.avg_price:
        min_price = float(destination.avg_price) * 0.7
        max_price = float(destination.avg_price) * 1.3
        similar_price = queryset.filter(avg_price__gte=min_price, avg_price__lte=max_price)
    else:
        similar_price = queryset.none()
    
    # Gộp và tính điểm tương đồng
    candidates = {}
    
    # Điểm cho cùng loại hình
    for dest in same_type[:10]:
        candidates[dest.id] = {'dest': dest, 'score': 40}
    
    # Điểm cho cùng khu vực
    for dest in same_location[:10]:
        if dest.id in candidates:
            candidates[dest.id]['score'] += 30
        else:
            candidates[dest.id] = {'dest': dest, 'score': 30}
    
    # Điểm cho mức giá tương đương
    for dest in similar_price[:10]:
        if dest.id in candidates:
            candidates[dest.id]['score'] += 20
        else:
            candidates[dest.id] = {'dest': dest, 'score': 20}
    
    # Thêm điểm recommendation
    for dest_id, data in candidates.items():
        dest = data['dest']
        if hasattr(dest, 'recommendation') and dest.recommendation:
            data['score'] += dest.recommendation.overall_score * 0.05
    
    # Sắp xếp theo điểm và lấy top
    sorted_candidates = sorted(candidates.values(), key=lambda x: x['score'], reverse=True)
    
    return [c['dest'] for c in sorted_candidates[:limit]]


def get_personalized_recommendations(user_preferences: Dict, limit: int = 6) -> List:
    """
    Gợi ý cá nhân hóa dựa trên sở thích người dùng
    
    Args:
        user_preferences: Dict chứa sở thích
            - travel_types: List loại hình yêu thích
            - locations: List địa điểm yêu thích
            - max_price: Ngân sách tối đa
        limit: Số lượng gợi ý
        
    Returns:
        List các destination phù hợp
    """
    from .models import Destination
    from django.db.models import Q
    
    queryset = Destination.objects.select_related('recommendation')
    
    # Filter theo sở thích
    filters = Q()
    
    travel_types = user_preferences.get('travel_types', [])
    if travel_types:
        type_filter = Q()
        for t in travel_types:
            type_filter |= Q(travel_type__icontains=t)
        filters &= type_filter
    
    locations = user_preferences.get('locations', [])
    if locations:
        loc_filter = Q()
        for loc in locations:
            loc_filter |= Q(location__icontains=loc)
        filters &= loc_filter
    
    max_price = user_preferences.get('max_price')
    if max_price:
        filters &= Q(avg_price__lte=max_price)
    
    if filters:
        queryset = queryset.filter(filters)
    
    # Sắp xếp theo điểm gợi ý
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])


def get_seasonal_recommendations(month: int = None, limit: int = 6) -> List:
    """
    Gợi ý theo mùa/thời điểm trong năm
    
    Args:
        month: Tháng (1-12), mặc định là tháng hiện tại
        limit: Số lượng gợi ý
        
    Returns:
        List các destination phù hợp với mùa
    """
    from .models import Destination
    from datetime import datetime
    
    if month is None:
        month = datetime.now().month
    
    queryset = Destination.objects.select_related('recommendation')
    
    # Gợi ý theo mùa ở Việt Nam
    if month in [12, 1, 2]:  # Mùa đông - Tết
        # Ưu tiên: Miền Bắc (hoa đào), Đà Lạt (hoa mai anh đào)
        queryset = queryset.filter(
            Q(location__icontains='Hà Nội') |
            Q(location__icontains='Sa Pa') |
            Q(location__icontains='Đà Lạt') |
            Q(travel_type__icontains='Núi')
        )
    elif month in [3, 4, 5]:  # Mùa xuân
        # Ưu tiên: Miền Trung, biển
        queryset = queryset.filter(
            Q(location__icontains='Đà Nẵng') |
            Q(location__icontains='Huế') |
            Q(location__icontains='Hội An') |
            Q(travel_type__icontains='Biển')
        )
    elif month in [6, 7, 8]:  # Mùa hè
        # Ưu tiên: Biển, đảo
        queryset = queryset.filter(
            Q(location__icontains='Nha Trang') |
            Q(location__icontains='Phú Quốc') |
            Q(location__icontains='Hạ Long') |
            Q(travel_type__icontains='Biển')
        )
    else:  # Mùa thu (9, 10, 11)
        # Ưu tiên: Tây Nguyên, miền Bắc
        queryset = queryset.filter(
            Q(location__icontains='Đà Lạt') |
            Q(location__icontains='Hà Nội') |
            Q(location__icontains='Ninh Bình') |
            Q(travel_type__icontains='Núi')
        )
    
    # Sắp xếp theo điểm
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])


def get_personalized_for_user(user, limit: int = 6) -> List:
    """
    Gợi ý cá nhân hóa dựa trên sở thích đã lưu của user
    
    Args:
        user: User object
        limit: Số lượng gợi ý
        
    Returns:
        List các destination phù hợp với sở thích user
    """
    from .models import Destination
    from users.models import TravelPreference
    from django.db.models import Q
    
    # Lấy sở thích của user
    preferences = TravelPreference.objects.filter(user=user)
    
    if not preferences.exists():
        # Nếu chưa có sở thích, trả về top destinations
        return list(
            Destination.objects.select_related('recommendation')
            .order_by('-recommendation__overall_score')[:limit]
        )
    
    # Lấy danh sách travel_type và location yêu thích
    travel_types = list(preferences.values_list('travel_type', flat=True).distinct())
    locations = list(preferences.values_list('location', flat=True).distinct())
    
    # Build query
    queryset = Destination.objects.select_related('recommendation')
    
    filters = Q()
    
    # Filter theo loại hình yêu thích
    if travel_types:
        type_filter = Q()
        for t in travel_types:
            if t:
                type_filter |= Q(travel_type__icontains=t)
        if type_filter:
            filters |= type_filter
    
    # Filter theo địa điểm yêu thích
    if locations:
        loc_filter = Q()
        for loc in locations:
            if loc:
                loc_filter |= Q(location__icontains=loc)
        if loc_filter:
            filters |= loc_filter
    
    if filters:
        queryset = queryset.filter(filters)
    
    # Sắp xếp theo điểm gợi ý
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])
