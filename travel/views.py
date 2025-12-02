from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
import os
from django.conf import settings
from datetime import datetime

from .models import Destination, Review, RecommendationScore, SearchHistory
from .ai_module import search_destinations, analyze_sentiment
from .services import get_weather_forecast, get_current_weather, get_route, get_location_coordinates, calculate_distance
import math


def get_client_ip(request):
    """Lấy IP của client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def home(request):
    """Trang chủ - hiển thị địa điểm nổi bật"""
    base_path = os.path.join(settings.BASE_DIR, 'travel', 'static', 'images')
    results = []

    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            images = [
                f"{folder}/{img}" for img in os.listdir(folder_path)
                if img.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
            ]

            if images:
                results.append({
                    "name": folder.title(),
                    "desc": f"Khám phá vẻ đẹp của {folder.title()}",
                    "images": images,
                    "folder": folder,
                    "img": images[0]
                })
    
    # Lấy top địa điểm được gợi ý
    top_destinations = Destination.objects.select_related('recommendation').order_by(
        '-recommendation__overall_score'
    )[:6]

    return render(request, 'travel/index.html', {
        "results": results,
        "top_destinations": top_destinations
    })


def search(request):
    """Trang tìm kiếm nâng cao với thời tiết và đường đi"""
    query = request.GET.get('q', '').strip()
    from_location = request.GET.get('from_location', '').strip()
    location_filter = request.GET.get('location', '').strip()  # Đổi tên để tránh nhầm lẫn
    travel_date = request.GET.get('travel_date', '').strip()
    travel_type = request.GET.get('type', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    min_rating = request.GET.get('min_rating', '').strip()
    
    # Xây dựng filters
    filters = {}
    # Chỉ filter theo location nếu người dùng chọn từ dropdown, không phải từ query
    if location_filter:
        filters['location'] = location_filter
    if travel_type:
        filters['travel_type'] = travel_type
    if max_price:
        try:
            filters['max_price'] = float(max_price)
        except ValueError:
            pass
    if min_rating:
        try:
            filters['min_rating'] = float(min_rating)
        except ValueError:
            pass
    
    # Tìm kiếm địa điểm - chỉ dùng query, không dùng location_filter
    destinations = search_destinations(query, filters)
    
    # Lưu lịch sử
    if query or to_location:
        SearchHistory.objects.create(
            query=query or to_location,
            user_ip=get_client_ip(request),
            results_count=destinations.count()
        )
    
    # Thông tin đường đi và thời tiết
    route_info = None
    weather_info = None
    from_coords = None
    
    if from_location and destinations.exists():
        # Lấy tọa độ điểm xuất phát
        from_coords = get_location_coordinates(from_location)
        
        if from_coords:
            # Tính đường đi đến địa điểm đầu tiên
            first_dest = destinations.first()
            if first_dest.latitude and first_dest.longitude:
                route_info = get_route(
                    from_coords['lat'], from_coords['lon'],
                    first_dest.latitude, first_dest.longitude
                )
                
                # Lấy thời tiết cho ngày đi
                if travel_date:
                    try:
                        date_obj = datetime.strptime(travel_date, '%Y-%m-%d')
                        weather_info = get_weather_forecast(
                            first_dest.latitude,
                            first_dest.longitude,
                            travel_date
                        )
                    except:
                        pass
    
    # Phân trang
    paginator = Paginator(destinations, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Lấy danh sách locations và types
    all_locations = Destination.objects.values_list('location', flat=True).distinct()
    all_types = Destination.objects.values_list('travel_type', flat=True).distinct()
    
    context = {
        'query': query,
        'destinations': page_obj,
        'total_results': destinations.count(),
        'all_locations': all_locations,
        'all_types': all_types,
        'filters': {
            'from_location': from_location,
            'location': location_filter,
            'travel_date': travel_date,
            'travel_type': travel_type,
            'max_price': max_price,
            'min_rating': min_rating,
        },
        'route_info': route_info,
        'weather_info': weather_info,
        'from_coords': from_coords,
    }
    
    return render(request, 'travel/search.html', context)


def destination_detail(request, destination_id):
    """Chi tiết địa điểm với thời tiết và đường đi"""
    destination = get_object_or_404(Destination, id=destination_id)
    
    # Lấy reviews
    reviews = Review.objects.filter(destination=destination).order_by('-created_at')[:50]
    
    # Lấy điểm gợi ý
    try:
        recommendation = destination.recommendation
    except RecommendationScore.DoesNotExist:
        recommendation = None
    
    # Thông tin từ query params
    from_location = request.GET.get('from_location', '').strip()
    travel_date = request.GET.get('travel_date', '').strip()
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    
    # Thông tin đường đi
    route_info = None
    from_coords = None
    distance = None
    
    if from_location and destination.latitude and destination.longitude:
        from_coords = get_location_coordinates(from_location)
        if from_coords:
            route_info = get_route(
                from_coords['lat'], from_coords['lon'],
                destination.latitude, destination.longitude
            )
    elif user_lat and user_lng and destination.latitude and destination.longitude:
        try:
            distance = calculate_distance(
                float(user_lat), float(user_lng),
                destination.latitude, destination.longitude
            )
        except ValueError:
            pass
    
    # Thông tin thời tiết
    weather_info = None
    if destination.latitude and destination.longitude:
        if travel_date:
            weather_info = get_weather_forecast(
                destination.latitude,
                destination.longitude,
                travel_date
            )
        else:
            # Thời tiết hiện tại
            current = get_current_weather(destination.latitude, destination.longitude)
            if 'error' not in current:
                weather_info = {
                    'temperature': current['temperature'],
                    'windspeed': current['windspeed'],
                    'is_current': True
                }
    
    context = {
        'destination': destination,
        'reviews': reviews,
        'recommendation': recommendation,
        'distance': distance,
        'route_info': route_info,
        'from_coords': from_coords,
        'weather_info': weather_info,
        'travel_date': travel_date,
        'from_location': from_location,
    }
    
    return render(request, 'travel/destination_detail.html', context)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa 2 điểm (Haversine formula)
    Trả về khoảng cách tính bằng km
    """
    R = 6371  # Bán kính trái đất (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return round(distance, 2)


# API endpoints (cho AJAX requests)
def api_search(request):
    """API tìm kiếm (trả về JSON) - Hỗ trợ autocomplete"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    from .utils_helpers import normalize_search_text
    
    # Tìm kiếm địa điểm
    destinations = Destination.objects.all()
    
    # Tìm kiếm với normalize (hỗ trợ không dấu)
    query_normalized = normalize_search_text(query)
    
    matching_destinations = []
    for dest in destinations:
        # Kiểm tra tên và location
        name_normalized = normalize_search_text(dest.name)
        location_normalized = normalize_search_text(dest.location)
        
        if query_normalized in name_normalized or query_normalized in location_normalized:
            matching_destinations.append(dest)
    
    # Sắp xếp theo điểm gợi ý (ưu tiên địa điểm nổi tiếng)
    matching_destinations = sorted(
        matching_destinations,
        key=lambda x: x.recommendation.overall_score if hasattr(x, 'recommendation') else 0,
        reverse=True
    )[:10]
    
    results = []
    for dest in matching_destinations:
        try:
            score = dest.recommendation.overall_score
            avg_rating = dest.recommendation.avg_rating
        except:
            score = 0
            avg_rating = 0
        
        results.append({
            'id': dest.id,
            'name': dest.name,
            'location': dest.location,
            'travel_type': dest.travel_type,
            'score': round(score, 1),
            'avg_rating': round(avg_rating, 1),
            'avg_price': float(dest.avg_price) if dest.avg_price else None,
        })
    
    return JsonResponse({'results': results})


def api_search_provinces(request):
    """API tìm kiếm tỉnh thành (cho autocomplete)"""
    query = request.GET.get('q', '').strip()
    
    from .utils_helpers import search_provinces
    
    provinces = search_provinces(query)
    
    return JsonResponse({'provinces': provinces})


def api_submit_review(request):
    """API gửi đánh giá"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    destination_id = request.POST.get('destination_id')
    author_name = request.POST.get('author_name', 'Anonymous')
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    
    if not destination_id or not rating:
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    
    try:
        destination = Destination.objects.get(id=destination_id)
        rating = int(rating)
        
        if rating < 1 or rating > 5:
            return JsonResponse({'error': 'Rating must be between 1 and 5'}, status=400)
        
        # Phân tích sentiment
        sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(comment)
        
        # Tạo review
        review = Review.objects.create(
            destination=destination,
            author_name=author_name,
            rating=rating,
            comment=comment,
            sentiment_score=sentiment_score,
            positive_keywords=pos_keywords,
            negative_keywords=neg_keywords
        )
        
        return JsonResponse({
            'success': True,
            'review_id': review.id,
            'message': 'Cảm ơn bạn đã đánh giá!'
        })
        
    except Destination.DoesNotExist:
        return JsonResponse({'error': 'Destination not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid rating value'}, status=400)
