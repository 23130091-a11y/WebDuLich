# travel/admin.py

from django.contrib import admin
from .models import Category, Destination, TourPackage, DestinationImage, TourImage

# ----------------------------------------------------
# 1. Inline cho DestinationImage và TourPackage
# ----------------------------------------------------

# Cho phép thêm nhiều ảnh chi tiết ngay trong trang Destination
class DestinationImageInline(admin.TabularInline):
    model = DestinationImage
    extra = 1 # Số lượng form trống mặc định

# Cho phép thêm nhiều Gói Tour/Giá/Ngày ngay trong trang Destination
class TourPackageInline(admin.TabularInline):
    model = TourPackage
    extra = 1
    

# ----------------------------------------------------
# 2. Đăng ký Mô hình chính (Destination Admin)
# ----------------------------------------------------
@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    # Các trường hiển thị trong danh sách Địa điểm
    list_display = ('name', 'location', 'score', 'get_tags')
    
    # Các trường để tìm kiếm
    search_fields = ('name', 'location', 'description')
    
    # Các trường được điền sẵn từ trường khác (slug từ name)
    prepopulated_fields = {'slug': ('name',)}
    
    # Các Inline cho phép chỉnh sửa TourPackage và Ảnh ngay tại đây
    inlines = [TourPackageInline, DestinationImageInline]
    
    # Hiển thị Tags (TaggableManager) trong danh sách
    def get_tags(self, obj):
        return ", ".join(o.name for o in obj.tags.all())
    get_tags.short_description = 'Hoạt động/Tags'


# ----------------------------------------------------
# 3. Đăng ký các Mô hình còn lại
# ----------------------------------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)} # Tự động tạo slug



class TourImageInline(admin.TabularInline):
    model = TourImage
    extra = 3 # Hiển thị sẵn 3 ô để chọn ảnh
    fields = ('image', 'caption')

@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    # 2. Hiển thị danh sách cột thông minh (List Display)
    list_display = ('name', 'destination', 'category', 'price', 'duration', 'rating', 'is_active', 'is_available_today')
    
    # 3. Thanh tìm kiếm đa năng (Search Fields)
    # Cho phép tìm theo tên tour, tên địa danh hoặc chi tiết
    search_fields = ('name', 'destination__name', 'details', 'address_detail')
    
    # 4. Bộ lọc nhanh bên phải (List Filter)
    list_filter = ('is_active', 'is_available_today', 'category', 'destination', 'start_date')
    
    # 5. Tự động sinh Slug khi gõ tên (Prepopulated Fields)
    prepopulated_fields = {'slug': ('name',)}
    
    # 6. Tích hợp Inline ảnh đã tạo ở trên
    inlines = [TourImageInline]
    
    # 7. Sắp xếp lại giao diện nhập liệu cho chuyên nghiệp (Fieldsets)
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
            'classes': ('collapse',), # Thu gọn mục này lại, bấm vào mới hiện ra
        }),
    )

    # Thêm màu sắc hoặc icon cho các trạng thái (Tùy chọn)
    list_editable = ('is_active', 'is_available_today') # Sửa nhanh ngay tại danh sách