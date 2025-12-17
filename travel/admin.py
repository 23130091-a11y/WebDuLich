from django.contrib import admin
from .models import Category, Destination, TourPackage, DestinationImage, TourImage

# ----------------------------------------------------
# 1. Inline cho DestinationImage và TourPackage
# ----------------------------------------------------
class DestinationImageInline(admin.TabularInline):
    model = DestinationImage
    extra = 1

class TourPackageInline(admin.TabularInline):
    model = TourPackage
    extra = 1
    prepopulated_fields = {'slug': ('name',)}

# ----------------------------------------------------
# 2. Destination Admin
# ----------------------------------------------------
@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    # Các trường hiển thị trong danh sách Địa điểm
    list_display = ('name', 'location', 'score', 'get_tags')
    
    # Các trường để tìm kiếm
    search_fields = ('name', 'location', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TourPackageInline, DestinationImageInline]

    def get_tags(self, obj):
        return ", ".join(o.name for o in obj.tags.all())
    get_tags.short_description = 'Hoạt động/Tags'

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