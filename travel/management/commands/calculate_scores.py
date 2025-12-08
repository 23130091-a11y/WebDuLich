# Script tính toán điểm gợi ý (chạy định kỳ)
# Cải thiện v2: Thêm options và thống kê chi tiết

from django.core.management.base import BaseCommand
from travel.models import Destination, Review, RecommendationScore
from travel.ai_module import recalculate_all_scores


class Command(BaseCommand):
    help = 'Tính toán lại điểm gợi ý cho tất cả địa điểm'

    def add_arguments(self, parser):
        parser.add_argument(
            '--top',
            type=int,
            default=0,
            help='Chỉ hiển thị top N địa điểm (0 = tất cả)'
        )
        parser.add_argument(
            '--min-reviews',
            type=int,
            default=0,
            help='Chỉ tính cho địa điểm có ít nhất N reviews'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Hiển thị thống kê chi tiết'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Chỉ hiển thị kết quả cuối cùng'
        )

    def handle(self, *args, **options):
        top_n = options.get('top', 0)
        min_reviews = options.get('min_reviews', 0)
        show_stats = options.get('stats', False)
        quiet = options.get('quiet', False)

        self.stdout.write('🔄 Bắt đầu tính toán điểm gợi ý...\n')
        
        results = recalculate_all_scores()
        
        # Lọc theo min_reviews nếu có
        if min_reviews > 0:
            filtered_results = []
            for r in results:
                try:
                    dest = Destination.objects.get(name=r['destination'])
                    if dest.reviews.count() >= min_reviews:
                        filtered_results.append(r)
                except Destination.DoesNotExist:
                    pass
            results = filtered_results
            self.stdout.write(f'📊 Lọc địa điểm có >= {min_reviews} reviews: {len(results)} địa điểm\n')

        # Sắp xếp theo điểm giảm dần
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        # Giới hạn top N
        display_results = results[:top_n] if top_n > 0 else results
        
        if not quiet:
            self.stdout.write('📋 Kết quả:')
            for i, result in enumerate(display_results, 1):
                score = result['score']
                # Color coding
                if score >= 80:
                    style = self.style.SUCCESS
                    emoji = '🌟'
                elif score >= 70:
                    style = self.style.HTTP_INFO
                    emoji = '✓'
                else:
                    style = self.style.WARNING
                    emoji = '○'
                
                self.stdout.write(style(
                    f"  {i:2}. {emoji} {result['destination']}: {score:.2f} điểm"
                ))
        
        # Thống kê
        if show_stats and results:
            scores = [r['score'] for r in results]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            excellent = len([s for s in scores if s >= 80])
            good = len([s for s in scores if 70 <= s < 80])
            average = len([s for s in scores if s < 70])
            
            self.stdout.write('\n📊 THỐNG KÊ:')
            self.stdout.write(f'   Tổng địa điểm: {len(results)}')
            self.stdout.write(f'   Điểm trung bình: {avg_score:.2f}')
            self.stdout.write(f'   Điểm cao nhất: {max_score:.2f}')
            self.stdout.write(f'   Điểm thấp nhất: {min_score:.2f}')
            self.stdout.write(f'\n   🌟 Xuất sắc (>=80): {excellent}')
            self.stdout.write(f'   ✓ Tốt (70-79): {good}')
            self.stdout.write(f'   ○ Trung bình (<70): {average}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Đã tính toán {len(results)} địa điểm!'))
