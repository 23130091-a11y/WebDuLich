"""
Script để cập nhật RecommendationScore cho tất cả các địa điểm
Chạy: python manage.py shell < update_all_scores.py
Hoặc: python update_all_scores.py (từ thư mục WebDuLich)
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.models import Destination, RecommendationScore, Review, RecommendationConfig
from django.db.models import Avg, Count

def update_destination_scores(destination):
    """Cập nhật điểm gợi ý cho một địa điểm"""
    try:
        config = RecommendationConfig.objects.first()

        review_weight = config.review_score if config else 0.4
        sentiment_weight = config.sentiment_score if config else 0.3
        popularity_weight = config.popularity_score if config else 0.3
        popularity_point_per_review = config.popularity_point_per_review if config else 5

        reviews = Review.objects.filter(destination=destination)
        stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id'),
            avg_sentiment=Avg('sentiment_score')
        )
        
        avg_rating = stats['avg_rating'] or 0
        total_reviews = stats['total_reviews'] or 0
        avg_sentiment = stats['avg_sentiment'] or 0
        
        positive_reviews = reviews.filter(rating__gte=4).count()
        positive_ratio = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0
        
        # Tính điểm
        score_from_rating = (avg_rating / 5) * 100
        score_from_sentiment = ((avg_sentiment + 1) / 2) * 100
        score_from_popularity = min(total_reviews * popularity_point_per_review, 100)
        overall_score = (score_from_rating * review_weight) + \
                        (score_from_sentiment * sentiment_weight) + \
                        (score_from_popularity * popularity_weight)

        # Nếu không có review, đặt điểm mặc định
        if total_reviews == 0:
            overall_score = 50  # Điểm mặc định cho địa điểm chưa có đánh giá
            avg_rating = 0
            positive_ratio = 0

        recommendation, created = RecommendationScore.objects.update_or_create(
            destination=destination,
            defaults={
                'overall_score': overall_score,
                'sentiment_score': score_from_sentiment,
                'popularity_score': score_from_popularity,
                'total_reviews': total_reviews,
                'avg_rating': avg_rating,
                'positive_review_ratio': positive_ratio
            }
        )
        
        return recommendation, created
    except Exception as e:
        print(f"Lỗi khi cập nhật {destination.name}: {e}")
        return None, False

def main():
    destinations = Destination.objects.all()
    total = destinations.count()
    created_count = 0
    updated_count = 0
    
    print(f"Đang cập nhật scores cho {total} địa điểm...")
    
    for i, dest in enumerate(destinations, 1):
        rec, created = update_destination_scores(dest)
        if rec:
            if created:
                created_count += 1
                print(f"[{i}/{total}] ✓ Tạo mới: {dest.name} - Điểm: {rec.overall_score:.0f}")
            else:
                updated_count += 1
                print(f"[{i}/{total}] ↻ Cập nhật: {dest.name} - Điểm: {rec.overall_score:.0f}")
        else:
            print(f"[{i}/{total}] ✗ Lỗi: {dest.name}")
    
    print(f"\n=== HOÀN TẤT ===")
    print(f"Tạo mới: {created_count}")
    print(f"Cập nhật: {updated_count}")
    print(f"Tổng: {total}")

if __name__ == '__main__':
    main()
