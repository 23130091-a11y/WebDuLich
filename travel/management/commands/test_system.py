"""
Command kiểm tra tổng hợp hệ thống
Chạy các test cơ bản để đảm bảo mọi thứ hoạt động đúng
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError
from travel.models import Destination, Review, RecommendationScore


class Command(BaseCommand):
    help = 'Kiểm tra tổng hợp hệ thống travel'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Tự động sửa các vấn đề phát hiện được'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Hiển thị chi tiết'
        )

    def handle(self, *args, **options):
        fix_mode = options.get('fix', False)
        verbose = options.get('verbose', False)
        
        self.stdout.write('🔍 KIỂM TRA HỆ THỐNG TRAVEL\n')
        self.stdout.write('=' * 50 + '\n')
        
        issues = []
        
        # 1. Kiểm tra database connection
        self.stdout.write('1️⃣ Kiểm tra kết nối database...')
        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS(' ✓ OK\n'))
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f' ❌ Lỗi: {e}\n'))
            issues.append('Database connection failed')
            return
        
        # 2. Kiểm tra số lượng dữ liệu
        self.stdout.write('2️⃣ Kiểm tra dữ liệu...')
        dest_count = Destination.objects.count()
        review_count = Review.objects.count()
        score_count = RecommendationScore.objects.count()
        
        self.stdout.write(f'\n   📍 Destinations: {dest_count}')
        self.stdout.write(f'   📝 Reviews: {review_count}')
        self.stdout.write(f'   ⭐ Scores: {score_count}')
        
        if dest_count == 0:
            self.stdout.write(self.style.WARNING('\n   ⚠️ Chưa có destination nào!'))
            self.stdout.write('   💡 Chạy: python manage.py import_destinations')
            issues.append('No destinations')
        else:
            self.stdout.write(self.style.SUCCESS('\n   ✓ Có dữ liệu\n'))
        
        # 3. Kiểm tra destinations thiếu reviews
        self.stdout.write('3️⃣ Kiểm tra destinations thiếu reviews...')
        dests_no_reviews = Destination.objects.filter(reviews__isnull=True).distinct()
        no_review_count = dests_no_reviews.count()
        
        if no_review_count > 0:
            self.stdout.write(self.style.WARNING(f'\n   ⚠️ {no_review_count} destinations chưa có review'))
            if verbose:
                for d in dests_no_reviews[:5]:
                    self.stdout.write(f'      - {d.name}')
                if no_review_count > 5:
                    self.stdout.write(f'      ... và {no_review_count - 5} địa điểm khác')
            self.stdout.write('   💡 Chạy: python manage.py crawl_all_reviews')
            issues.append(f'{no_review_count} destinations without reviews')
        else:
            self.stdout.write(self.style.SUCCESS(' ✓ Tất cả đều có reviews\n'))
        
        # 4. Kiểm tra destinations thiếu scores
        self.stdout.write('4️⃣ Kiểm tra destinations thiếu scores...')
        dests_with_scores = RecommendationScore.objects.values_list('destination_id', flat=True)
        dests_no_scores = Destination.objects.exclude(id__in=dests_with_scores)
        no_score_count = dests_no_scores.count()
        
        if no_score_count > 0:
            self.stdout.write(self.style.WARNING(f'\n   ⚠️ {no_score_count} destinations chưa có score'))
            if fix_mode:
                self.stdout.write('   🔧 Đang tính toán scores...')
                from travel.ai_module import recalculate_all_scores
                recalculate_all_scores()
                self.stdout.write(self.style.SUCCESS('   ✓ Đã tính toán xong!'))
            else:
                self.stdout.write('   💡 Chạy: python manage.py calculate_scores')
            issues.append(f'{no_score_count} destinations without scores')
        else:
            self.stdout.write(self.style.SUCCESS(' ✓ Tất cả đều có scores\n'))
        
        # 5. Kiểm tra reviews có rating không hợp lệ
        self.stdout.write('5️⃣ Kiểm tra reviews có rating không hợp lệ...')
        invalid_reviews = Review.objects.exclude(rating__gte=1, rating__lte=5)
        invalid_count = invalid_reviews.count()
        
        if invalid_count > 0:
            self.stdout.write(self.style.ERROR(f'\n   ❌ {invalid_count} reviews có rating không hợp lệ'))
            if fix_mode:
                self.stdout.write('   🔧 Đang sửa...')
                for r in invalid_reviews:
                    r.rating = max(1, min(5, r.rating))
                    r.save()
                self.stdout.write(self.style.SUCCESS('   ✓ Đã sửa xong!'))
            issues.append(f'{invalid_count} invalid ratings')
        else:
            self.stdout.write(self.style.SUCCESS(' ✓ Tất cả ratings hợp lệ\n'))
        
        # 6. Kiểm tra destinations thiếu tọa độ
        self.stdout.write('6️⃣ Kiểm tra destinations thiếu tọa độ...')
        no_coords = Destination.objects.filter(latitude__isnull=True)
        no_coords_count = no_coords.count()
        
        if no_coords_count > 0:
            self.stdout.write(self.style.WARNING(f'\n   ⚠️ {no_coords_count} destinations thiếu tọa độ'))
            if verbose:
                for d in no_coords[:5]:
                    self.stdout.write(f'      - {d.name}')
            self.stdout.write('   💡 Chạy: python manage.py import_csv (với geocoding)')
            issues.append(f'{no_coords_count} destinations without coordinates')
        else:
            self.stdout.write(self.style.SUCCESS(' ✓ Tất cả đều có tọa độ\n'))
        
        # 7. Thống kê tổng hợp
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('📊 THỐNG KÊ TỔNG HỢP:\n')
        
        if dest_count > 0:
            avg_reviews = review_count / dest_count
            self.stdout.write(f'   Trung bình reviews/destination: {avg_reviews:.1f}')
            
            # Top 5 destinations
            top_scores = RecommendationScore.objects.order_by('-overall_score')[:5]
            if top_scores:
                self.stdout.write('\n   🏆 Top 5 địa điểm:')
                for i, s in enumerate(top_scores, 1):
                    self.stdout.write(f'      {i}. {s.destination.name}: {s.overall_score:.2f}')
        
        # Kết luận
        self.stdout.write('\n' + '=' * 50)
        if issues:
            self.stdout.write(self.style.WARNING(f'\n⚠️ Phát hiện {len(issues)} vấn đề:'))
            for issue in issues:
                self.stdout.write(f'   - {issue}')
            if not fix_mode:
                self.stdout.write('\n💡 Chạy với --fix để tự động sửa một số vấn đề')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Hệ thống hoạt động tốt!'))
