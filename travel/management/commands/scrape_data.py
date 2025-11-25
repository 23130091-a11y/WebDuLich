# Script cào dữ liệu mẫu (Mock Data)
# Trong thực tế, bạn có thể dùng BeautifulSoup hoặc Selenium để cào từ web

from django.core.management.base import BaseCommand
from travel.models import Destination, Review
from travel.ai_module import analyze_sentiment
import random

class Command(BaseCommand):
    help = 'Tạo dữ liệu mẫu cho hệ thống'

    def handle(self, *args, **kwargs):
        self.stdout.write('Bắt đầu tạo dữ liệu mẫu...')
        
        # Dữ liệu địa điểm mẫu
        destinations_data = [
            {
                'name': 'Vịnh Hạ Long',
                'travel_type': 'Biển',
                'location': 'Quảng Ninh',
                'address': 'TP. Hạ Long, Quảng Ninh',
                'description': 'Di sản thiên nhiên thế giới với hàng nghìn đảo đá vôi kỳ vĩ',
                'latitude': 20.9101,
                'longitude': 107.1839,
                'avg_price': 1500000
            },
            {
                'name': 'Phố Cổ Hội An',
                'travel_type': 'Văn hóa',
                'location': 'Quảng Nam',
                'address': 'TP. Hội An, Quảng Nam',
                'description': 'Phố cổ với kiến trúc độc đáo, đèn lồng rực rỡ',
                'latitude': 15.8801,
                'longitude': 108.3380,
                'avg_price': 800000
            },
            {
                'name': 'Đà Lạt',
                'travel_type': 'Núi',
                'location': 'Lâm Đồng',
                'address': 'TP. Đà Lạt, Lâm Đồng',
                'description': 'Thành phố ngàn hoa với khí hậu mát mẻ quanh năm',
                'latitude': 11.9404,
                'longitude': 108.4583,
                'avg_price': 1000000
            },
            {
                'name': 'Phú Quốc',
                'travel_type': 'Biển',
                'location': 'Kiên Giang',
                'address': 'Đảo Phú Quốc, Kiên Giang',
                'description': 'Đảo ngọc với bãi biển đẹp và hải sản tươi ngon',
                'latitude': 10.2899,
                'longitude': 103.9840,
                'avg_price': 2000000
            },
            {
                'name': 'Sapa',
                'travel_type': 'Núi',
                'location': 'Lào Cai',
                'address': 'Huyện Sa Pa, Lào Cai',
                'description': 'Ruộng bậc thang tuyệt đẹp và văn hóa dân tộc đa dạng',
                'latitude': 22.3364,
                'longitude': 103.8438,
                'avg_price': 1200000
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
            created_destinations.append(dest)
        
        # Dữ liệu review mẫu
        review_templates = {
            'positive': [
                'Địa điểm rất đẹp, phong cảnh tuyệt vời. Rất đáng để đi!',
                'Tôi rất thích nơi này. Mọi thứ đều tốt, giá cả hợp lý.',
                'Trải nghiệm tuyệt vời! Sẽ quay lại lần sau.',
                'Cảnh đẹp, không khí trong lành. Recommend cho mọi người!',
                'Dịch vụ tốt, nhân viên thân thiện. Rất hài lòng.',
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
        
        # Tạo reviews cho mỗi destination
        for dest in created_destinations:
            num_reviews = random.randint(10, 30)
            
            for i in range(num_reviews):
                # Random sentiment type
                sentiment_type = random.choices(
                    ['positive', 'neutral', 'negative'],
                    weights=[0.6, 0.25, 0.15]  # 60% positive, 25% neutral, 15% negative
                )[0]
                
                comment = random.choice(review_templates[sentiment_type])
                
                # Rating tương ứng với sentiment
                if sentiment_type == 'positive':
                    rating = random.randint(4, 5)
                elif sentiment_type == 'neutral':
                    rating = 3
                else:
                    rating = random.randint(1, 2)
                
                # Phân tích sentiment
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
        
        self.stdout.write(self.style.SUCCESS('\n✅ Hoàn thành tạo dữ liệu mẫu!'))
