"""
Script crawl đơn giản sử dụng requests + BeautifulSoup
Crawl từ các trang review công khai (ít bị chặn hơn)
"""

from django.core.management.base import BaseCommand
from travel.models import Destination, Review
from travel.ai_module import analyze_sentiment
import requests
from bs4 import BeautifulSoup
import time
import random

class Command(BaseCommand):
    help = 'Crawl đánh giá đơn giản (không cần Selenium)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--destination-id',
            type=int,
            help='ID của địa điểm cần crawl reviews'
        )
        parser.add_argument(
            '--source',
            type=str,
            default='demo',
            choices=['demo', 'foody', 'tripadvisor'],
            help='Nguồn crawl: demo (dữ liệu mẫu), foody, tripadvisor'
        )

    def handle(self, *args, **options):
        destination_id = options.get('destination_id')
        source = options.get('source')

        if not destination_id:
            self.stdout.write(self.style.ERROR(
                '❌ Vui lòng chỉ định --destination-id\n'
                'VD: python manage.py crawl_simple --destination-id=1 --source=demo'
            ))
            return

        try:
            destination = Destination.objects.get(id=destination_id)
        except Destination.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Không tìm thấy địa điểm với ID {destination_id}'))
            return

        self.stdout.write(f'🔍 Crawl reviews cho: {destination.name}')
        self.stdout.write(f'📍 Nguồn: {source}')

        if source == 'demo':
            self._crawl_demo_data(destination)
        elif source == 'foody':
            self._crawl_foody(destination)
        elif source == 'tripadvisor':
            self._crawl_tripadvisor(destination)

    def _crawl_demo_data(self, destination):
        """Tạo dữ liệu demo chất lượng cao (giả lập crawl thật)"""
        self.stdout.write('📝 Tạo dữ liệu demo chất lượng cao...')

        # Dữ liệu review chân thực hơn
        reviews_data = [
            {
                'author': 'Nguyễn Văn A',
                'rating': 5,
                'comment': 'Địa điểm rất đẹp và ấn tượng. Tôi đã có một chuyến đi tuyệt vời cùng gia đình. Phong cảnh thơ mộng, không khí trong lành. Giá vé hợp lý, nhân viên thân thiện. Rất recommend!'
            },
            {
                'author': 'Trần Thị B',
                'rating': 4,
                'comment': 'Nơi này khá đẹp, phù hợp để chụp ảnh. Tuy nhiên vào cuối tuần hơi đông người. Nên đi vào buổi sáng sớm để tránh đông đúc. Nhìn chung là một trải nghiệm tốt.'
            },
            {
                'author': 'Lê Văn C',
                'rating': 5,
                'comment': 'Tuyệt vời! Kiến trúc độc đáo, có nhiều góc đẹp để check-in. Dịch vụ tốt, khu vực sạch sẽ. Sẽ quay lại lần sau và giới thiệu cho bạn bè.'
            },
            {
                'author': 'Phạm Thị D',
                'rating': 3,
                'comment': 'Ổn, không quá đặc biệt nhưng cũng đáng để ghé thăm một lần. Giá hơi cao so với những gì nhận được. Có thể cải thiện thêm về cơ sở vật chất.'
            },
            {
                'author': 'Hoàng Văn E',
                'rating': 5,
                'comment': 'Cảnh đẹp tuyệt vời, không khí trong lành. Rất thích hợp cho những ai muốn tìm một nơi yên tĩnh để thư giãn. View đẹp, phục vụ chu đáo.'
            },
            {
                'author': 'Vũ Thị F',
                'rating': 4,
                'comment': 'Địa điểm đẹp, phù hợp đi cùng gia đình. Có nhiều hoạt động thú vị. Tuy nhiên bãi đỗ xe hơi nhỏ, khó tìm chỗ vào giờ cao điểm.'
            },
            {
                'author': 'Đỗ Văn G',
                'rating': 5,
                'comment': 'Rất hài lòng với chuyến đi này. Mọi thứ đều tốt từ cảnh quan đến dịch vụ. Giá cả hợp lý, đáng đồng tiền bát gạo. Chắc chắn sẽ quay lại!'
            },
            {
                'author': 'Bùi Thị H',
                'rating': 2,
                'comment': 'Hơi thất vọng. Kỳ vọng cao hơn sau khi đọc reviews. Thực tế không như hình ảnh quảng cáo. Giá hơi đắt, cần cải thiện chất lượng dịch vụ.'
            },
            {
                'author': 'Đinh Văn I',
                'rating': 4,
                'comment': 'Nơi này khá ok, phong cảnh đẹp. Thích hợp để đi chơi cuối tuần. Có một số điểm cần cải thiện nhưng nhìn chung là tốt.'
            },
            {
                'author': 'Mai Thị K',
                'rating': 5,
                'comment': 'Tuyệt vời! Đây là một trong những địa điểm đẹp nhất tôi từng đến. Cảnh quan hùng vĩ, không khí trong lành. Nhân viên nhiệt tình, chu đáo. Highly recommended!'
            },
            {
                'author': 'Phan Văn L',
                'rating': 4,
                'comment': 'Địa điểm đẹp, view tuyệt vời. Giá vé hợp lý. Tuy nhiên đồ ăn uống hơi đắt. Nên mang theo đồ ăn nhẹ nếu đi cả ngày.'
            },
            {
                'author': 'Lý Thị M',
                'rating': 5,
                'comment': 'Quá tuyệt vời! Không gian rộng rãi, thoáng mát. Rất nhiều điểm check-in đẹp. Phù hợp cho cả gia đình và nhóm bạn. Sẽ quay lại nhiều lần nữa!'
            },
            {
                'author': 'Trương Văn N',
                'rating': 3,
                'comment': 'Bình thường, không có gì quá đặc biệt. Có thể ghé qua nếu đang ở gần. Giá cả chấp nhận được nhưng trải nghiệm chưa thực sự ấn tượng.'
            },
            {
                'author': 'Võ Thị O',
                'rating': 5,
                'comment': 'Địa điểm tuyệt đẹp! Kiến trúc độc đáo, có giá trị lịch sử. Nhân viên thân thiện, nhiệt tình hướng dẫn. Rất đáng để tham quan và tìm hiểu.'
            },
            {
                'author': 'Dương Văn P',
                'rating': 4,
                'comment': 'Nơi này khá đẹp và yên tĩnh. Thích hợp để đi vào các ngày trong tuần, tránh cuối tuần vì sẽ rất đông. Giá vé hợp lý, dịch vụ tốt.'
            },
        ]

        # Thêm thêm reviews ngẫu nhiên
        additional_comments = [
            'Cảnh đẹp, không khí trong lành. Rất thích hợp để thư giãn.',
            'Địa điểm tuyệt vời, phù hợp cho cả gia đình.',
            'View đẹp, dịch vụ tốt. Sẽ quay lại lần sau.',
            'Khá ổn, giá cả hợp lý. Đáng để thử một lần.',
            'Rất hài lòng với chuyến đi này. Recommend!',
            'Nơi này đẹp nhưng hơi đông người vào cuối tuần.',
            'Trải nghiệm tốt, nhân viên thân thiện.',
            'Cảnh quan đẹp, không gian thoáng mát.',
            'Giá hơi cao nhưng chất lượng tốt.',
            'Địa điểm lý tưởng để chụp ảnh và check-in.',
        ]

        for i, comment in enumerate(additional_comments):
            reviews_data.append({
                'author': f'Du khách {i+16}',
                'rating': random.choice([3, 4, 4, 5, 5]),  # Bias về positive
                'comment': comment
            })

        # Lưu vào database
        created_count = 0
        for review_data in reviews_data:
            # Kiểm tra duplicate
            existing = Review.objects.filter(
                destination=destination,
                author_name=review_data['author'],
                comment=review_data['comment']
            ).exists()

            if not existing:
                sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(review_data['comment'])
                
                Review.objects.create(
                    destination=destination,
                    author_name=review_data['author'],
                    rating=review_data['rating'],
                    comment=review_data['comment'],
                    sentiment_score=sentiment_score,
                    positive_keywords=pos_keywords,
                    negative_keywords=neg_keywords
                )
                created_count += 1
                self.stdout.write(f"  ✓ {review_data['author']}: {review_data['rating']}⭐")

        self.stdout.write(self.style.SUCCESS(f'\n✅ Đã tạo {created_count} reviews!'))
        self.stdout.write('💡 Chạy: python manage.py calculate_scores')

    def _crawl_foody(self, destination):
        """Crawl từ Foody.vn (chỉ demo, cần điều chỉnh selector)"""
        self.stdout.write(self.style.WARNING(
            '⚠️ Foody crawling chưa được implement đầy đủ.\n'
            'Cần phân tích cấu trúc HTML của Foody và có thể cần xử lý anti-crawl.'
        ))

    def _crawl_tripadvisor(self, destination):
        """Crawl từ TripAdvisor (chỉ demo, cần điều chỉnh)"""
        self.stdout.write(self.style.WARNING(
            '⚠️ TripAdvisor có chống crawl mạnh, cần sử dụng Selenium hoặc API.\n'
            'Khuyến nghị sử dụng TripAdvisor Content API (có phí).'
        ))
