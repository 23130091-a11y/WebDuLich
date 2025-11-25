from django.contrib import admin
from django.urls import path, include
from django.conf import settings 
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('travel.urls')),  # Trang home của travel
    path('auth/', include('users.urls')),
]


# CHỈ THÊM DÒNG NÀY KHI ĐANG PHÁT TRIỂN (development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)