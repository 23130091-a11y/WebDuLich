from django.contrib import admin
from .models import Destination, Review, RecommendationScore, SearchHistory

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'travel_type', 'avg_price', 'created_at']
    list_filter = ['travel_type', 'location']
    search_fields = ['name', 'location', 'description']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['destination', 'author_name', 'rating', 'sentiment_score', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['author_name', 'comment']

@admin.register(RecommendationScore)
class RecommendationScoreAdmin(admin.ModelAdmin):
    list_display = ['destination', 'overall_score', 'avg_rating', 'total_reviews', 'last_calculated']
    ordering = ['-overall_score']

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['query', 'results_count', 'user_ip', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query']
