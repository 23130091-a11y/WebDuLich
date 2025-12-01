from django.urls import path, include
from . import views

# travel/urls.py (GỢI Ý SỬA ĐỔI)

urlpatterns = [
    path('', views.home, name='home'),
    path('category-detail/', views.category_detail, name='category_filter'), # <--- Đổi tên URL
    path('danh-muc/<slug:category_slug>/', views.category_detail, name='category_detail'),
    path('api/goi-y-theo-the-loai/', views.goi_y_theo_the_loai, name='goi_y_theo_the_loai'),
    path('tour/<slug:tour_slug>/', views.tour_detail, name='tour_detail'),
]