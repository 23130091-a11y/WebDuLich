# Script thêm dữ liệu cho TP.HCM và các địa điểm cụ thể

from django.core.management.base import BaseCommand
from travel.models import Destination, Review
from travel.ai_module import analyze_sentiment
import random

class Command(BaseCommand):
    help = 'Thêm dữ liệu địa điểm TP.HCM và các địa điểm cụ thể'

    def handle(self, *args, **kwargs):
        self.stdout.write('Bắt đầu thêm dữ liệu...')
        
        # Dữ liệu địa điểm TP.HCM và các tỉnh khác
        destinations_data = [
            # TP Hồ Chí Minh
            {
                'name': 'Nhà thờ Đức Bà',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '01 Công xã Paris, Bến Nghé, Quận 1',
                'description': 'Nhà thờ Công giáo La Mã nổi tiếng với kiến trúc Gothic độc đáo, được xây dựng từ năm 1863-1880',
                'latitude': 10.7797,
                'longitude': 106.6990,
                'avg_price': 0
            },
            {
                'name': 'Bến Nhà Rồng',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '01 Nguyễn Tất Thành, Phường 12, Quận 4',
                'description': 'Bến cảng lịch sử nơi Chủ tịch Hồ Chí Minh ra đi tìm đường cứu nước năm 1911',
                'latitude': 10.7676,
                'longitude': 106.7073,
                'avg_price': 0
            },
            {
                'name': 'Dinh Độc Lập',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '135 Nam Kỳ Khởi Nghĩa, Phường Bến Thành, Quận 1',
                'description': 'Di tích lịch sử quan trọng, nơi diễn ra sự kiện lịch sử 30/4/1975',
                'latitude': 10.7769,
                'longitude': 106.6955,
                'avg_price': 40000
            },
            {
                'name': 'Chợ Bến Thành',
                'travel_type': 'Ẩm thực',
                'location': 'TP Hồ Chí Minh',
                'address': 'Lê Lợi, Phường Bến Thành, Quận 1',
                'description': 'Chợ truyền thống nổi tiếng với đa dạng hàng hóa và ẩm thực đường phố',
                'latitude': 10.7720,
                'longitude': 106.6981,
                'avg_price': 200000
            },
            {
                'name': 'Phố đi bộ Nguyễn Huệ',
                'travel_type': 'Thành phố',
                'location': 'TP Hồ Chí Minh',
                'address': 'Đường Nguyễn Huệ, Quận 1',
                'description': 'Không gian đi bộ hiện đại với nhiều hoạt động văn hóa nghệ thuật',
                'latitude': 10.7743,
                'longitude': 106.7012,
                'avg_price': 0
            },
            {
                'name': 'Bảo tàng Chứng tích Chiến tranh',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '28 Võ Văn Tần, Phường 6, Quận 3',
                'description': 'Bảo tàng lưu giữ những chứng tích về chiến tranh Việt Nam',
                'latitude': 10.7797,
                'longitude': 106.6918,
                'avg_price': 40000
            },
            
            # Hà Nội
            {
                'name': 'Chùa Một Cột',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': 'Ông Ích Khiêm, Ba Đình',
                'description': 'Ngôi chùa cổ kính với kiến trúc độc đáo, được xây dựng từ năm 1049',
                'latitude': 21.0364,
                'longitude': 105.8336,
                'avg_price': 0
            },
            {
                'name': 'Hồ Hoàn Kiếm',
                'travel_type': 'Thành phố',
                'location': 'Hà Nội',
                'address': 'Quận Hoàn Kiếm',
                'description': 'Hồ nước ngọt nằm ở trung tâm Hà Nội, biểu tượng của thủ đô',
                'latitude': 21.0285,
                'longitude': 105.8542,
                'avg_price': 0
            },
            {
                'name': 'Văn Miếu Quốc Tử Giám',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': '58 Quốc Tử Giám, Đống Đa',
                'description': 'Trường đại học đầu tiên của Việt Nam, di sản văn hóa thế giới',
                'latitude': 21.0277,
                'longitude': 105.8355,
                'avg_price': 30000
            },
            
            # Đà Nẵng
            {
                'name': 'Cầu Rồng',
                'travel_type': 'Thành phố',
                'location': 'Đà Nẵng',
                'address': 'Cầu Rồng, Sông Hàn',
                'description': 'Cầu biểu tượng của Đà Nẵng với hình dáng con rồng phun lửa và nước',
                'latitude': 16.0544,
                'longitude': 108.2272,
                'avg_price': 0
            },
            {
                'name': 'Bà Nà Hills',
                'travel_type': 'Núi',
                'location': 'Đà Nẵng',
                'address': 'Hòa Ninh, Hòa Vang',
                'description': 'Khu du lịch nghỉ dưỡng trên núi với cầu Vàng nổi tiếng',
                'latitude': 15.9959,
                'longitude': 107.9953,
                'avg_price': 750000
            },
            {
                'name': 'Bãi biển Mỹ Khê',
                'travel_type': 'Biển',
                'location': 'Đà Nẵng',
                'address': 'Phường Phước Mỹ, Quận Sơn Trà',
                'description': 'Một trong những bãi biển đẹp nhất thế giới theo Forbes',
                'latitude': 16.0471,
                'longitude': 108.2425,
                'avg_price': 0
            },
        ]
        
        # Tạo destinations
        created_destinations = []
        for data in destinations_data:
            dest, created = Destination.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'✓ Tạo địa điểm: {dest.name}')
            else:
                self.stdout.write(f'  Đã tồn tại: {dest.name}')
            created_destinations.append(dest)
        
        # Dữ liệu review mẫu
        review_templates = {
            'positive': [
                'Địa điểm rất đẹp, phong cảnh tuyệt vời. Rất đáng để đi!',
                'Tôi rất thích nơi này. Mọi thứ đều tốt, giá cả hợp lý.',
                'Trải nghiệm tuyệt vời! Sẽ quay lại lần sau.',
                'Cảnh đẹp, không khí trong lành. Recommend cho mọi người!',
                'Dịch vụ tốt, nhân viên thân thiện. Rất hài lòng.',
                'Nơi này thật sự tuyệt vời, đáng để ghé thăm.',
                'Kiến trúc đẹp, có nhiều điều thú vị để khám phá.',
                'Rất ấn tượng với nơi này, sẽ giới thiệu cho bạn bè.',
            ],
            'negative': [
                'Hơi đắt so với chất lượng. Không như mong đợi.',
                'Bẩn và ồn ào. Không nên đi vào cuối tuần.',
                'Thất vọng với dịch vụ. Thái độ nhân viên không tốt.',
                'Giá cả chặt chém, không đáng tiền.',
                'Cũ kỹ, cần cải tạo lại. Không recommend.',
            ],
            'neutral': [
                'Bình thường, không có gì đặc biệt.',
                'Ổn, có thể đi thử một lần.',
                'Giá hơi cao nhưng cảnh đẹp.',
                'Có điểm tốt và điểm chưa tốt.',
                'Được, nhưng có thể tốt hơn.',
            ]
        }
        
        # Tạo reviews cho mỗi destination mới
        for dest in created_destinations:
            # Kiểm tra xem đã có review chưa
            existing_reviews = Review.objects.filter(destination=dest).count()
            if existing_reviews > 0:
                continue
                
            num_reviews = random.randint(15, 35)
            
            for i in range(num_reviews):
                sentiment_type = random.choices(
                    ['positive', 'neutral', 'negative'],
                    weights=[0.65, 0.25, 0.10]
                )[0]
                
                comment = random.choice(review_templates[sentiment_type])
                
                if sentiment_type == 'positive':
                    rating = random.randint(4, 5)
                elif sentiment_type == 'neutral':
                    rating = 3
                else:
                    rating = random.randint(1, 2)
                
                sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(comment)
                
                Review.objects.create(
                    destination=dest,
                    author_name=f'User{i+1}',
                    rating=rating,
                    comment=comment,
                    sentiment_score=sentiment_score,
                    positive_keywords=pos_keywords,
                    negative_keywords=neg_keywords
                )
            
            self.stdout.write(f'  ✓ Tạo {num_reviews} reviews cho {dest.name}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Hoàn thành thêm dữ liệu!'))
        self.stdout.write('Chạy lệnh: python manage.py calculate_scores để tính điểm gợi ý')
