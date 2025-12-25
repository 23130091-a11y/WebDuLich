"""
Script tạo reviews cho tất cả địa điểm
Cải thiện v2: Thêm dry-run, progress tracking, và thống kê
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from travel.models import Destination, Review
from travel.ai_module import analyze_sentiment
import random


class Command(BaseCommand):
    help = 'Tạo reviews cho tất cả địa điểm chưa có review'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-reviews',
            type=int,
            default=15,
            help='Số reviews tối thiểu cho mỗi địa điểm'
        )
        parser.add_argument(
            '--max-reviews',
            type=int,
            default=35,
            help='Số reviews tối đa cho mỗi địa điểm'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ preview, không thực sự tạo reviews'
        )
        parser.add_argument(
            '--destination-id',
            type=int,
            help='Chỉ tạo reviews cho một địa điểm cụ thể'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Tạo thêm reviews ngay cả khi đã đủ số lượng'
        )

    def handle(self, *args, **options):
        min_reviews = options.get('min_reviews')
        max_reviews = options.get('max_reviews')
        dry_run = options.get('dry_run', False)
        destination_id = options.get('destination_id')
        force = options.get('force', False)

        self.stdout.write('📝 Tạo reviews cho các địa điểm\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ CHẾ ĐỘ DRY-RUN: Không thực sự tạo reviews\n'))

        # Lấy địa điểm
        if destination_id:
            try:
                destinations = [Destination.objects.get(id=destination_id)]
                self.stdout.write(f'📍 Chỉ xử lý: {destinations[0].name}\n')
            except Destination.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Không tìm thấy địa điểm ID {destination_id}'))
                return
        else:
            destinations = Destination.objects.all()
        
        if not destinations:
            self.stdout.write(self.style.ERROR(
                '❌ Chưa có địa điểm nào! Chạy: python manage.py import_destinations'
            ))
            return

        # Dữ liệu review đa dạng
        review_templates = self._get_review_templates()
        vietnamese_names = self._get_vietnamese_names()

        total_created = 0
        skipped_count = 0
        total = len(destinations)

        # Dry run - chỉ preview
        if dry_run:
            need_reviews = 0
            for dest in destinations:
                existing = Review.objects.filter(destination=dest).count()
                if existing < min_reviews or force:
                    target = random.randint(min_reviews, max_reviews)
                    need = max(0, target - existing) if not force else target
                    need_reviews += need
                    self.stdout.write(f'  📍 {dest.name}: {existing} hiện có → +{need} reviews')
            
            self.stdout.write(f'\n📊 Tổng cộng sẽ tạo: ~{need_reviews} reviews')
            return

        # Thực sự tạo reviews
        try:
            with transaction.atomic():
                for i, dest in enumerate(destinations, 1):
                    existing_count = Review.objects.filter(destination=dest).count()
                    
                    if existing_count >= min_reviews and not force:
                        skipped_count += 1
                        continue

                    # Số reviews cần tạo
                    target_count = random.randint(min_reviews, max_reviews)
                    need_count = target_count - existing_count if not force else target_count

                    created_count = 0
                    for _ in range(need_count):
                        # Random loại sentiment
                        sentiment_type = random.choices(
                            ['positive', 'neutral', 'negative'],
                            weights=[0.65, 0.25, 0.10]
                        )[0]

                        # Lấy template phù hợp với loại địa điểm
                        templates = review_templates.get(dest.travel_type, review_templates['default'])
                        comment = random.choice(templates[sentiment_type])

                        # Rating tương ứng (validate 1-5)
                        if sentiment_type == 'positive':
                            rating = random.choice([4, 4, 5, 5, 5])
                        elif sentiment_type == 'neutral':
                            rating = random.choice([3, 3, 4])
                        else:
                            rating = random.choice([1, 2, 2])
                        
                        # Đảm bảo rating trong range 1-5
                        rating = max(1, min(5, rating))

                        # Tên người đánh giá
                        author_name = random.choice(vietnamese_names)

                        # Phân tích sentiment
                        sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(comment)

                        Review.objects.create(
                            destination=dest,
                            author_name=author_name,
                            rating=rating,
                            comment=comment,
                            sentiment_score=sentiment_score,
                            positive_keywords=pos_keywords,
                            negative_keywords=neg_keywords
                        )
                        created_count += 1

                    total_created += created_count
                    self.stdout.write(f'  [{i}/{total}] ✓ {dest.name}: +{created_count} reviews')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Lỗi: {e}'))
            return

        # Thống kê
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Hoàn thành!'
        ))
        self.stdout.write(f'   📝 Tạo mới: {total_created} reviews')
        self.stdout.write(f'   ⏭️ Bỏ qua: {skipped_count} địa điểm (đã đủ reviews)')
        self.stdout.write(f'   📊 Tổng reviews: {Review.objects.count()}')
        self.stdout.write('\n💡 Chạy tiếp: python manage.py calculate_scores')

    def _get_vietnamese_names(self):
        """Danh sách tên người Việt Nam"""
        return [
            'Nguyễn Văn An', 'Trần Thị Bình', 'Lê Văn Cường', 'Phạm Thị Dung',
            'Hoàng Văn Em', 'Vũ Thị Phương', 'Đỗ Văn Giang', 'Bùi Thị Hoa',
            'Đinh Văn Hùng', 'Mai Thị Kim', 'Phan Văn Long', 'Lý Thị Mai',
            'Trương Văn Nam', 'Võ Thị Oanh', 'Dương Văn Phúc', 'Ngô Thị Quỳnh',
            'Đặng Văn Sơn', 'Hồ Thị Tâm', 'Lương Văn Tuấn', 'Cao Thị Uyên',
            'Tạ Văn Vinh', 'Chu Thị Xuân', 'Vương Văn Yên', 'La Thị Zara',
            'Minh Anh', 'Thanh Tùng', 'Hải Yến', 'Quốc Bảo', 'Thùy Linh',
            'Đức Minh', 'Ngọc Ánh', 'Hoàng Nam', 'Thu Hà', 'Văn Đức',
            'Traveler_VN', 'Du khách 2024', 'Phượt thủ Sài Gòn', 'Backpacker HN',
        ]

    def _get_review_templates(self):
        """Templates review theo loại địa điểm"""
        return {
            'Biển': {
                'positive': [
                    'Bãi biển tuyệt đẹp, nước trong xanh như ngọc. Cát trắng mịn, rất sạch sẽ. Recommend!',
                    'View biển đẹp xuất sắc! Sóng êm, phù hợp tắm biển. Dịch vụ tốt, giá cả hợp lý.',
                    'Thiên đường biển! Hoàng hôn ở đây đẹp không tưởng. Sẽ quay lại nhiều lần nữa.',
                    'Biển đẹp, không khí trong lành. Hải sản tươi ngon, giá phải chăng. Rất thích!',
                    'Nơi nghỉ dưỡng lý tưởng. Bãi biển sạch, ít người. Yên tĩnh và thư giãn.',
                ],
                'neutral': [
                    'Biển đẹp nhưng hơi đông người vào cuối tuần. Nên đi ngày thường.',
                    'Ổn, cảnh đẹp. Tuy nhiên dịch vụ cần cải thiện thêm.',
                    'Bãi biển bình thường, không quá đặc biệt. Giá hơi cao.',
                ],
                'negative': [
                    'Biển bẩn, nhiều rác. Dịch vụ kém, giá đắt. Thất vọng!',
                    'Quá đông đúc, ồn ào. Không như hình ảnh quảng cáo.',
                ]
            },
            'Núi': {
                'positive': [
                    'Cảnh núi non hùng vĩ, không khí trong lành. Tuyệt vời cho những ai thích thiên nhiên!',
                    'View đẹp mê hồn! Biển mây bồng bềnh, khí hậu mát mẻ. Đáng để leo lên.',
                    'Phong cảnh tuyệt đẹp, yên bình. Rất thích hợp để nghỉ ngơi và thư giãn.',
                    'Núi non hùng vĩ, ruộng bậc thang đẹp. Người dân thân thiện, đồ ăn ngon.',
                ],
                'neutral': [
                    'Cảnh đẹp nhưng đường đi hơi khó. Cần chuẩn bị kỹ trước khi đi.',
                    'Ổn, view đẹp. Tuy nhiên thời tiết thất thường, cần theo dõi.',
                ],
                'negative': [
                    'Đường đi quá khó, không phù hợp người già và trẻ em.',
                    'Giá cáp treo đắt, dịch vụ không tương xứng.',
                ]
            },
            'Văn hóa': {
                'positive': [
                    'Di tích lịch sử tuyệt vời! Kiến trúc độc đáo, có giá trị văn hóa cao. Rất đáng tham quan.',
                    'Nơi này rất ấn tượng! Học được nhiều điều về lịch sử Việt Nam. Recommend!',
                    'Kiến trúc đẹp, không gian trang nghiêm. Hướng dẫn viên nhiệt tình, am hiểu.',
                    'Di sản văn hóa quý giá. Cần được bảo tồn và phát huy. Rất đáng để ghé thăm.',
                ],
                'neutral': [
                    'Địa điểm lịch sử quan trọng. Tuy nhiên cần cải thiện cơ sở vật chất.',
                    'Ổn, có giá trị văn hóa. Hơi đông vào cuối tuần.',
                ],
                'negative': [
                    'Xuống cấp nhiều, cần trùng tu. Giá vé cao so với những gì nhận được.',
                ]
            },
            'Sinh thái': {
                'positive': [
                    'Thiên nhiên hoang sơ, tuyệt đẹp! Không khí trong lành, nhiều loài động thực vật.',
                    'Trải nghiệm tuyệt vời giữa thiên nhiên. Rất thích hợp cho những ai yêu môi trường.',
                    'Cảnh quan đẹp, hệ sinh thái đa dạng. Đi xuồng xuyên rừng rất thú vị!',
                ],
                'neutral': [
                    'Cảnh đẹp nhưng muỗi nhiều. Nên mang theo thuốc chống muỗi.',
                    'Ổn, thiên nhiên đẹp. Tuy nhiên đường đi hơi khó.',
                ],
                'negative': [
                    'Không như mong đợi. Cần cải thiện dịch vụ và vệ sinh.',
                ]
            },
            'Thành phố': {
                'positive': [
                    'Thành phố sôi động, nhiều điều thú vị để khám phá. Ẩm thực đa dạng, ngon!',
                    'Nơi này rất đẹp, hiện đại. Nhiều hoạt động vui chơi giải trí. Recommend!',
                    'Không gian đẹp, sạch sẽ. Thích hợp đi dạo buổi tối. Rất thích!',
                ],
                'neutral': [
                    'Thành phố đông đúc, ồn ào. Tuy nhiên có nhiều điểm tham quan thú vị.',
                    'Ổn, có nhiều thứ để xem. Giao thông hơi phức tạp.',
                ],
                'negative': [
                    'Quá đông đúc, kẹt xe. Giá cả đắt đỏ.',
                ]
            },
            'Ẩm thực': {
                'positive': [
                    'Đồ ăn ngon tuyệt! Đa dạng món, giá cả hợp lý. Thiên đường ẩm thực!',
                    'Hải sản tươi ngon, chế biến đậm đà. Phục vụ nhanh, thân thiện. Recommend!',
                    'Ẩm thực đường phố tuyệt vời! Nhiều món đặc sản địa phương. Rất thích!',
                ],
                'neutral': [
                    'Đồ ăn ổn, giá hơi cao. Nên thử các quán địa phương thay vì quán du lịch.',
                ],
                'negative': [
                    'Giá chặt chém, đồ ăn không ngon như quảng cáo. Thất vọng!',
                ]
            },
            'Giải trí': {
                'positive': [
                    'Khu vui chơi tuyệt vời! Nhiều trò chơi hấp dẫn, phù hợp mọi lứa tuổi. Recommend!',
                    'Rất vui! Trẻ con thích mê. Dịch vụ tốt, nhân viên thân thiện.',
                    'Đáng đồng tiền bát gạo! Chơi cả ngày không chán. Sẽ quay lại!',
                ],
                'neutral': [
                    'Ổn, nhiều trò chơi. Tuy nhiên giá vé hơi cao, đông vào cuối tuần.',
                ],
                'negative': [
                    'Giá vé đắt, xếp hàng lâu. Một số trò chơi đang bảo trì.',
                ]
            },
            'default': {
                'positive': [
                    'Địa điểm rất đẹp, phong cảnh tuyệt vời. Rất đáng để đi!',
                    'Tôi rất thích nơi này. Mọi thứ đều tốt, giá cả hợp lý.',
                    'Trải nghiệm tuyệt vời! Sẽ quay lại lần sau.',
                    'Cảnh đẹp, không khí trong lành. Recommend cho mọi người!',
                    'Dịch vụ tốt, nhân viên thân thiện. Rất hài lòng.',
                ],
                'neutral': [
                    'Bình thường, không có gì đặc biệt.',
                    'Ổn, có thể đi thử một lần.',
                    'Giá hơi cao nhưng cảnh đẹp.',
                ],
                'negative': [
                    'Hơi đắt so với chất lượng. Không như mong đợi.',
                    'Thất vọng với dịch vụ. Cần cải thiện.',
                ]
            }
        }
