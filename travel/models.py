# D:\LT_Python\PyWeb\DoAnWeb\WebDuLich\travel\models.py
from linecache import cache
from django.conf import settings
from django.db import models
import requests
from taggit.managers import TaggableManager
from django.utils.text import slugify
from django.conf import settings
from django.db.models import Q

from travel.services.nearby_service import get_nearby_hotels
from travel.services.nearby_service import get_nearby_restaurants
User = settings.AUTH_USER_MODEL

# ----------------------------------------------------------------------
# 1. Category Model
# ----------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)
    order = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categories"
        verbose_name_plural = "Categories"
        ordering = ['name']
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class TravelType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

# ----------------------------------------------------------------------
# 2. Destination Model
# ----------------------------------------------------------------------
from .services.nearby_service import get_nearby_hotels, get_nearby_restaurants
class Destination(models.Model):
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    is_popular = models.BooleanField(default=False)

    slug = models.SlugField(unique=True, max_length=200)
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")

    avg_price = models.DecimalField(
        max_digits=10, decimal_places=0, null=True, blank=True,
        verbose_name="Gia trung binh (VND)"
    )  # TRUNG BÌNH REVIEW

    # Rating tổng hợp từ review
    avg_rating = models.FloatField(default=0.0)

    # phục vụ cho bản đồ
    # Thong tin dia ly (tu B - cho weather/routing)
    latitude = models.FloatField(null=True, blank=True, verbose_name="Vi do")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Kinh do")

    # ===== THỜI GIAN =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    travel_type = models.ManyToManyField(
        TravelType,
        related_name='destinations',
        blank=True
    )

    class Meta:
        verbose_name = "Destination"
        verbose_name_plural = "Destination"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['location']),
            models.Index(fields=['avg_rating']),
            models.Index(fields=['is_popular']),
            models.Index(fields=['created_at']),
        ]

    @property
    def get_main_image(self):
        # Lấy tấm ảnh đầu tiên của destination này
        img = self.images.first() # self.images là related_name từ DestinationImage
        if img and img.image:
            return img.image.url
        return None

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_weather_data(self, lat, lon):
        if not lat or not lon:
            return {'error': 'Thiếu tọa độ'}

        # Sử dụng API Open-Meteo (Miễn phí, không cần API Key)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&timezone=auto"
        
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if "current" in data:
                current = data['current']
                return {
                    'is_current': True,
                    'temperature': current['temperature_2m'],
                    'windspeed': current['wind_speed_10m'],
                    'precipitation': current['precipitation'],
                    'weather_desc': 'Dữ liệu thực tế',
                    'icon': '🌡️',
                    'error': None
                }
            return {'error': 'Không có dữ liệu từ API'}
        except Exception as e:
            return {'error': f"Lỗi kết nối API: {str(e)}"}
        
    def get_hotels(self, lat, lon):
        return []

    def get_restaurants(self, lat, lon):
        return []
    
    def get_nearby_hotels_data(self):
        """Sử dụng logic từ service để trả về data cho template"""
        return get_nearby_hotels(self.latitude, self.longitude, self.name)

    def get_nearby_restaurants_data(self):
        """Sử dụng logic từ service để trả về data cho template"""
        return get_nearby_restaurants(self.latitude, self.longitude, self.name)

    def __str__(self):
        return self.name

# ----------------------------------------------------------------------
# 3. DestinationImage Model
# ----------------------------------------------------------------------
class DestinationImage(models.Model):
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='images'
    )

    image = models.ImageField(upload_to='destinations/images/', blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(default=0, verbose_name="Thu tu hien thi")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Image"
        verbose_name_plural = "Image"
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"Image for {self.destination.name}"

# ----------------------------------------------------------------------
# 4. TourPackage Model
# ----------------------------------------------------------------------
class TourPackage(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='tour_packages',
        null=True,
        blank=True
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='packages'
    )
    name = models.CharField(max_length=255)
    duration = models.IntegerField(help_text="Duration in days")
    average_rating = models.FloatField(default=5.0) 
    total_reviews = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    address_detail = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Địa chỉ đón/trả khách hoặc địa chỉ chính"
    )
    details = models.TextField(
        verbose_name="Chi tiết tour"
    )
    is_active = models.BooleanField(default=True)
    image_main = models.ImageField(
        upload_to='packages/main_images/',
        blank=True,
        null=True
    )
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    # slug:
    # /destination/da-nang/
    # /tour/ba-na-hills-1-ngay/
    is_available_today = models.BooleanField(
        default=False,
        help_text="Check nếu tour này khả dụng trong ngày hiện tại hoặc tương lai gần."
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    #vi tri 
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    meeting_point = models.CharField(max_length=255, blank=True, help_text="Địa điểm tập trung cụ thể")

    # Trạng thái nổi bật
    total_views = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['price']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def update_rating(self):
        reviews = self.reviews.filter(status='published')
        if reviews.exists():
            from django.db.models import Avg
            self.total_reviews = reviews.count()
            self.average_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        else:
            self.total_reviews = 0
            self.average_rating = 5.0
        self.save()

    def save(self, *args, **kwargs):
        # Nếu chưa gán category, tự động lấy từ destination
        if not self.category and self.destination and self.destination.category:
            self.category = self.destination.category

        # Nếu chưa có slug, tự động sinh từ name
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def get_nearby_data(self):
        lat = float(self.start_latitude) if self.start_latitude else self.destination.latitude
        lon = float(self.start_longitude) if self.start_longitude else self.destination.longitude

        return {
            'weather': self.destination.get_weather_data(lat, lon),
            'hotels': self.destination.get_hotels(lat, lon), # Sẽ không còn lỗi nữa
            'restaurants': self.destination.get_restaurants(lat, lon) # Sẽ không còn lỗi nữa
        }

    def get_similar_tours(self, limit=4):
        return TourPackage.objects.filter(
            Q(category=self.category) | Q(destination=self.destination), 
            is_active=True
        ).exclude(id=self.id).order_by('-average_rating')[:limit]

    def __str__(self):
        return f"{self.name} at {self.destination.name}"
    
    
class TourImage(models.Model):
    tour = models.ForeignKey(TourPackage, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='packages/gallery/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.tour.name}"

from django.contrib.contenttypes.fields import GenericRelation
class TourReview(models.Model):
    tour = models.ForeignKey(TourPackage, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) # Cho phép khách ẩn danh hoặc đã đăng nhập
    author_name = models.CharField(max_length=100, verbose_name="Tên người đánh giá")
    rating = models.IntegerField(default=5)
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Thêm cái này để làm tính năng Like/Hữu ích 
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)

    reports = GenericRelation('ReviewReport', related_query_name='tour_review')
    not_helpful_count = models.PositiveIntegerField(default=0, verbose_name="Không hữu ích")

    # Trạng thái xác minh
    is_verified_user = models.BooleanField(default=False, verbose_name="Tài khoản đã xác minh")
    is_verified_purchase = models.BooleanField(default=False, verbose_name="Khách đã trải nghiệm tour")
    
    # Thêm trạng thái để Admin có thể ẩn/hiện nhận xét
    STATUS_CHOICES = [
        ('pending', 'Chờ duyệt'),
        ('published', 'Đã hiển thị'),
        ('hidden', 'Đã ẩn (Vi phạm)'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author_name} - {self.tour.name} ({self.rating}*)"
    
from django.conf import settings

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('completed', 'Đã hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ]

    PAYMENT_STATUS = [
        ('unpaid', 'Chưa thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('refunded', 'Đã hoàn tiền'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    tour = models.ForeignKey(TourPackage, on_delete=models.CASCADE, related_name='bookings')
    
    # Thông tin khách hàng cung cấp khi đặt
    full_name = models.CharField(max_length=255, verbose_name="Họ tên người đặt")
    phone_number = models.CharField(max_length=20, verbose_name="Số điện thoại")
    email = models.EmailField()
    
    # Chi tiết tour đặt
    departure_date = models.DateField(verbose_name="Ngày khởi hành")
    number_of_adults = models.PositiveIntegerField(default=1, verbose_name="Số người lớn")
    number_of_children = models.PositiveIntegerField(default=0, verbose_name="Số trẻ em")
    
    # Tài chính
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    special_requests = models.TextField(blank=True, null=True, verbose_name="Yêu cầu đặc biệt")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='unpaid') 
    
    # THÊM MÃ ĐƠN HÀNG (Dùng để khách chuyển khoản ghi nội dung)
    booking_code = models.CharField(max_length=10, unique=True, editable=False, null=True)

    def save(self, *args, **kwargs):
        if not self.booking_code:
            import random, string
            # Vòng lặp đảm bảo mã booking_code không bị trùng lặp (unique)
            trong_he_thong = True
            while trong_he_thong:
                code = 'HH' + ''.join(random.choices(string.digits, k=6))
                if not Booking.objects.filter(booking_code=code).exists():
                    self.booking_code = code
                    trong_he_thong = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} - {self.tour.name} by {self.full_name}"
    
# Thanh
# ======================================================================
# 7. SearchHistory Model (tu Project B - giu nguyen)
# ======================================================================
class SearchHistory(models.Model):
    """Lich su tim kiem"""
    query = models.CharField(max_length=255, verbose_name="Tu khoa tim kiem")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='search_history',
        verbose_name="Nguoi dung"
    )
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lich su tim kiem"
        verbose_name_plural = "Lich su tim kiem"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='idx_search_created'),
            models.Index(fields=['query'], name='idx_search_query'),
            models.Index(fields=['user'], name='idx_search_user'),
        ]

    def __str__(self):
        return f"{self.query} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

# ======================================================================
# 5. Review Model (Enhanced for User-Generated Content)
# ======================================================================
class Review(models.Model):
    """Danh gia dia diem - Ho tro User-Generated Content"""

    # Review status choices
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Chờ duyệt'),
        (STATUS_APPROVED, 'Đã duyệt'),
        (STATUS_REJECTED, 'Từ chối'),
    ]

    # Core fields
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True
    )
   
    author_name = models.CharField(
        max_length=100,
        default="Anonymous"
    )
    rating = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        default=5,
        verbose_name="Đánh giá (1-5 sao)"
    )
    comment = models.TextField(
        blank=True,
        default=""
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    # User authentication (optional - cho phép cả guest và logged user)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name="Người dùng"
    )

    # Verification & Moderation
    is_verified = models.BooleanField(default=False, verbose_name="Đã xác minh")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_APPROVED,  # Auto-approve for now, can change to PENDING
        verbose_name="Trạng thái"
    )

    # User metadata (for spam detection)
    user_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP người dùng")
    user_agent = models.CharField(max_length=500, blank=True, verbose_name="User Agent")

    # Travel context (optional - để review có giá trị hơn)
    visit_date = models.DateField(null=True, blank=True, verbose_name="Ngày đi")
    travel_types = models.ForeignKey(
        TravelType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Loại chuyến đi")
    travel_with = models.CharField(max_length=50, blank=True, verbose_name="Đi cùng ai")

    # Phan tich sentiment (tu dong tinh)
    sentiment_score = models.FloatField(default=0.0, verbose_name="Điểm cảm xúc (-1 đến 1)")
    positive_keywords = models.JSONField(default=list, blank=True, verbose_name="Từ khóa tích cực")
    negative_keywords = models.JSONField(default=list, blank=True, verbose_name="Từ khóa tiêu cực")

    # Engagement metrics
    helpful_count = models.IntegerField(default=0, verbose_name="Số lượt hữu ích")
    not_helpful_count = models.IntegerField(default=0, verbose_name="Số lượt không hữu ích")
    report_count = models.IntegerField(default=0, verbose_name="Số lượt báo cáo")

    reports = GenericRelation('ReviewReport', related_query_name='normal_review')

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destination', '-created_at'], name='idx_review_dest_date'),
            models.Index(fields=['created_at'], name='idx_review_created'),
            models.Index(fields=['rating'], name='idx_review_rating'),
            models.Index(fields=['status'], name='idx_review_status'),
            models.Index(fields=['user'], name='idx_review_user'),
            models.Index(fields=['-helpful_count'], name='idx_review_helpful'),
        ]

    def __str__(self):
        verified = "✓" if self.is_verified else ""
        return f"{self.author_name}{verified} - {self.destination.name} ({self.rating} sao)"

    @property
    def is_user_review(self):
        """Check if review is from logged-in user"""
        return self.user is not None

    @property
    def helpfulness_score(self):
        """Calculate helpfulness percentage"""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0
        return round((self.helpful_count / total) * 100)


# ======================================================================
# 5.1 ReviewVote Model - Tracking user votes on reviews
# ======================================================================
class ReviewVote(models.Model):
    """Tracking votes on reviews (helpful/not helpful)"""
    VOTE_HELPFUL = 'helpful'
    VOTE_NOT_HELPFUL = 'not_helpful'
    VOTE_CHOICES = [
        (VOTE_HELPFUL, 'Hữu ích'),
        (VOTE_NOT_HELPFUL, 'Không hữu ích'),
    ]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes', null=True, blank=True)
    tour_review = models.ForeignKey(TourReview, on_delete=models.CASCADE, related_name='votes', null=True, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    vote_type = models.CharField(max_length=20, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Ràng buộc cho Destination Review
            models.UniqueConstraint(
                fields=['review', 'user'],
                condition=~models.Q(user=None) & ~models.Q(review=None),
                name='unique_user_vote'
            ),
            # Ràng buộc cho Tour Review
            models.UniqueConstraint(
                fields=['tour_review', 'user'],
                condition=~models.Q(user=None) & ~models.Q(tour_review=None),
                name='unique_user_tour_vote'
            ),
        ]

    def __str__(self):
        target = f"Review #{self.review.id}" if self.review else f"TourReview #{self.tour_review.id}"
        return f"{self.vote_type} - {target}"


# ======================================================================
# 5.2 ReviewReport Model - Report inappropriate reviews
# ======================================================================
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
class ReviewReport(models.Model):
    """Report inappropriate reviews"""

    REASON_SPAM = 'spam'
    REASON_INAPPROPRIATE = 'inappropriate'
    REASON_FAKE = 'fake'
    REASON_OTHER = 'other'
    REASON_CHOICES = [
        (REASON_SPAM, 'Spam/Quảng cáo'),
        (REASON_INAPPROPRIATE, 'Nội dung không phù hợp'),
        (REASON_FAKE, 'Đánh giá giả'),
        (REASON_OTHER, 'Lý do khác'),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    review_object = GenericForeignKey('content_type', 'object_id')

    reporter_ip = models.GenericIPAddressField()
    reporter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(blank=True, verbose_name="Mô tả chi tiết")
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Báo cáo đánh giá"
        verbose_name_plural = "Báo cáo đánh giá"
        # Index để tìm kiếm nhanh hơn
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"Report: {self.reason} - {self.review_object}"


# ======================================================================
# Bảng RecommendationScore phục vụ AI tính điểm và gợi ý
# ======================================================================
class RecommendationScore(models.Model):
    destination = models.OneToOneField(
        'Destination', on_delete=models.CASCADE, 
        related_name='recommendation', null=True, blank=True
    )
    tour = models.OneToOneField(
        'TourPackage', on_delete=models.CASCADE, 
        related_name='recommendation', null=True, blank=True
    )

    overall_score = models.FloatField(default=0.0, verbose_name="Điểm tổng thể (0-100)")
    popularity_score = models.FloatField(default=0.0, verbose_name="Điểm phổ biến")
    sentiment_score = models.FloatField(default=0.0, verbose_name="Điểm cảm xúc")
    positive_review_ratio = models.FloatField(default=0.0, verbose_name="Tỷ lệ đánh giá tích cực")

    avg_rating = models.FloatField(default=0.0)
    total_reviews = models.IntegerField(default=0)
    last_calculated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Điểm gợi ý"
        verbose_name_plural = "Điểm gợi ý"
        ordering = ['-overall_score']
        indexes = [
            models.Index(fields=['-overall_score']),
        ]

    def __str__(self):
        obj = self.destination or self.tour
        return f"{obj.name if obj else 'Chưa xác định'} - {self.overall_score}"



# 7.Account Profile
class AccountProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)

    birthday = models.DateField(null=True, blank=True)
    profession = models.CharField(max_length=100, blank=True, null=True)

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return self.user.username

# Tạo model Favorite
class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_tours"
    )
    tour = models.ForeignKey(
        TourPackage,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        null=True,   # giữ lại
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "tour")

    def __str__(self):
        return f"{self.user} thích {self.tour.name}"


class FavoriteDestination(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_destinations"
    )
    destination = models.ForeignKey(
        'Destination',  # Đảm bảo tên model Destination chính xác
        on_delete=models.CASCADE,
        related_name="favorited_by_users"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Đảm bảo một người dùng không thể yêu thích một địa điểm 2 lần
        unique_together = ("user", "destination")

    def __str__(self):
        return f"{self.user} thích {self.destination.name}"
    
