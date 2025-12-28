"""
Import đánh giá từ file CSV
File CSV cần có các cột: destination_name, author_name, rating, comment

Cách sử dụng:
1. Tạo file CSV với các cột: destination_name, author_name, rating, comment
2. Chạy: python manage.py import_reviews --csv-path data/reviews.csv
"""

from django.core.management.base import BaseCommand
from travel.models import Destination, Review, RecommendationScore
from travel.ai_engine import analyze_sentiment
from django.db.models import Avg, Count
import csv
import os


class Command(BaseCommand):
    help = 'Import đánh giá từ file CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='data/reviews.csv',
            help='Đường dẫn đến file CSV chứa reviews'
        )

    def handle(self, *args, **options):
        csv_path = options.get('csv_path')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'❌ Không tìm thấy file: {csv_path}'))
            self.stdout.write('\n📝 Tạo file CSV với format sau:')
            self.stdout.write('destination_name,author_name,rating,comment')
            self.stdout.write('Hà Nội,Nguyễn Văn A,5,Địa điểm rất đẹp và thú vị!')
            return

        self.stdout.write(f'📂 Đang đọc file: {csv_path}')
        
        imported = 0
        skipped = 0
        errors = 0
        destinations_updated = set()

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        dest_name = row.get('destination_name', '').strip()
                        author = row.get('author_name', 'Khách').strip()
                        rating = int(row.get('rating', 5))
                        comment = row.get('comment', '').strip()
                        
                        if not dest_name:
                            skipped += 1
                            continue
                        
                        # Tìm destination
                        destination = Destination.objects.filter(name__icontains=dest_name).first()
                        if not destination:
                            destination = Destination.objects.filter(location__icontains=dest_name).first()
                        
                        if not destination:
                            self.stdout.write(f'  ⚠️ Không tìm thấy địa điểm: {dest_name}')
                            skipped += 1
                            continue
                        
                        # Kiểm tra duplicate
                        exists = Review.objects.filter(
                            destination=destination,
                            author_name=author,
                            comment=comment
                        ).exists()
                        
                        if exists:
                            skipped += 1
                            continue
                        
                        # Phân tích sentiment
                        sentiment_score = 0.0
                        pos_keywords = []
                        neg_keywords = []
                        if comment:
                            try:
                                sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(comment)
                            except:
                                pass
                        
                        # Tạo review
                        Review.objects.create(
                            destination=destination,
                            author_name=author or 'Khách',
                            rating=min(max(rating, 1), 5),
                            comment=comment,
                            sentiment_score=sentiment_score,
                            positive_keywords=pos_keywords,
                            negative_keywords=neg_keywords
                        )
                        
                        destinations_updated.add(destination.id)
                        imported += 1
                        self.stdout.write(f'  ✓ {destination.name}: {author} - {rating}⭐')
                        
                    except Exception as e:
                        self.stdout.write(f'  ❌ Lỗi: {str(e)}')
                        errors += 1

            # Cập nhật điểm cho các destination
            self.stdout.write('\n📊 Đang cập nhật điểm gợi ý...')
            for dest_id in destinations_updated:
                self.update_scores(dest_id)

            self.stdout.write(self.style.SUCCESS(f'\n✅ Hoàn tất!'))
            self.stdout.write(f'   - Imported: {imported}')
            self.stdout.write(f'   - Skipped: {skipped}')
            self.stdout.write(f'   - Errors: {errors}')
            self.stdout.write(f'   - Destinations updated: {len(destinations_updated)}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Lỗi đọc file: {str(e)}'))

    def update_scores(self, destination_id):
        """Cập nhật điểm gợi ý cho destination"""
        try:
            destination = Destination.objects.get(id=destination_id)
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
            
            review_score = (avg_rating / 5) * 100
            sentiment_score = ((avg_sentiment + 1) / 2) * 100
            popularity_score = min(total_reviews * 5, 100)
            overall_score = (review_score * 0.4) + (sentiment_score * 0.3) + (popularity_score * 0.3)
            
            RecommendationScore.objects.update_or_create(
                destination=destination,
                defaults={
                    'overall_score': overall_score,
                    'review_score': review_score,
                    'sentiment_score': sentiment_score,
                    'popularity_score': popularity_score,
                    'total_reviews': total_reviews,
                    'avg_rating': avg_rating,
                    'positive_review_ratio': positive_ratio
                }
            )
            
            destination.rating = avg_rating
            destination.save(update_fields=['rating'])
            
        except Exception as e:
            self.stdout.write(f'  ⚠️ Lỗi cập nhật điểm: {str(e)}')
