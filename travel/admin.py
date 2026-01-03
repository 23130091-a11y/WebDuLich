from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Destination, DestinationImage, TourPackage, 
    Review, RecommendationScore, SearchHistory,
    ReviewVote, ReviewReport
)

# ======================================================================
# 1. INLINES (Để hiện các bảng phụ ngay trong bảng chính)
# ======================================================================

class DestinationImageInline(admin.TabularInline):
    model = DestinationImage
    extra = 2
    fields = ['image', 'caption', 'order']

class TourPackageInline(admin.StackedInline):
    model = TourPackage
    extra = 1
    prepopulated_fields = {'slug': ('name',)}
    fields = ['name', 'slug', 'price', 'duration', 'is_active']

# ======================================================================
# 2. ADMIN CLASSES CHO MODEL MỚI
# ======================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    # Thêm average_rating và is_featured vào danh sách hiển thị
    list_display = ['name', 'destination', 'price', 'average_rating', 'is_featured', 'is_active', 'total_views']
    
    # Cho phép bật/tắt nhanh "Nổi bật" và "Hoạt động" ngay tại danh sách
    list_editable = ['is_featured', 'is_active']
    
    # Thêm bộ lọc cho các trường AI
    list_filter = ['is_active', 'is_featured', 'destination', 'category']
    
    search_fields = ['name', 'destination__name']
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'slug', 'destination', 'category', 'details')
        }),
        ('Giá & Lịch trình', {
            'fields': ('price', 'duration', 'start_date', 'end_date', 'is_available_today')
        }),
        ('Trạng thái & Ảnh', {
            'fields': ('is_active', 'is_featured', 'image_main', 'tags')
        }),
        ('AI & Đánh giá (Tự động cập nhật)', {
            'fields': ('average_rating', 'total_reviews', 'total_views'),
            'classes': ('collapse',), 
        }),
        ('Vị trí & Bản đồ', {
            'fields': ('meeting_point', 'start_latitude', 'start_longitude'),
            'description': 'Nhập tọa độ để hiển thị điểm bắt đầu trên bản đồ.'
        }),
        ('Danh sách Yêu thích', {
            'fields': ('favorites',),
            'classes': ('collapse',),
        }),
    )
    
    filter_horizontal = ('favorites',)

# ======================================================================
# 3. CẬP NHẬT DESTINATION ADMIN (Hợp nhất cũ & mới)
# ======================================================================

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'location', 'travel_type', 'avg_price', 'rating', 'is_popular', 'created_at']
    list_filter = ['category', 'travel_type', 'location', 'is_popular']
    search_fields = ['name', 'location', 'description']
    list_editable = ['is_popular', 'category']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    # Quan trọng: Hiện cả ảnh và các tour liên quan
    inlines = [DestinationImageInline, TourPackageInline]

# ======================================================================
# 4. REVIEW & LOGIC CŨ (Giữ nguyên toàn bộ logic của bạn)
# ======================================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'destination', 'author_name', 'rating_stars', 'status', 'status_badge', 
        'is_verified', 'helpful_count', 'report_count', 'created_at'
    ]
    list_filter = ['status', 'rating', 'is_verified', 'created_at', 'travel_type']
    search_fields = ['author_name', 'comment', 'destination__name']
    list_editable = ['status']
    readonly_fields = [
        'user', 'user_ip', 'user_agent', 'sentiment_score', 
        'positive_keywords', 'negative_keywords', 'created_at', 'updated_at',
        'helpful_count', 'not_helpful_count', 'report_count'
    ]
    
    fieldsets = (
        ('Thông tin cơ bản', {'fields': ('destination', 'author_name', 'rating', 'comment')}),
        ('Thông tin chuyến đi', {'fields': ('visit_date', 'travel_type', 'travel_with'), 'classes': ('collapse',)}),
        ('Xác minh & Trạng thái', {'fields': ('user', 'is_verified', 'status')}),
        ('AI Analysis', {'fields': ('sentiment_score', 'positive_keywords', 'negative_keywords'), 'classes': ('collapse',)}),
        ('Engagement', {'fields': ('helpful_count', 'not_helpful_count', 'report_count'), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('user_ip', 'user_agent', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )
    
    actions = ['approve_reviews', 'reject_reviews', 'mark_verified']
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #ffc107;">{}</span>', stars)
    rating_stars.short_description = 'Rating'
    
    def status_badge(self, obj):
        colors = {'pending': '#ffc107', 'approved': '#28a745', 'rejected': '#dc3545'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    @admin.action(description='Duyệt các review đã chọn')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(status=Review.STATUS_APPROVED)
        self.message_user(request, f'Đã duyệt {updated} review(s)')

    @admin.action(description='Từ chối các review đã chọn')
    def reject_reviews(self, request, queryset):
        updated = queryset.update(status=Review.STATUS_REJECTED)
        self.message_user(request, f'Đã từ chối {updated} review(s)')

    @admin.action(description='Đánh dấu đã xác minh')
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'Đã xác minh {updated} review(s)')

# ======================================================================
# 5. CÁC MODEL PHỤ KHÁC (ReviewVote, ReviewReport, RecommendationScore, SearchHistory)
# ======================================================================

@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ['review', 'reason', 'reporter_ip', 'is_resolved', 'created_at']
    list_filter = ['reason', 'is_resolved', 'created_at']
    list_editable = ['is_resolved']
    readonly_fields = ['review', 'reporter_ip', 'reporter_user', 'reason', 'description', 'created_at']
    actions = ['resolve_reports', 'reject_reported_reviews']
    @admin.action(description='Đánh dấu đã xử lý')
    def resolve_reports(self, request, queryset):
        updated = queryset.update(is_resolved=True)
        self.message_user(request, f'Đã xử lý {updated} báo cáo')
    @admin.action(description='Từ chối review bị báo cáo')
    def reject_reported_reviews(self, request, queryset):
        for report in queryset:
            report.review.status = Review.STATUS_REJECTED
            report.review.save()
            report.is_resolved = True
            report.save()
        self.message_user(request, f'Đã từ chối {queryset.count()} review(s)')

@admin.register(ReviewVote)
class ReviewVoteAdmin(admin.ModelAdmin):
    list_display = ['review', 'vote_type', 'user', 'user_ip', 'created_at']
    list_filter = ['vote_type', 'created_at']
    readonly_fields = ['review', 'user', 'user_ip', 'vote_type', 'created_at']

@admin.register(RecommendationScore)
class RecommendationScoreAdmin(admin.ModelAdmin):
    list_display = ['destination', 'overall_score', 'avg_rating', 'total_reviews', 'positive_review_ratio', 'last_calculated']
    ordering = ['-overall_score']
    readonly_fields = ['last_calculated']

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['query', 'results_count', 'user', 'user_ip', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query']
    readonly_fields = ['query', 'user', 'user_ip', 'results_count', 'created_at']