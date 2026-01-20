from django.contrib import admin
from .models import Category, Destination, TourPackage, DestinationImage, TourImage, Review, ReviewReport, ReviewVote, \
    RecommendationScore, SearchHistory, TravelType, RecommendationConfig
from django.utils.html import format_html


# ----------------------------------------------------
# 1. Inline cho DestinationImage và TourPackage
# ----------------------------------------------------
class DestinationImageInline(admin.TabularInline):
    model = DestinationImage
    extra = 1 # Hiển thị 1 dòng trống sẵn

class TourPackageInline(admin.TabularInline):
    model = TourPackage
    extra = 1
    prepopulated_fields = {'slug': ('name',)} # Tự động sinh giá trị cho slug dựa trên trường name

# ----------------------------------------------------
# 2. Destination Admin
# ----------------------------------------------------
@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'category',
        'location',
        'display_travel_types',
        'avg_price',
        'avg_rating',
        'is_popular',
        'created_at'
    ]

    list_filter = ['category', 'travel_type', 'location', 'is_popular']
    search_fields = ['name', 'location', 'description']
    list_editable = ['is_popular', 'category']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['travel_type']
    prepopulated_fields = {'slug': ('name',)}

    inlines = [DestinationImageInline, TourPackageInline]

    def display_travel_types(self, obj):
        return ", ".join(t.name for t in obj.travel_type.all())
    display_travel_types.short_description = "Loại du lịch" 

@admin.register(TravelType)
class TravelTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
# ----------------------------------------------------
# 3. Category Admin (hiển thị TourPackage)
# ----------------------------------------------------
class TourPackageInlineForCategory(admin.TabularInline):
    model = TourPackage
    extra = 0
    fields = ('name', 'price', 'duration', 'is_active')
    show_change_link = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)} # Tự động tạo slug

# Quản lý tourimage ngay trong trang tourpackage
class TourImageInline(admin.TabularInline):
    model = TourImage
    extra = 3 # Hiển thị sẵn 3 ô để chọn ảnh
    fields = ('image', 'caption')

@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    # Hiển thị danh sách cột thông minh (List Display)
    list_display = ('name', 'destination', 'total_reviews', 'duration', 'average_rating', 'is_available_today', 'is_active')

    # Thanh tìm kiếm đa năng (Search Fields)
    # Cho phép tìm theo tên tour, tên địa danh, chi tiết hoặc địa chỉ
    search_fields = ('name', 'destination__name', 'details', 'address_detail')

    # Bộ lọc nhanh bên phải (List Filter)
    list_filter = ('is_active', 'is_available_today', 'category', 'destination', 'start_date')

    # Tự động sinh Slug khi gõ tên (Prepopulated Fields)
    prepopulated_fields = {'slug': ('name',)}

    # Tích hợp TourImageInline phía trên ảnh đã tạo ở trên
    inlines = [TourImageInline]

    # Sắp xếp lại giao diện nhập liệu cho chuyên nghiệp (Fieldsets)
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'slug', 'category', 'destination')
        }),
        ('Giá và Thời lượng', {
            'fields': ('price', 'duration', 'start_date', 'end_date', 'is_available_today')
        }),
        ('Nội dung chi tiết', {
            'fields': ('is_active', 'image_main', 'details', 'address_detail', 'tags'),
            'description': 'Tải lên ảnh đại diện chính và mô tả chi tiết lịch trình tại đây.'
        }),
        ('AI & Đánh giá (Tự động cập nhật)', {
            'fields': ('average_rating', 'total_reviews', 'total_views'),
            'classes': ('collapse',), 
        }),
        ('Vị trí', {
            'fields': ('meeting_point', 'start_latitude', 'start_longitude'),
            'description': 'Nhập tọa độ để hiển thị điểm bắt đầu trên bản đồ.'
        }),
        
    )

    # Sửa nhanh ngay tại danh sách
    list_editable = ('is_active', 'is_available_today')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'destination',
        'author_name',
        'rating_stars',
        'status',
        'status_badge',
        'is_verified',
        'helpful_count',
        'report_count',
        'created_at'
    ]

    list_filter = ['status', 'rating', 'is_verified', 'created_at', 'travel_types']
    search_fields = ['author_name', 'comment', 'destination__name']
    list_editable = ['status']

    readonly_fields = [
        'user', 'user_ip', 'user_agent',
        'sentiment_score', 'positive_keywords', 'negative_keywords',
        'created_at', 'updated_at',
        'helpful_count', 'not_helpful_count', 'report_count'
    ]

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('destination', 'author_name', 'rating', 'comment')
        }),
        ('Thông tin chuyến đi', {
            'fields': ('visit_date', 'travel_types', 'travel_with'),
            'classes': ('collapse',)
        }),
        ('Xác minh & Trạng thái', {
            'fields': ('user', 'is_verified', 'status')
        }),
        ('AI Analysis', {
            'fields': ('sentiment_score', 'positive_keywords', 'negative_keywords'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('helpful_count', 'not_helpful_count', 'report_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('user_ip', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_reviews', 'reject_reviews', 'mark_verified']

    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color:#ffc107;font-size:14px">{}</span>', stars)
    rating_stars.short_description = 'Rating'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
        }
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;border-radius:10px;font-size:11px">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    @admin.action(description='Duyệt review')
    def approve_reviews(self, request, queryset):
        queryset.update(status=Review.STATUS_APPROVED)

    @admin.action(description='Từ chối review')
    def reject_reviews(self, request, queryset):
        queryset.update(status=Review.STATUS_REJECTED)

    @admin.action(description='Đánh dấu đã xác minh')
    def mark_verified(self, request, queryset):
        queryset.update(is_verified=True)


from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from .models import TourReview, ReviewReport

@admin.register(TourReview)
class TourReviewAdmin(admin.ModelAdmin):
    # Hiển thị các cột bạn cần
    list_display = (
        'user', 'tour', 'rating', 
        'helpful_count', 'not_helpful_count', 
        'report_count_display', # Cột đếm số lượt báo cáo
        'is_verified_user', 
        'is_verified_purchase', 
        'status'
    )
    list_filter = ('status', 'is_verified_purchase', 'is_verified_user', 'rating')
    list_editable = ('status', 'is_verified_user', 'is_verified_purchase')

    # Hàm tính số lượt báo cáo để hiện lên cột
    def report_count_display(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        count = ReviewReport.objects.filter(content_type=ct, object_id=obj.id).count()
        if count >= 5: # Nếu trên 5 lượt báo cáo thì hiện màu đỏ
            return format_html('<b style="color:red;">{} báo cáo (Cần xử lý!)</b>', count)
        return f"{count} báo cáo"
    
    report_count_display.short_description = "Số lượt báo cáo"

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ReviewReport

@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    # Thay 'review' bằng 'review_content' (một function) hoặc 'review_object'
    list_display = ('review_content', 'reason', 'reporter_user', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'reason', 'created_at')
    
    # readonly_fields phải chứa các field thực sự tồn tại trong model hoặc các method
    readonly_fields = ('created_at', 'reporter_ip', 'reporter_user', 'review_content')
    
    # Ẩn các trường kỹ thuật của GenericForeignKey để tránh nhầm lẫn
    exclude = ('content_type', 'object_id')

    def review_content(self, obj):
        """Hiển thị link dẫn đến Review bị báo cáo (TourReview hoặc Review)"""
        if obj.review_object:
            # Lấy thông tin model (tourreview hoặc review)
            app_label = obj.content_type.app_label
            model_name = obj.content_type.model
            
            try:
                # Tạo URL dẫn đến trang edit của Review đó
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.object_id])
                content = obj.review_object.comment[:50] # Lấy 50 ký tự đầu của comment
                return format_html('<a href="{}">[{}] {}...</a>', url, model_name.upper(), content)
            except:
                return f"[{model_name.upper()}] {obj.review_object}"
        return "Nội dung đã bị xóa"

    review_content.short_description = "Nội dung bị báo cáo"

    # Action để xử lý nhanh nhiều báo cáo
    actions = ['mark_as_resolved']

    @admin.action(description="Đánh dấu các báo cáo đã chọn là đã xử lý")
    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
    
@admin.register(ReviewVote)
class ReviewVoteAdmin(admin.ModelAdmin):
    list_display = ['review', 'vote_type', 'user', 'user_ip', 'created_at']
    list_filter = ['vote_type']
    readonly_fields = ['review', 'user', 'user_ip', 'vote_type', 'created_at']

@admin.register(RecommendationScore)
class RecommendationScoreAdmin(admin.ModelAdmin):
    # Sử dụng phương thức để hiển thị tên đối tượng (Destsination hoặc Tour)
    def get_target_name(self, obj):
        if obj.destination:
            return f"📍 {obj.destination.name}"
        if obj.tour:
            return f"🎫 {obj.tour.name}"
        return "N/A"
    get_target_name.short_description = 'Đối tượng'

    list_display = [
        'get_target_name',       # Hiển thị tên linh hoạt
        'overall_score', 
        'popularity_score',      # Khớp với model bạn gửi
        'sentiment_score', 
        'positive_review_ratio', 
        'total_reviews', 
        'last_calculated'
    ]

    # Thêm bộ lọc để dễ quản lý
    list_filter = ['last_calculated', 'overall_score']
    search_fields = ['destination__name', 'tour__name']
    ordering = ['-overall_score']
    readonly_fields = ['last_calculated']

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['query', 'results_count', 'user', 'user_ip', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query']
    readonly_fields = ['query', 'user', 'user_ip', 'results_count', 'created_at']


@admin.register(RecommendationConfig)
class RecommendationConfigAdmin(admin.ModelAdmin):
    list_display = ('review_score', 'sentiment_score', 'popularity_score')


