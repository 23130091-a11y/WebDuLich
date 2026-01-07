"""
Universal Recommendation Scoring Engine v2.1
=============================================

Cải tiến v2.1:
1. Convention rõ ràng: tất cả component ∈ [0,10], overall ∈ [0,100]
2. Anti-gaming: min-of-penalties thay vì multiply chaining
3. Recency = freshness only (không double-count rating)
4. Confidence penalty cho địa điểm ít dữ liệu
5. Burst penalty mềm hơn (dựa trên burst_strength)
6. Sentiment weight có cap và confidence scaling
7. Engagement tách biệt hơn với Sentiment

Công thức:
    overall_0_10 = Σ(weight × component_score)
    overall_0_100 = overall_0_10 × 10 × confidence_factor
"""

import math
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
from django.db.models import Avg, Count, Sum, F, Q
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class GlobalStats:
    """Tính toán và cache các thống kê toàn cục"""
    
    CACHE_KEY = 'scoring_global_stats_v21'
    CACHE_TTL = 3600
    
    @classmethod
    def get_stats(cls) -> Dict[str, float]:
        cached = cache.get(cls.CACHE_KEY)
        if cached:
            return cached
        
        stats = cls._calculate_stats()
        cache.set(cls.CACHE_KEY, stats, cls.CACHE_TTL)
        return stats

    @classmethod
    def _calculate_stats(cls) -> Dict[str, float]:
        from .models import Review, Destination
        
        rating_stats = Review.objects.filter(status='approved').aggregate(
            mean=Avg('rating'),
            count=Count('id'),
        )
        
        dest_review_counts = list(
            Destination.objects.annotate(
                review_count=Count('reviews', filter=Q(reviews__status='approved'))
            ).values_list('review_count', flat=True)
        )
        
        review_counts_positive = sorted([c for c in dest_review_counts if c > 0]) or [1]
        
        return {
            'global_mean_rating': rating_stats['mean'] or 3.5,
            'total_reviews': rating_stats['count'] or 0,
            'review_count_p10': cls._percentile(review_counts_positive, 10),
            'review_count_p50': cls._percentile(review_counts_positive, 50),
            'review_count_p90': cls._percentile(review_counts_positive, 90),
            'review_count_p95': cls._percentile(review_counts_positive, 95),
            'review_count_max': max(review_counts_positive),
            'num_destinations_with_reviews': len(review_counts_positive),
        }
    
    @staticmethod
    def _percentile(sorted_list: List[float], percentile: int) -> float:
        if not sorted_list:
            return 0
        k = (len(sorted_list) - 1) * percentile / 100
        f, c = math.floor(k), math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        return sorted_list[int(f)] * (c - k) + sorted_list[int(c)] * (k - f)
    
    @classmethod
    def invalidate_cache(cls):
        cache.delete(cls.CACHE_KEY)


class AntiGamingRules:
    """
    Anti-gaming v2.1: Min-of-penalties approach
    Thay vì nhân liên tục, lấy min của các penalty scores
    """
    
    @classmethod
    def calculate_review_weight(cls, review, all_reviews_for_dest) -> float:
        """
        Tính weight bằng min-of-penalties
        Mỗi penalty ∈ [0, 1], weight = min(penalties)
        """
        penalties = []
        
        # 1. User verification (0.7 nếu chưa verify, 1.0 nếu đã verify)
        if review.user:
            if hasattr(review, 'is_verified') and not review.is_verified:
                penalties.append(0.7)
            
            # Account age (0.6 nếu < 1 ngày, scale lên 1.0 sau 7 ngày)
            if hasattr(review.user, 'date_joined'):
                account_age = (timezone.now() - review.user.date_joined).days
                age_penalty = min(1.0, 0.6 + account_age * 0.057)
                penalties.append(age_penalty)
        else:
            penalties.append(0.5)
        
        # 2. Duplicate IP (soft penalty dựa trên số lần trùng)
        if hasattr(review, 'user_ip') and review.user_ip:
            same_ip_count = sum(
                1 for r in all_reviews_for_dest 
                if hasattr(r, 'user_ip') and r.user_ip == review.user_ip and r.id != review.id
            )
            if same_ip_count > 0:
                ip_penalty = max(0.3, 0.7 - same_ip_count * 0.2)
                penalties.append(ip_penalty)
        
        # 3. Multiple reviews per user
        if review.user:
            user_reviews = [r for r in all_reviews_for_dest if r.user_id == review.user_id]
            user_reviews_sorted = sorted(user_reviews, key=lambda r: r.created_at)
            review_index = next((i for i, r in enumerate(user_reviews_sorted) if r.id == review.id), 0)
            
            if review_index >= 3:
                penalties.append(0.3)
            elif review_index >= 1:
                penalties.append(0.5)
        
        # 4. Spam score (soft penalty)
        if hasattr(review, 'spam_score') and review.spam_score and review.spam_score > 0.3:
            spam_penalty = max(0.2, 1 - review.spam_score)
            penalties.append(spam_penalty)
        
        # 5. Low quality
        if hasattr(review, 'is_low_quality') and review.is_low_quality:
            penalties.append(0.4)
        
        if penalties:
            weight = min(penalties)
        else:
            weight = 1.0
        
        return max(0.15, min(1.0, weight))
    
    @classmethod
    def calculate_burst_strength(cls, reviews, window_hours: int = 24) -> float:
        """
        Tính burst_strength ∈ [0, 1]
        0 = không burst, 1 = burst cực mạnh
        """
        if len(reviews) < 5:
            return 0.0
        
        now = timezone.now()
        window_start = now - timedelta(hours=window_hours)
        
        recent_count = sum(1 for r in reviews if r.created_at >= window_start)
        total_count = len(reviews)
        
        recent_ratio = recent_count / total_count
        
        if recent_ratio < 0.3:
            return 0.0
        elif recent_ratio < 0.5:
            return (recent_ratio - 0.3) / 0.2 * 0.5
        else:
            return 0.5 + (recent_ratio - 0.5) / 0.5 * 0.5

class
 ContentQualityAnalyzer:
    """Phân tích chất lượng nội dung review"""
    
    EMOJI_PATTERN = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
    REPEATED_CHAR_PATTERN = re.compile(r'(.)\1{4,}')
    
    @classmethod
    def analyze(cls, text: str) -> Dict[str, Any]:
        if not text:
            return {'quality_score': 0.2, 'is_low_quality': True}
        
        text = text.strip()
        words = text.split()
        word_count = len(words)
        
        emoji_count = len(cls.EMOJI_PATTERN.findall(text))
        repeated_chars = len(cls.REPEATED_CHAR_PATTERN.findall(text))
        
        unique_words = len(set(w.lower() for w in words))
        diversity = unique_words / max(word_count, 1)
        
        quality_score = 1.0
        
        if word_count < 3:
            quality_score *= 0.3
        elif word_count < 10:
            quality_score *= 0.6
        
        if word_count > 0 and emoji_count / word_count > 0.3:
            quality_score *= 0.5
        
        if repeated_chars > 2:
            quality_score *= 0.6
        
        if diversity < 0.3 and word_count > 10:
            quality_score *= 0.5
        
        if 15 <= word_count <= 150:
            quality_score = min(1.0, quality_score * 1.1)
        
        return {
            'quality_score': max(0.1, min(1.0, quality_score)),
            'is_low_quality': quality_score < 0.4,
            'word_count': word_count,
            'diversity': diversity,
        }


class UniversalScoringEngine:
    """
    Universal Scoring Engine v2.1
    
    Convention:
    - Tất cả component scores ∈ [0, 10]
    - overall_0_10 = weighted sum of components
    - overall_0_100 = overall_0_10 × 10 × confidence_factor
    """
    
    WEIGHTS = {
        'bayesian_rating': 0.40,
        'popularity': 0.20,
        'sentiment': 0.20,
        'recency': 0.10,
        'engagement': 0.10,
    }
    
    RECENCY_HALF_LIFE_DAYS = 180
    
    def __init__(self):
        self._global_stats = None
    
    @property
    def global_stats(self) -> Dict[str, float]:
        if self._global_stats is None:
            self._global_stats = GlobalStats.get_stats()
        return self._global_stats
    
    def refresh_stats(self):
        GlobalStats.invalidate_cache()
        self._global_stats = None
    
    def calculate_score(self, destination, include_breakdown: bool = False) -> Dict[str, Any]:
        """Tính điểm tổng hợp cho một địa điểm"""
        reviews = list(destination.reviews.filter(status='approved'))
        
        if not reviews:
            return self._empty_score()
        
        review_weights = {
            r.id: AntiGamingRules.calculate_review_weight(r, reviews)
            for r in reviews
        }
        total_weight = sum(review_weights.values())
        
        burst_strength = AntiGamingRules.calculate_burst_strength(reviews)
        
        bayesian_rating = self._calculate_bayesian_rating(reviews, review_weights)
        popularity_score = self._calculate_popularity_score(reviews, burst_strength)
        sentiment_score = self._calculate_sentiment_score(reviews, review_weights)
        recency_score = self._calculate_recency_score(reviews, burst_strength)
        engagement_score = self._calculate_engagement_score(reviews)
        
        overall_0_10 = (
            bayesian_rating * self.WEIGHTS['bayesian_rating'] +
            popularity_score * self.WEIGHTS['popularity'] +
            sentiment_score * self.WEIGHTS['sentiment'] +
            recency_score * self.WEIGHTS['recency'] +
            engagement_score * self.WEIGHTS['engagement']
        )
        
        C = self._get_dynamic_prior_c()
        confidence_factor = min(1.0, 0.8 + 0.2 * (total_weight / C))
        
        overall_0_100 = overall_0_10 * 10 * confidence_factor
        
        total_reviews = len(reviews)
        avg_rating = sum(r.rating for r in reviews) / total_reviews
        positive_ratio = sum(1 for r in reviews if r.rating >= 4) / total_reviews * 100
        
        result = {
            'overall_score': round(overall_0_100, 2),
            'bayesian_rating': round(bayesian_rating, 2),
            'popularity_score': round(popularity_score, 2),
            'sentiment_score': round(sentiment_score, 2),
            'recency_score': round(recency_score, 2),
            'engagement_score': round(engagement_score, 2),
            'total_reviews': total_reviews,
            'avg_rating': round(avg_rating, 2),
            'positive_review_ratio': round(positive_ratio, 2),
            'confidence_level': self._get_confidence_level(total_reviews),
            'confidence_factor': round(confidence_factor, 3),
            'burst_strength': round(burst_strength, 2),
        }
        
        if include_breakdown:
            result['breakdown'] = {
                'weights': self.WEIGHTS,
                'global_mean_rating': self.global_stats['global_mean_rating'],
                'prior_C': self._get_dynamic_prior_c(),
                'popularity_cap': self.global_stats['review_count_p95'],
                'total_weight': round(total_weight, 2),
            }
        
        return result
    
def _empty_score(self) -> Dict[str, Any]:
        return {
            'overall_score': 0.0,
            'bayesian_rating': 0.0,
            'popularity_score': 0.0,
            'sentiment_score': 0.0,
            'recency_score': 0.0,
            'engagement_score': 0.0,
            'total_reviews': 0,
            'avg_rating': 0.0,
            'positive_review_ratio': 0.0,
            'confidence_level': 'none',
            'confidence_factor': 0.8,
            'burst_strength': 0.0,
        }
    
    def _get_dynamic_prior_c(self) -> float:
        p10 = self.global_stats.get('review_count_p10', 5)
        return max(5, min(50, p10))
    
    def _calculate_bayesian_rating(self, reviews: List, review_weights: Dict) -> float:
        """Bayesian Average Rating → [0, 10]"""
        C = self._get_dynamic_prior_c()
        m = self.global_stats.get('global_mean_rating', 3.5)
        
        weighted_sum = sum(r.rating * review_weights.get(r.id, 1.0) for r in reviews)
        total_weight = sum(review_weights.values())
        
        bayesian_avg = (C * m + weighted_sum) / (C + total_weight)
        return (bayesian_avg - 1) / 4 * 10
    
    def _calculate_popularity_score(self, reviews: List, burst_strength: float) -> float:
        """Popularity Score → [0, 10]"""
        n = len(reviews)
        if n == 0:
            return 0.0
        
        n_cap = max(10, self.global_stats.get('review_count_p95', 100))
        
        raw_score = math.log(1 + n) / math.log(1 + n_cap)
        raw_score = min(1.0, raw_score)
        
        burst_penalty = 1 - 0.3 * burst_strength
        
        return raw_score * 10 * burst_penalty
    
    def _calculate_sentiment_score(self, reviews: List, review_weights: Dict) -> float:
        """Sentiment Score → [0, 10]"""
        total_weight = 0
        weighted_sentiment = 0
        
        for review in reviews:
            base_weight = review_weights.get(review.id, 1.0)
            
            helpful_count = getattr(review, 'helpful_count', 0) or 0
            helpful_weight = min(1.8, 1 + math.log(1 + helpful_count) * 0.25)
            
            comment_len = len(review.comment or '')
            length_weight = min(1.4, 1 + math.log(1 + comment_len / 80) * 0.15)
            
            quality = ContentQualityAnalyzer.analyze(review.comment or '')
            quality_weight = quality['quality_score']
            
            combined_weight = base_weight * helpful_weight * length_weight * quality_weight
            combined_weight = min(2.5, combined_weight)
            
            sentiment = getattr(review, 'sentiment_score', 0) or 0
            sentiment_normalized = (sentiment + 1) / 2
            
            weighted_sentiment += sentiment_normalized * combined_weight
            total_weight += combined_weight
        
        if total_weight == 0:
            return 5.0
        
        return (weighted_sentiment / total_weight) * 10
    
    def _calculate_recency_score(self, reviews: List, burst_strength: float) -> float:
        """Recency Score → [0, 10]"""
        if not reviews:
            return 0.0
        
        now = timezone.now()
        total_decay = 0
        
        for review in reviews:
            days_old = (now - review.created_at).days
            decay = 0.5 ** (days_old / self.RECENCY_HALF_LIFE_DAYS)
            total_decay += decay
        
        avg_decay = total_decay / len(reviews)
        score = avg_decay * 10
        
        if burst_strength > 0:
            score = score * (1 - burst_strength * 0.3) + 5.0 * (burst_strength * 0.3)
        
        return score
    
    def _calculate_engagement_score(self, reviews: List) -> float:
        """Engagement Score → [0, 10]"""
        if not reviews:
            return 0.0
        
        n = len(reviews)
        
        verified_count = sum(1 for r in reviews if getattr(r, 'is_verified', False))
        verified_ratio = verified_count / n
        
        reviews_with_helpful = sum(1 for r in reviews if (getattr(r, 'helpful_count', 0) or 0) > 0)
        helpful_ratio = reviews_with_helpful / n
        
        quality_reviews = 0
        for r in reviews:
            if r.comment:
                quality = ContentQualityAnalyzer.analyze(r.comment)
                if quality['word_count'] >= 15 and not quality['is_low_quality']:
                    quality_reviews += 1
        content_ratio = quality_reviews / n
        
        engagement = (
            verified_ratio * 0.4 +
            helpful_ratio * 0.3 +
            content_ratio * 0.3
        )
        
        return engagement * 10
    
    def _get_confidence_level(self, total_reviews: int) -> str:
        p10 = self.global_stats.get('review_count_p10', 5)
        p50 = self.global_stats.get('review_count_p50', 20)
        
        if total_reviews == 0:
            return 'none'
        elif total_reviews < max(3, p10 * 0.5):
            return 'low'
        elif total_reviews < p10:
            return 'medium'
        elif total_reviews < p50:
            return 'high'
        else:
            return 'very_high'

def
 update_destination_scores(destination_id: int = None, verbose: bool = False) -> int:
    """Cập nhật điểm cho destinations"""
    from .models import Destination, RecommendationScore
    
    engine = UniversalScoringEngine()
    engine.refresh_stats()
    
    if destination_id:
        destinations = Destination.objects.filter(id=destination_id)
    else:
        destinations = Destination.objects.all()
    
    updated = 0
    for destination in destinations:
        scores = engine.calculate_score(destination, include_breakdown=verbose)
        
        RecommendationScore.objects.update_or_create(
            destination=destination,
            defaults={
                'overall_score': scores['overall_score'],
                'review_score': scores['bayesian_rating'],
                'sentiment_score': scores['sentiment_score'],
                'popularity_score': scores['popularity_score'],
                'total_reviews': scores['total_reviews'],
                'avg_rating': scores['avg_rating'],
                'positive_review_ratio': scores['positive_review_ratio'],
            }
        )
        updated += 1
        
        if verbose:
            logger.info(f"Updated {destination.name}: {scores['overall_score']:.1f}/100")
    
    return updated


def get_top_destinations(limit: int = 10, travel_type: str = None, min_confidence: str = 'low') -> List:
    """Lấy top destinations theo điểm gợi ý"""
    from .models import Destination
    
    confidence_thresholds = {'none': 0, 'low': 1, 'medium': 3, 'high': 5, 'very_high': 10}
    min_reviews = confidence_thresholds.get(min_confidence, 0)
    
    queryset = Destination.objects.select_related('recommendation')
    
    if travel_type:
        queryset = queryset.filter(travel_type__icontains=travel_type)
    
    queryset = queryset.filter(
        recommendation__isnull=False,
        recommendation__overall_score__gt=0,
        recommendation__total_reviews__gte=min_reviews
    )
    
    return list(queryset.order_by('-recommendation__overall_score')[:limit])


_scoring_engine = None

def get_scoring_engine() -> UniversalScoringEngine:
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = UniversalScoringEngine()
    return _scoring_engine