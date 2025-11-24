# travel/admin.py

from django.contrib import admin
from .models import Category, Destination, TourPackage, DestinationImage

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
    list_display = ('name', 'location', 'rating', 'get_tags')
    
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

