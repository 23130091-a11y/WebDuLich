from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()


from django.db import models
from django.utils.text import slugify

# ======================================================================
# 1. Category Model - Danh mục (Biển, Núi, Nghỉ dưỡng...)
# ======================================================================
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên danh mục")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug URL")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    icon = models.CharField(max_length=50, blank=True, verbose_name="Icon class")
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ======================================================================
# 2. Destination Model - Địa danh (Vịnh Hạ Long, Phú Quốc...)
# ======================================================================
class Destination(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='destinations', verbose_name="Danh mục"
    )
    name = models.CharField(max_length=200, verbose_name="Tên địa điểm")
    travel_type = models.CharField(max_length=50, verbose_name="Loại hình du lịch")
    location = models.CharField(max_length=100, verbose_name="Vị trí")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ chi tiết")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    image = models.ImageField(upload_to='destinations/', blank=True)
    
    latitude = models.FloatField(null=True, blank=True, verbose_name="Vĩ độ")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Kinh độ")
    avg_price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="Giá TB (VND)")
    
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    rating = models.FloatField(default=0.0, verbose_name="Đánh giá")
    is_popular = models.BooleanField(default=False, verbose_name="Địa điểm nổi bật")
    slug = models.SlugField(max_length=200, unique=True, null=True, blank=True, verbose_name="Slug URL")
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Địa điểm"
        verbose_name_plural = "Địa điểm"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ======================================================================
# 3. DestinationImage Model - Thư viện ảnh cho Địa danh
# ======================================================================
class DestinationImage(models.Model):
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField(upload_to='destinations/images/', blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chú thích")
    order = models.IntegerField(default=0, verbose_name="Thứ tự hiển thị")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ảnh địa điểm"
        verbose_name_plural = "Ảnh địa điểm"
        ordering = ['order', '-created_at']


# ======================================================================
# 4. TourPackage Model - Các gói Tour cụ thể (Tour 3 ngày 2 đêm...)
# ======================================================================
class TourPackage(models.Model):
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name='packages', verbose_name="Địa điểm"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='tour_packages', verbose_name="Danh mục"
    )
    name = models.CharField(max_length=255, verbose_name="Tên tour")
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    details = models.TextField(verbose_name="Chi tiết tour")
    price = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True, verbose_name="Giá (VND)")
    duration = models.IntegerField(help_text="Số ngày", verbose_name="Thời lượng")
    
    image_main = models.ImageField(upload_to='packages/main_images/', blank=True, null=True, verbose_name="Ảnh chính")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    is_available_today = models.BooleanField(default=False, verbose_name="Có sẵn hôm nay")
    
    start_date = models.DateField(null=True, blank=True, verbose_name="Ngày bắt đầu")
    end_date = models.DateField(null=True, blank=True, verbose_name="Ngày kết thúc")
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")

    # 1. Điểm đánh giá (Rating)
    average_rating = models.FloatField(default=5.0) 
    total_reviews = models.IntegerField(default=0)

    # 2. Vị trí cụ thể của Tour (Dùng cho bản đồ)
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    meeting_point = models.CharField(max_length=255, blank=True, help_text="Địa điểm tập trung cụ thể")

    # 3. Yêu thích (Mối quan hệ Many-to-Many với User)
    favorites = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='favorite_tours', 
        blank=True
    )

    # 4. Trạng thái nổi bật
    total_views = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Gói tour"
        verbose_name_plural = "Gói tour"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.destination.name}"

    def save(self, *args, **kwargs):
        # Tự động đồng bộ Category từ Địa danh sang Tour nếu chưa chọn
        if not self.category and self.destination:
            self.category = self.destination.category
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


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
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='reviews')
    author_name = models.CharField(max_length=100, verbose_name="Tên người đánh giá")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="Đánh giá (1-5 sao)")
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True)
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
    travel_type = models.CharField(max_length=50, blank=True, verbose_name="Loại chuyến đi")
    travel_with = models.CharField(max_length=50, blank=True, verbose_name="Đi cùng ai")
    
    # Phan tich sentiment (tu dong tinh)
    sentiment_score = models.FloatField(default=0.0, verbose_name="Điểm cảm xúc (-1 đến 1)")
    positive_keywords = models.JSONField(default=list, blank=True, verbose_name="Từ khóa tích cực")
    negative_keywords = models.JSONField(default=list, blank=True, verbose_name="Từ khóa tiêu cực")
    
    # Engagement metrics
    helpful_count = models.IntegerField(default=0, verbose_name="Số lượt hữu ích")
    not_helpful_count = models.IntegerField(default=0, verbose_name="Số lượt không hữu ích")
    report_count = models.IntegerField(default=0, verbose_name="Số lượt báo cáo")

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
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='votes')
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
        verbose_name = "Vote đánh giá"
        verbose_name_plural = "Vote đánh giá"
        # Mỗi user/IP chỉ vote 1 lần cho mỗi review
        unique_together = [
            ('review', 'user'),
        ]
    
    def __str__(self):
        return f"{self.vote_type} - Review #{self.review.id}"


# ======================================================================
# 5.2 ReviewReport Model - Report inappropriate reviews
# ======================================================================
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
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
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
    
    def __str__(self):
        return f"Report: {self.reason} - Review #{self.review.id}"


# ======================================================================
# 6. RecommendationScore Model (tu Project B - giu nguyen)
# ======================================================================
class RecommendationScore(models.Model):
    """Diem goi y (Pre-calculated)"""
    destination = models.OneToOneField(Destination, on_delete=models.CASCADE, related_name='score_stats')

    # Cac chi so danh gia
    overall_score = models.FloatField(default=0.0, verbose_name="Diem tong the (0-100)")
    review_score = models.FloatField(default=0.0, verbose_name="Diem tu danh gia")
    sentiment_score = models.FloatField(default=0.0, verbose_name="Diem cam xuc")
    popularity_score = models.FloatField(default=0.0, verbose_name="Diem pho bien")

    # Thong ke
    total_reviews = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0.0)
    positive_review_ratio = models.FloatField(default=0.0, verbose_name="Ty le danh gia tich cuc")

    # Metadata
    last_calculated = models.DateTimeField(auto_now=True, verbose_name="Lan tinh cuoi")

    class Meta:
        verbose_name = "Diem goi y"
        verbose_name_plural = "Diem goi y"
        ordering = ['-overall_score']
        indexes = [
            models.Index(fields=['-overall_score'], name='idx_rec_score'),
            models.Index(fields=['-avg_rating'], name='idx_rec_rating'),
            models.Index(fields=['-total_reviews'], name='idx_rec_reviews'),
        ]

    def __str__(self):
        return f"{self.destination.name} - Score: {self.overall_score:.2f}"


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
# Trong file models.py của app travel
class DestinationRecommendation(models.Model):
    # Dòng này cực kỳ quan trọng: thêm related_name='recommendation'
    destination = models.OneToOneField(
        'Destination', 
        on_delete=models.CASCADE, 
        related_name='destination_stats' 
    )
    total_views = models.IntegerField(default=0)
    total_favorites = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0.0)
    overall_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.destination.name}"
    
class DestinationView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='view_history')
    ip_address = models.GenericIPAddressField(null=True, blank=True) # Để tính cả khách vãng lai
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Tối ưu hóa truy vấn khi dữ liệu lớn
        indexes = [
            models.Index(fields=['destination', 'viewed_at']),
            models.Index(fields=['user', 'viewed_at']),
        ]