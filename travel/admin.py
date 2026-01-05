from django.contrib import admin
from .models import Category, Destination, TourPackage, DestinationImage, TourImage, Review, ReviewReport, ReviewVote, \
    RecommendationScore, SearchHistory
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
        'location',
        'display_travel_types',
        'avg_price',
        'avg_rating',
        'is_popular',
        'created_at'
    ]

    list_filter = ['is_popular', 'location', 'created_at']
    search_fields = ['name', 'location', 'description']
    list_editable = ['is_popular']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['travel_type']

    def display_travel_types(self, obj):
        return ", ".join(t.name for t in obj.travel_type.all())
    display_travel_types.short_description = "Loại du lịch"

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
    list_display = ('name', 'destination', 'category', 'price', 'duration', 'rating', 'is_active', 'is_available_today')

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
            'fields': ('name', 'slug', 'category', 'destination', 'rating')
        }),
        ('Giá và Thời lượng', {
            'fields': ('price', 'duration', 'start_date', 'end_date')
        }),
        ('Nội dung chi tiết', {
            'fields': ('image_main', 'details', 'address_detail', 'tags'),
            'description': 'Tải lên ảnh đại diện chính và mô tả chi tiết lịch trình tại đây.'
        }),
        ('Cấu hình hiển thị', {
            'fields': ('is_active', 'is_available_today'),
            'classes': ('collapse',), # Cấu hình hiển thị (collapse): Thu gọn mục này lại, bấm vào mới hiện ra
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

@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ['review', 'reason', 'reporter_ip', 'is_resolved', 'created_at']
    list_filter = ['reason', 'is_resolved', 'created_at']
    list_editable = ['is_resolved']

    readonly_fields = [
        'review', 'reporter_ip', 'reporter_user',
        'reason', 'description', 'created_at'
    ]

@admin.register(ReviewVote)
class ReviewVoteAdmin(admin.ModelAdmin):
    list_display = ['review', 'vote_type', 'user', 'user_ip', 'created_at']
    list_filter = ['vote_type']
    readonly_fields = ['review', 'user', 'user_ip', 'vote_type', 'created_at']

@admin.register(RecommendationScore)
class RecommendationScoreAdmin(admin.ModelAdmin):
    list_display = [
        'destination',
        'overall_score',
        'review_score',
        'sentiment_score',
        'total_reviews',
        'positive_review_ratio',
        'last_calculated'
    ]

    ordering = ['-overall_score']
    readonly_fields = ['last_calculated']

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['query', 'results_count', 'user', 'user_ip', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query']
    readonly_fields = ['query', 'user', 'user_ip', 'results_count', 'created_at']