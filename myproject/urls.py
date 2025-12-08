from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('travel.urls')),  # Trang home của travel
    path('auth/', include('users.urls')),
]
