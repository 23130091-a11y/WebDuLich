from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import models
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
import os
from django.conf import settings
from datetime import datetime, timedelta
import bleach

from .models import Destination, Review, RecommendationScore, SearchHistory
from .ai_engine import search_destinations, analyze_sentiment, get_similar_destinations, get_personalized_for_user
from .services import get_weather_forecast, get_current_weather, get_route, get_location_coordinates, calculate_distance, get_nearby_hotels, get_nearby_restaurants
from .cache_utils import get_cache_key, get_or_set_cache
import math


def get_client_ip(request):
    """Lấy IP của client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def save_user_preference(user, destination):
    """Lưu sở thích của user dựa trên địa điểm đã xem"""
    from users.models import TravelPreference
    
    # Lưu loại hình du lịch
    if destination.travel_type:
        TravelPreference.objects.get_or_create(
            user=user,
            travel_type=destination.travel_type,
            location=''
        )
    
    # Lưu địa điểm
    if destination.location:
        TravelPreference.objects.get_or_create(
            user=user,
            travel_type='',
            location=destination.location
        )


def home(request):
    """Trang chủ - hiển thị địa điểm nổi bật (with caching)"""
    # Cache static images list
    cache_key = get_cache_key('homepage', 'images')
    
    def get_images():
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
        return results
    
    results = get_or_set_cache(
        cache_key,
        get_images,
        timeout=settings.CACHE_TTL['homepage']
    )
    
    # Cache top destinations
    def get_top_destinations():
        return list(
            Destination.objects.select_related('recommendation')
            .prefetch_related('reviews')
            .order_by('-recommendation__overall_score')[:6]
        )
    
    top_destinations = get_or_set_cache(
        get_cache_key('homepage', 'top_destinations'),
        get_top_destinations,
        timeout=settings.CACHE_TTL['recommendations']
    )
    
    # Gợi ý cá nhân hóa
    personalized_destinations = []
    viewed_history = request.session.get('viewed_destinations', [])
    travel_types = []
    locations = []
    
    # Nếu đã đăng nhập, lấy sở thích từ database
    if request.user.is_authenticated:
        from users.models import TravelPreference
        prefs = TravelPreference.objects.filter(user=request.user)
        travel_types = list(prefs.exclude(travel_type='').values_list('travel_type', flat=True).distinct())
        locations = list(prefs.exclude(location='').values_list('location', flat=True).distinct())
    
    # Nếu chưa có sở thích từ DB, lấy từ lịch sử xem (session)
    if not travel_types and not locations and viewed_history:
        recent_destinations = Destination.objects.filter(id__in=viewed_history[:5])
        travel_types = list(recent_destinations.values_list('travel_type', flat=True).distinct())
        locations = list(recent_destinations.values_list('location', flat=True).distinct())
    
    # Tìm địa điểm phù hợp
    if travel_types or locations:
        from django.db.models import Q
        filters = Q()
        for t in travel_types:
            if t:
                filters |= Q(travel_type__icontains=t)
        for loc in locations:
            if loc:
                filters |= Q(location__icontains=loc)
        
        if filters:
            personalized_destinations = list(
                Destination.objects.select_related('recommendation')
                .filter(filters)
                .exclude(id__in=viewed_history)
                .order_by('-recommendation__overall_score')[:6]
            )

    return render(request, 'travel/index.html', {
        "results": results,
        "top_destinations": top_destinations,
        "personalized_destinations": personalized_destinations,
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
    
    # Lưu lịch sử tìm kiếm theo IP
    if query:
        SearchHistory.objects.create(
            query=query,
            user_ip=get_client_ip(request),
            results_count=len(destinations)
        )
    
    # Thông tin đường đi và thời tiết
    route_info = None
    weather_info = None
    from_coords = None
    
    if from_location and len(destinations) > 0:
        # Lấy tọa độ điểm xuất phát
        from_coords = get_location_coordinates(from_location)
        
        if from_coords:
            # Tính đường đi đến địa điểm đầu tiên
            first_dest = destinations[0] if destinations else None
            if first_dest and first_dest.latitude and first_dest.longitude:
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
    
    # Lấy danh sách locations và types (optimized - only fetch needed fields)
    all_locations = Destination.objects.values_list('location', flat=True).distinct().order_by('location')
    all_types = Destination.objects.values_list('travel_type', flat=True).distinct().order_by('travel_type')
    
    context = {
        'query': query,
        'destinations': page_obj,
        'total_results': len(destinations),
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
    destination = get_object_or_404(
        Destination.objects.select_related('recommendation'),
        id=destination_id
    )
    
    # Lưu lịch sử xem vào session (cho gợi ý cá nhân hóa)
    viewed_history = request.session.get('viewed_destinations', [])
    if destination.id not in viewed_history:
        viewed_history.insert(0, destination.id)  # Thêm vào đầu
        viewed_history = viewed_history[:20]  # Giữ tối đa 20 địa điểm
        request.session['viewed_destinations'] = viewed_history
    
    # Tự động lưu sở thích nếu user đã đăng nhập
    if request.user.is_authenticated:
        save_user_preference(request.user, destination)
    
    # Lấy reviews với pagination
    reviews_list = Review.objects.filter(destination=destination).order_by('-created_at')
    reviews_paginator = Paginator(reviews_list, 10)  # 10 reviews per page
    reviews_page = request.GET.get('reviews_page', 1)
    reviews = reviews_paginator.get_page(reviews_page)
    
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
    
    # Lấy địa điểm tương tự
    similar_destinations = get_similar_destinations(destination, limit=4)
    
    context = {
        'destination': destination,
        'reviews': reviews,
        'reviews_paginator': reviews_paginator,  # For pagination info
        'total_reviews': reviews_paginator.count,
        'recommendation': recommendation,
        'distance': distance,
        'route_info': route_info,
        'from_coords': from_coords,
        'weather_info': weather_info,
        'travel_date': travel_date,
        'from_location': from_location,
        'similar_destinations': similar_destinations,
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
@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def api_search(request):
    """API tìm kiếm (trả về JSON) - Hỗ trợ autocomplete với rate limiting và caching"""
    query = request.GET.get('q', '').strip()
    
    # Sanitize query
    query = bleach.clean(query)[:100]
    
    if not query:
        return JsonResponse({'results': []})
    
    # Cache search results
    cache_key = get_cache_key('api_search', query=query.lower())
    
    def perform_search():
        from .utils_helpers import normalize_search_text
        
        # Tìm kiếm địa điểm - optimize with select_related
        destinations = Destination.objects.select_related('recommendation').all()
        
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
        
        return results
    
    results = get_or_set_cache(
        cache_key,
        perform_search,
        timeout=settings.CACHE_TTL['search']
    )
    
    return JsonResponse({'results': results})


@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def api_search_provinces(request):
    """API tìm kiếm tỉnh thành (cho autocomplete) với rate limiting"""
    query = request.GET.get('q', '').strip()
    query = bleach.clean(query)[:100]
    
    from .utils_helpers import search_provinces
    
    provinces = search_provinces(query)
    
    return JsonResponse({'provinces': provinces})


@require_POST
@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def api_submit_review(request):
    """
    API gửi đánh giá - Enhanced User-Generated Content
    Hỗ trợ cả guest và logged-in users
    """
    import json
    import logging
    logger = logging.getLogger(__name__)
    
    # Parse data từ cả form và JSON
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        data = request.POST
    
    destination_id = data.get('destination_id')
    author_name = data.get('author_name', '').strip()
    rating = data.get('rating')
    comment = data.get('comment', '').strip()
    
    # Optional fields for richer reviews
    visit_date = data.get('visit_date', '')
    travel_type = data.get('travel_type', '')
    travel_with = data.get('travel_with', '')
    
    # Validation
    if not destination_id or not rating:
        return JsonResponse({'error': 'Vui lòng điền đầy đủ thông tin'}, status=400)
    
    # Sanitize inputs để tránh XSS
    author_name = bleach.clean(author_name)[:100]
    comment = bleach.clean(comment)[:2000]  # Tăng limit cho comment chi tiết hơn
    travel_type = bleach.clean(travel_type)[:50]
    travel_with = bleach.clean(travel_with)[:50]
    
    # Get client info
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    # Xử lý user authentication
    user = None
    if request.user.is_authenticated:
        user = request.user
        # Ưu tiên tên từ user profile
        if not author_name:
            author_name = user.username or user.email.split('@')[0]
    elif not author_name:
        author_name = 'Khách'
    
    # Validate author name
    if len(author_name) < 2:
        return JsonResponse({'error': 'Tên phải có ít nhất 2 ký tự'}, status=400)
    
    try:
        destination = Destination.objects.get(id=int(destination_id))
        rating = int(rating)
        
        if rating < 1 or rating > 5:
            return JsonResponse({'error': 'Đánh giá phải từ 1 đến 5 sao'}, status=400)
        
        # Spam detection - kiểm tra nhiều điều kiện
        # 1. Cùng IP, cùng destination trong 1 giờ
        recent_review_ip = Review.objects.filter(
            destination=destination,
            user_ip=client_ip,
            created_at__gte=datetime.now() - timedelta(hours=1)
        ).exists()
        
        # 2. Cùng user (nếu đã đăng nhập), cùng destination
        recent_review_user = False
        if user:
            recent_review_user = Review.objects.filter(
                destination=destination,
                user=user,
                created_at__gte=datetime.now() - timedelta(hours=24)
            ).exists()
        
        if recent_review_ip or recent_review_user:
            return JsonResponse({
                'error': 'Bạn đã đánh giá địa điểm này gần đây. Vui lòng đợi trước khi gửi đánh giá mới.',
                'code': 'DUPLICATE_REVIEW'
            }, status=429)
        
        # Content quality check (only if comment is provided)
        if comment:
            # Kiểm tra spam patterns (links, repeated chars, etc.)
            spam_patterns = [
                r'http[s]?://',  # URLs
                r'(.)\1{5,}',    # Repeated characters (aaaaa)
                r'[A-Z]{10,}',   # All caps spam
            ]
            import re
            for pattern in spam_patterns:
                if re.search(pattern, comment):
                    return JsonResponse({
                        'error': 'Nội dung không hợp lệ. Vui lòng không đăng link hoặc spam.',
                        'code': 'SPAM_DETECTED'
                    }, status=400)
        
        # Phân tích sentiment (nếu có comment)
        sentiment_score = 0.0
        pos_keywords = []
        neg_keywords = []
        if comment:
            try:
                sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(comment)
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {e}")
                # Continue without sentiment if analysis fails
        
        # Parse visit_date
        parsed_visit_date = None
        if visit_date:
            try:
                parsed_visit_date = datetime.strptime(visit_date, '%Y-%m-%d').date()
            except ValueError:
                pass  # Ignore invalid date
        
        # Tạo review với đầy đủ thông tin
        review = Review.objects.create(
            destination=destination,
            author_name=author_name,
            rating=rating,
            comment=comment,
            user=user,
            user_ip=client_ip,
            user_agent=user_agent,
            visit_date=parsed_visit_date,
            travel_type=travel_type,
            travel_with=travel_with,
            sentiment_score=sentiment_score,
            positive_keywords=pos_keywords,
            negative_keywords=neg_keywords,
            is_verified=user is not None,  # Verified if logged in
            status=Review.STATUS_APPROVED,  # Auto-approve (có thể đổi thành PENDING)
        )
        
        # Cập nhật điểm gợi ý cho destination
        update_destination_scores(destination)
        
        # Lưu preference nếu user đã đăng nhập
        if user:
            save_user_preference(user, destination)
        
        logger.info(f"New review #{review.id} for {destination.name} by {author_name}")
        
        return JsonResponse({
            'success': True,
            'review_id': review.id,
            'message': 'Cảm ơn bạn đã chia sẻ trải nghiệm!',
            'is_verified': review.is_verified,
            'sentiment': {
                'score': round(sentiment_score, 2),
                'positive_keywords': pos_keywords[:5],
                'negative_keywords': neg_keywords[:5],
            }
        })
        
    except Destination.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy địa điểm'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)
    except Exception as e:
        logger.error(f"Error submitting review: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Có lỗi xảy ra. Vui lòng thử lại sau.'}, status=500)


@require_POST
@ratelimit(key='ip', rate='30/m', method='POST', block=True)
def api_vote_review(request):
    """API vote review helpful/not helpful"""
    import json
    
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        data = request.POST
    
    review_id = data.get('review_id')
    vote_type = data.get('vote_type')  # 'helpful' or 'not_helpful'
    
    if not review_id or vote_type not in ['helpful', 'not_helpful']:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    
    try:
        from .models import ReviewVote
        
        review = Review.objects.get(id=int(review_id))
        client_ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        
        # Check if already voted (by IP or user)
        existing_vote = ReviewVote.objects.filter(
            review=review,
            user_ip=client_ip
        ).first()
        
        if user:
            existing_vote = ReviewVote.objects.filter(
                review=review,
                user=user
            ).first() or existing_vote
        
        if existing_vote:
            # Update existing vote
            old_type = existing_vote.vote_type
            if old_type == vote_type:
                return JsonResponse({
                    'success': True,
                    'message': 'Bạn đã vote rồi',
                    'helpful_count': review.helpful_count,
                    'not_helpful_count': review.not_helpful_count,
                })
            
            # Change vote
            existing_vote.vote_type = vote_type
            existing_vote.save()
            
            # Update counts
            if old_type == 'helpful':
                review.helpful_count = max(0, review.helpful_count - 1)
                review.not_helpful_count += 1
            else:
                review.not_helpful_count = max(0, review.not_helpful_count - 1)
                review.helpful_count += 1
        else:
            # Create new vote
            ReviewVote.objects.create(
                review=review,
                user=user,
                user_ip=client_ip,
                vote_type=vote_type
            )
            
            if vote_type == 'helpful':
                review.helpful_count += 1
            else:
                review.not_helpful_count += 1
        
        review.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cảm ơn phản hồi của bạn!',
            'helpful_count': review.helpful_count,
            'not_helpful_count': review.not_helpful_count,
        })
        
    except Review.DoesNotExist:
        return JsonResponse({'error': 'Review không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def api_report_review(request):
    """API báo cáo review không phù hợp"""
    import json
    
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        data = request.POST
    
    review_id = data.get('review_id')
    reason = data.get('reason')
    description = data.get('description', '')
    
    valid_reasons = ['spam', 'inappropriate', 'fake', 'other']
    if not review_id or reason not in valid_reasons:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    
    try:
        from .models import ReviewReport
        
        review = Review.objects.get(id=int(review_id))
        client_ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        
        # Check if already reported by this IP
        existing_report = ReviewReport.objects.filter(
            review=review,
            reporter_ip=client_ip
        ).exists()
        
        if existing_report:
            return JsonResponse({
                'success': True,
                'message': 'Bạn đã báo cáo review này rồi'
            })
        
        # Create report
        ReviewReport.objects.create(
            review=review,
            reporter_ip=client_ip,
            reporter_user=user,
            reason=reason,
            description=bleach.clean(description)[:500]
        )
        
        # Update report count
        review.report_count += 1
        
        # Auto-hide if too many reports
        if review.report_count >= 3:
            review.status = Review.STATUS_PENDING
        
        review.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cảm ơn bạn đã báo cáo. Chúng tôi sẽ xem xét.'
        })
        
    except Review.DoesNotExist:
        return JsonResponse({'error': 'Review không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def update_destination_scores(destination):
    """Cập nhật điểm gợi ý cho destination sau khi có review mới"""
    from django.db.models import Avg, Count
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Lấy thống kê reviews
        reviews = Review.objects.filter(destination=destination)
        stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id'),
            avg_sentiment=Avg('sentiment_score')
        )
        
        avg_rating = stats['avg_rating'] or 0
        total_reviews = stats['total_reviews'] or 0
        avg_sentiment = stats['avg_sentiment'] or 0
        
        logger.info(f"Updating scores for {destination.name}: {total_reviews} reviews, avg_rating={avg_rating}")
        
        # Tính tỷ lệ đánh giá tích cực (rating >= 4)
        positive_reviews = reviews.filter(rating__gte=4).count()
        positive_ratio = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0
        
        # Tính điểm tổng thể
        # Formula: 40% rating + 30% sentiment + 30% popularity
        review_score = (avg_rating / 5) * 100
        sentiment_score = ((avg_sentiment + 1) / 2) * 100  # Convert -1~1 to 0~100
        popularity_score = min(total_reviews * 5, 100)  # Max 100 at 20 reviews
        
        overall_score = (review_score * 0.4) + (sentiment_score * 0.3) + (popularity_score * 0.3)
        
        # Cập nhật hoặc tạo RecommendationScore
        recommendation, created = RecommendationScore.objects.update_or_create(
            destination=destination,
            defaults={
                'overall_score': overall_score,
                'review_score': review_score,
                'sentiment_score': sentiment_score,
                'popularity_score': popularity_score,
                'total_reviews': total_reviews,
                'avg_rating': avg_rating,
                'positive_review_ratio': positive_ratio
            }
        )
        
        logger.info(f"RecommendationScore {'created' if created else 'updated'} for {destination.name}")
        
        # Cập nhật rating trong Destination
        destination.rating = avg_rating
        destination.save(update_fields=['rating'])
        
        # Refresh destination để lấy recommendation mới
        destination.refresh_from_db()
        
    except Exception as e:
        logger.error(f"Error updating destination scores: {str(e)}")
        raise


@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def api_nearby_places(request):
    """API lấy link tìm kiếm khách sạn và quán ăn gần đó"""
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    location_name = request.GET.get('location', '')
    
    if not lat or not lon:
        return JsonResponse({'error': 'Missing coordinates'}, status=400)
    
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return JsonResponse({'error': 'Invalid coordinates'}, status=400)
    
    hotels = get_nearby_hotels(lat, lon, location_name)
    restaurants = get_nearby_restaurants(lat, lon, location_name)
    
    return JsonResponse({
        'hotels': hotels,
        'restaurants': restaurants
    })


@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def api_search_history(request):
    """API lấy lịch sử tìm kiếm theo IP (không cần đăng nhập)"""
    client_ip = get_client_ip(request)
    limit = int(request.GET.get('limit', 10))
    
    # Lấy lịch sử tìm kiếm gần đây theo IP (unique queries)
    history = SearchHistory.objects.filter(
        user_ip=client_ip
    ).values('query').annotate(
        last_search=models.Max('created_at'),
        search_count=models.Count('id')
    ).order_by('-last_search')[:limit]
    
    results = [{
        'query': item['query'],
        'last_search': item['last_search'].strftime('%d/%m/%Y %H:%M'),
        'search_count': item['search_count']
    } for item in history]
    
    return JsonResponse({'history': results, 'has_history': len(results) > 0})


@require_http_methods(["POST"])
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def api_delete_search_history(request):
    """API xóa lịch sử tìm kiếm theo IP"""
    client_ip = get_client_ip(request)
    
    # Hỗ trợ cả POST form và JSON body
    if request.content_type == 'application/json':
        import json
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            delete_all = data.get('delete_all', False)
        except:
            query = ''
            delete_all = False
    else:
        query = request.POST.get('query', '').strip()
        delete_all = request.POST.get('delete_all', 'false') == 'true'
    
    if delete_all:
        deleted_count, _ = SearchHistory.objects.filter(user_ip=client_ip).delete()
    elif query:
        deleted_count, _ = SearchHistory.objects.filter(user_ip=client_ip, query=query).delete()
    else:
        return JsonResponse({'error': 'Thiếu tham số'}, status=400)
    
    return JsonResponse({
        'success': True,
        'deleted_count': deleted_count,
        'message': 'Đã xóa lịch sử tìm kiếm'
    })



