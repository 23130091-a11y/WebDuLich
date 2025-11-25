from django.urls import path
from . import views

app_name = 'travel'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('destination/<int:destination_id>/', views.destination_detail, name='destination_detail'),
    
    # API endpoints
    path('api/search/', views.api_search, name='api_search'),
    path('api/provinces/', views.api_search_provinces, name='api_search_provinces'),
    path('api/review/', views.api_submit_review, name='api_submit_review'),
]