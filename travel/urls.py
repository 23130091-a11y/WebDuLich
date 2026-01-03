from django.urls import path, include
from . import views

app_name = 'travel'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('destination/<int:destination_id>/', views.destination_detail, name='destination_detail'),
    path('tour/<slug:slug>/', views.tour_detail, name='tour_detail'), 
    path('accounts/', include('django.contrib.auth.urls')),
    path('tour/favorite/<int:tour_id>/', views.toggle_tour_favorite, name='toggle_tour_favorite'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
   
    # API endpoints
    path('api/search/', views.api_search, name='api_search'),
    path('api/provinces/', views.api_search_provinces, name='api_search_provinces'),
    path('api/nearby/', views.api_nearby_places, name='api_nearby_places'),
    path('api/search-history/', views.api_search_history, name='api_search_history'),
    path('api/search-history/delete/', views.api_delete_search_history, name='api_delete_search_history'),
    
    # Review APIs (User-Generated Content)
    path('api/review/', views.api_submit_review, name='api_submit_review'),
    path('api/review/vote/', views.api_vote_review, name='api_vote_review'),
    path('api/review/report/', views.api_report_review, name='api_report_review'),
]