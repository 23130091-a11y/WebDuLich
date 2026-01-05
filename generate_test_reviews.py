"""
Generate 300 diverse test reviews for comprehensive evaluation
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.models import Destination, Review
from django.contrib.auth import get_user_model
import random

User = get_user_model()

# Template reviews với expected sentiment
REVIEW_TEMPLATES = [
    # POSITIVE (rating 4-5)
    ("Địa điểm tuyệt vời, rất đáng đi", 5, "P"),
    ("Cảnh đẹp xuất sắc, recommend mạnh", 5, "P"),
    ("View đỉnh cao, phục vụ nhiệt tình", 5, "P"),
    ("Rất hài lòng, sẽ quay lại", 5, "P"),
    ("Hoàn hảo, xứng đáng 5 sao", 5, "P"),
    ("Tuyệt đẹp, không thể bỏ lỡ", 5, "P"),
    ("Siêu đẹp, chụp hình cực xịn", 5, "P"),
    ("Đáng tiền, trải nghiệm tốt", 4, "P"),
    ("Khá ổn, cảnh đẹp, dịch vụ tốt", 4, "P"),
    ("Hài lòng với chuyến đi", 4, "P"),
    ("Nên đi, view đẹp lắm", 4, "P"),
    ("Địa điểm xinh, nhân viên dễ thương", 4, "P"),
    ("Phòng sạch sẽ, tiện nghi đầy đủ", 4, "P"),
    ("Giá hợp lý, đáng để trải nghiệm", 4, "P"),
    ("Không gian yên bình, thơ mộng", 4, "P"),
    
    # NEGATIVE (rating 1-2)
    ("Dịch vụ tệ, không bao giờ quay lại", 1, "N"),
    ("Bẩn quá, toilet hôi hám", 1, "N"),
    ("Chặt chém du khách, lừa đảo", 1, "N"),
    ("Thất vọng hoàn toàn, không như quảng cáo", 1, "N"),
    ("Giá trên trời, không đáng tiền", 1, "N"),
    ("Nhân viên thái độ kém, phục vụ tệ", 2, "N"),
    ("Quá đông, chen chúc, chờ lâu", 2, "N"),
    ("Cơ sở vật chất xuống cấp, hư hỏng nhiều", 2, "N"),
    ("Không sạch sẽ, mùi khó chịu", 2, "N"),
    ("Đắt mà chất lượng kém", 2, "N"),
    
    # NEUTRAL/MIXED (rating 3)
    ("Bình thường, không có gì đặc biệt", 3, "NEU"),
    ("Tạm ổn, giá hơi cao", 3, "NEU"),
    ("Ok thôi, cũng được", 3, "NEU"),
    ("Cảnh đẹp nhưng đông quá", 3, "NEU"),
    ("Phòng sạch nhưng wifi yếu", 3, "NEU"),
    ("Đồ ăn ngon nhưng giá hơi mắc", 3, "NEU"),
    ("View đẹp nhưng xa trung tâm", 3, "NEU"),
    ("Nhân viên thân thiện nhưng phòng cũ", 3, "NEU"),
    ("Giá rẻ nhưng cơ sở vật chất hơi kém", 3, "NEU"),
    ("Được, nhưng kỳ vọng cao hơn", 3, "NEU"),
]

# Variations để tạo diversity
POSITIVE_VARIATIONS = [
    "Địa điểm {adj}, {action}",
    "Cảnh {adj}, {service}",
    "View {adj}, {recommend}",
    "{adj} lắm, {action}",
    "Rất {adj}, {recommend}",
]

NEGATIVE_VARIATIONS = [
    "Dịch vụ {adj}, {action}",
    "{adj} quá, {complaint}",
    "Nhân viên {adj}, {service}",
    "Giá {adj}, {complaint}",
    "{facility} {adj}, {action}",
]

MIXED_VARIATIONS = [
    "{positive} nhưng {negative}",
    "{positive}, tuy nhiên {negative}",
    "{negative} nhưng {positive}",
    "Có {positive} và {negative}",
]

POSITIVE_ADJS = ["đẹp", "tuyệt vời", "xuất sắc", "hoàn hảo", "tốt", "xinh", "xịn", "đỉnh"]
NEGATIVE_ADJS = ["tệ", "kém", "bẩn", "đắt", "cũ", "hư", "xấu", "dơ"]
ACTIONS = ["sẽ quay lại", "recommend", "đáng đi", "nên thử", "đáng trải nghiệm"]
SERVICES = ["phục vụ tốt", "nhân viên thân thiện", "dịch vụ tốt", "hỗ trợ nhiệt tình"]
COMPLAINTS = ["không đáng tiền", "không recommend", "thất vọng", "không hài lòng"]
FACILITIES = ["Phòng", "Toilet", "Wifi", "Cơ sở vật chất"]

def generate_reviews(num_reviews=300):
    """Generate diverse test reviews"""
    destinations = list(Destination.objects.all()[:20])  # Use first 20 destinations
    
    if not destinations:
        print("No destinations found! Please import destinations first.")
        return
    
    reviews_created = 0
    
    # Generate from templates (repeat to reach 300)
    templates_needed = num_reviews // len(REVIEW_TEMPLATES) + 1
    
    for _ in range(templates_needed):
        for template, rating, expected_sent in REVIEW_TEMPLATES:
            if reviews_created >= num_reviews:
                break
            
            dest = random.choice(destinations)
            
            # Add some variations
            comment = template
            if random.random() < 0.3:  # 30% add prefix
                prefixes = ["Mình thấy ", "Theo mình ", "Cá nhân mình nghĩ ", ""]
                comment = random.choice(prefixes) + comment
            
            if random.random() < 0.2:  # 20% add suffix
                suffixes = [" nha", " nhé", " ạ", " luôn", ""]
                comment = comment + random.choice(suffixes)
            
            Review.objects.create(
                destination=dest,
                author_name=f"TestUser{reviews_created}",
                rating=rating,
                comment=comment,
                user_ip=f"192.168.1.{reviews_created % 255}",
            )
            
            reviews_created += 1
            
            if reviews_created % 50 == 0:
                print(f"Created {reviews_created}/{num_reviews} reviews...")
    
    print(f"\n✅ Successfully created {reviews_created} test reviews!")
    
    # Statistics
    print("\n📊 STATISTICS:")
    print(f"Rating 5: {Review.objects.filter(rating=5).count()}")
    print(f"Rating 4: {Review.objects.filter(rating=4).count()}")
    print(f"Rating 3: {Review.objects.filter(rating=3).count()}")
    print(f"Rating 2: {Review.objects.filter(rating=2).count()}")
    print(f"Rating 1: {Review.objects.filter(rating=1).count()}")

if __name__ == "__main__":
    print("=" * 60)
    print("GENERATING 300 TEST REVIEWS")
    print("=" * 60)
    
    # Check if test reviews already exist
    existing = Review.objects.filter(author_name__startswith="TestUser").count()
    if existing > 0:
        response = input(f"\n⚠️  Found {existing} existing test reviews. Delete them? (y/n): ")
        if response.lower() == 'y':
            Review.objects.filter(author_name__startswith="TestUser").delete()
            print(f"Deleted {existing} test reviews.")
    
    generate_reviews(300)
