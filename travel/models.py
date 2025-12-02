from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Bảng địa điểm
class Destination(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên địa điểm")
    travel_type = models.CharField(max_length=50, verbose_name="Loại hình du lịch")
    location = models.CharField(max_length=100, verbose_name="Vị trí")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ chi tiết")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    image = models.ImageField(upload_to='destinations/', blank=True)
    
    # Thông tin địa lý (dùng cho tính khoảng cách)
    latitude = models.FloatField(null=True, blank=True, verbose_name="Vĩ độ")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Kinh độ")
    
    # Thông tin giá tham khảo (dữ liệu tĩnh)
    avg_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, 
                                     verbose_name="Giá trung bình (VNĐ)")
    
    # Metadata JSON (lưu thông tin bổ sung)
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Địa điểm"
        verbose_name_plural = "Địa điểm"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


# Bảng đánh giá (Review)
class Review(models.Model):
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='reviews')
    author_name = models.CharField(max_length=100, verbose_name="Tên người đánh giá")
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="Đánh giá (1-5 sao)")
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Phân tích sentiment (tự động tính)
    sentiment_score = models.FloatField(default=0.0, verbose_name="Điểm cảm xúc (-1 đến 1)")
    positive_keywords = models.JSONField(default=list, blank=True, verbose_name="Từ khóa tích cực")
    negative_keywords = models.JSONField(default=list, blank=True, verbose_name="Từ khóa tiêu cực")
    
    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.author_name} - {self.destination.name} ({self.rating}⭐)"


# Bảng điểm gợi ý (Pre-calculated)
class RecommendationScore(models.Model):
    destination = models.OneToOneField(Destination, on_delete=models.CASCADE, related_name='recommendation')
    
    # Các chỉ số đánh giá
    overall_score = models.FloatField(default=0.0, verbose_name="Điểm tổng thể (0-100)")
    review_score = models.FloatField(default=0.0, verbose_name="Điểm từ đánh giá")
    sentiment_score = models.FloatField(default=0.0, verbose_name="Điểm cảm xúc")
    popularity_score = models.FloatField(default=0.0, verbose_name="Điểm phổ biến")
    
    # Thống kê
    total_reviews = models.IntegerField(default=0)
    avg_rating = models.FloatField(default=0.0)
    positive_review_ratio = models.FloatField(default=0.0, verbose_name="Tỷ lệ đánh giá tích cực")
    
    # Metadata
    last_calculated = models.DateTimeField(auto_now=True, verbose_name="Lần tính cuối")
    
    class Meta:
        verbose_name = "Điểm gợi ý"
        verbose_name_plural = "Điểm gợi ý"
        ordering = ['-overall_score']
    
    def __str__(self):
        return f"{self.destination.name} - Score: {self.overall_score:.2f}"


# Bảng lịch sử tìm kiếm
class SearchHistory(models.Model):
    query = models.CharField(max_length=255, verbose_name="Từ khóa tìm kiếm")
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Lịch sử tìm kiếm"
        verbose_name_plural = "Lịch sử tìm kiếm"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.query} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"