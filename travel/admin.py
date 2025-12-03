from django.contrib import admin
from .models import Category, Destination, TourPackage, DestinationImage

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
    list_display = ('name', 'location', 'get_tags')
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
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TourPackageInlineForCategory]

# ----------------------------------------------------
# 4. TourPackage Admin riêng (quản lý độc lập)
# ----------------------------------------------------
@admin.register(TourPackage)
class TourPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'destination', 'category', 'price', 'rating', 'is_active')
    search_fields = ('name', 'destination__name', 'category__name')
    list_filter = ('category', 'destination', 'is_active')
    prepopulated_fields = {'slug': ('name',)}