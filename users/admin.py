from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, TravelPreference

# Register your models here.
# -----------------------------
# 1. Custom User Admin
# -----------------------------
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Các field hiển thị ngoài danh sách Users
    list_display = ('email', 'username', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username')

    # Sắp xếp
    ordering = ('email',)

    # Field dùng để đăng nhập
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Thông tin cá nhân', {'fields': ('username', 'avatar')}),
        ('Phân quyền', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        ('Thông tin hệ thống', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

# -----------------------------
# 2. TravelPreference Admin
# -----------------------------
@admin.register(TravelPreference)
class TravelPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'travel_type', 'location')
    search_fields = ('user__email', 'travel_type', 'location')
