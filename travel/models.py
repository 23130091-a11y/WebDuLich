# D:\LT_Python\PyWeb\DoAnWeb\WebDuLich\travel\models.py
from django.conf import settings
from django.db import models
from taggit.managers import TaggableManager
from django.utils.text import slugify
from django.conf import settings

# ----------------------------------------------------------------------
# 1. Category Model
# ----------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# ----------------------------------------------------------------------
# 2. Destination Model
# ----------------------------------------------------------------------
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
    score = models.FloatField(default=0.0)
    is_popular = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, max_length=200)
    tags = TaggableManager()  # dùng name để filter

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
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    address_detail = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Địa chỉ đón/trả khách hoặc địa chỉ chính"
    )
    details = models.TextField()
    is_active = models.BooleanField(default=True)
    image_main = models.ImageField(upload_to='packages/main_images/', blank=True, null=True)
    tags = TaggableManager(blank=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True) # slug:
    # /destination/da-nang/
    # /tour/ba-na-hills-1-ngay/
    is_available_today = models.BooleanField(
        default=False,
        help_text="Check nếu tour này khả dụng trong ngày hiện tại hoặc tương lai gần."
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Nếu chưa gán category, tự động lấy từ destination
        if not self.category and self.destination and self.destination.category:
            self.category = self.destination.category

        # Nếu chưa có slug, tự động sinh từ name
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} at {self.destination.name}"

class TourImage(models.Model):
    tour = models.ForeignKey(TourPackage, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='packages/gallery/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.tour.name}"

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
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'user'],
                condition=~models.Q(user=None),
                name='unique_user_vote'
            ),
            models.UniqueConstraint(
                fields=['review', 'user_ip'],
                condition=~models.Q(user_ip=None),
                name='unique_ip_vote'
            ),
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
    destination = models.OneToOneField(Destination, on_delete=models.CASCADE, related_name='recommendation')

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


# 7.Account Profile
class AccountProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)

    birthday = models.DateField(null=True, blank=True)
    profession = models.CharField(max_length=100, blank=True, null=True)

    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return self.user.username
