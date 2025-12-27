from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, TravelPreference

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    # Fields hiển thị trong form edit
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Thông tin cá nhân', {'fields': ('username', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),  # hiển thị nhưng không editable
    )

    # Chỉ định các trường readonly
    readonly_fields = ('last_login', 'date_joined')

    # Trường hiển thị trong list view
    list_display = ('email', 'username', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'is_superuser', 'groups')

    # Form để tạo user mới
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')}
         ),
    )

    search_fields = ('email', 'username')
    ordering = ('email',)
