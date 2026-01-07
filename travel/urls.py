from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

# travel/urls.py (GỢI Ý SỬA ĐỔI)
app_name = 'travel'

urlpatterns = [
    path('', views.home, name='home'),
    path('category-detail/', views.category_detail, name='category_filter'), # <--- Đổi tên URL
    path('api/goi-y-theo-the-loai/', views.goi_y_theo_the_loai, name='goi_y_theo_the_loai'),
    path('tour/<slug:tour_slug>/', views.tour_detail, name='tour_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('accounts/', include('django.contrib.auth.urls')),

    path('search/', views.search, name='search'),

    # Tour review API (specific path)
    path('api/tour/<int:tour_id>/review/', views.api_submit_tour_review, name='api_submit_tour_review'),

    # Thêm route cho destination detail
    path('destination/<int:destination_id>/', views.destination_detail, name='destination_detail'),
    path('destinations/', views.destination_list, name='destination_list'), # chưa sd

    # API endpoints
    path('api/search/', views.api_search, name='api_search'),
    path('api/provinces/', views.api_search_provinces, name='api_search_provinces'),
    path('api/nearby/', views.api_nearby_places, name='api_nearby_places'),
    path('api/search-history/', views.api_search_history, name='api_search_history'),
    path('api/search-history/delete/', views.api_delete_search_history, name='api_delete_search_history'),

    # Review APIs (User-Generated Content) - Destination reviews
    path('api/review/', views.api_submit_review, name='api_submit_review'),
    path('api/review/vote/', views.api_vote_review, name='api_vote_review'),
    path('api/review/report/', views.api_report_review, name='api_report_review'),

    #profile account
    path('accountProfile/', views.account_profile, name='profile'),
    path("api/profile/", views.api_profile, name="api_profile"),

    # Url danh sách yêu thích
    path('favorites/', views.favorite_list, name='favorite_list'),
    # Url yêu thích destination (id)
    path('favorite/toggle-dest/<int:dest_id>/', views.toggle_destination_favorite, name='toggle_destination_favorite'),
    
    path('favorite/toggle-tour/<int:tour_id>/', views.toggle_tour_favorite, name='toggle_tour_favorite'),

    # URL hiển thị tất cả tour
    path('tours/', views.all_tours, name='all_tours'),

]