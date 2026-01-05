import math
import os
import urllib.parse
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q, Max, Count
from django.utils.text import slugify

from datetime import datetime, date, timedelta

from users.models import TravelPreference
from .services import get_weather_forecast, get_route, get_location_coordinates, get_nearby_hotels, get_nearby_restaurants, get_current_weather
from django.core.paginator import Paginator
from .models import TourPackage, Category, Destination, SearchHistory, Review, Favorite
import bleach

from .cache_utils import get_cache_key, get_or_set_cache
from django.views.decorators.http import require_http_methods, require_POST
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.decorators import login_required

#--Tram--#
#accountProfile
from django.shortcuts import render

def account_profile(request):
    return render(request, 'travel/accountProfile.html')

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import AccountProfile, TravelType, RecommendationScore


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def api_profile(request):
    user = request.user

    profile, _ = AccountProfile.objects.get_or_create(user=user)

    if request.method == "GET":
        return Response({
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": profile.phone,
            "birthday": profile.birthday,
            "profession": profile.profession,
        })

    # PUT – cập nhật
    user.first_name = request.data.get("first_name", "")
    user.last_name = request.data.get("last_name", "")
    user.save()

    profile.phone = request.data.get("phone", "")
    profile.birthday = request.data.get("birthday") or None
    profile.profession = request.data.get("profession", "")
    profile.save()

    return Response({"success": True})



# ----------------------------
# Hàm chuẩn hóa tên Category
# ----------------------------
def normalize_category_name(name: str) -> str | None:
    if not name:
        return None

    raw = urllib.parse.unquote(name).strip().lower()

    mapping = {
        "biển & đảo": "Biển & Đảo",
        "bien & dao": "Biển & Đảo",
        "biển đảo": "Biển & Đảo",
        "bien dao": "Biển & Đảo",
        "du lịch và biển đảo": "Biển & Đảo",
        "du lich va bien dao": "Biển & Đảo",

        "núi & cao nguyên": "Núi & Cao nguyên",
        "nui & cao nguyen": "Núi & Cao nguyên",
        "núi cao nguyên": "Núi & Cao nguyên",
        "nui cao nguyen": "Núi & Cao nguyên",
        "du lịch núi & cao nguyên": "Núi & Cao nguyên",
        "du lich nui & cao nguyen": "Núi & Cao nguyên",

        "văn hóa - lịch sử": "Văn hóa - Lịch sử",
        "van hoa - lich su": "Văn hóa - Lịch sử",
        "văn hóa lịch sử": "Văn hóa - Lịch sử",
        "van hoa lich su": "Văn hóa - Lịch sử",

        "du lịch - sinh thái": "Du lịch - Sinh thái",
        "du lich - sinh thai": "Du lịch - Sinh thái",
        "du lịch sinh thái": "Du lịch - Sinh thái",
        "du lich sinh thai": "Du lịch - Sinh thái",
        "sinh thái": "Du lịch - Sinh thái",
        "sinh thai": "Du lịch - Sinh thái",

        "ẩm thực - chợ đêm": "Ẩm thực - Chợ đêm",
        "am thuc - cho dem": "Ẩm thực - Chợ đêm",
        "ẩm thực": "Ẩm thực - Chợ đêm",
        "am thuc": "Ẩm thực - Chợ đêm",
        "chợ đêm": "Ẩm thực - Chợ đêm",
        "cho dem": "Ẩm thực - Chợ đêm",

        "lễ hội - sự kiện": "Lễ hội - Sự kiện",
        "le hoi - su kien": "Lễ hội - Sự kiện",
        "lễ hội": "Lễ hội - Sự kiện",
        "le hoi": "Lễ hội - Sự kiện",
        "sự kiện": "Lễ hội - Sự kiện",
        "su kien": "Lễ hội - Sự kiện",

        "nghỉ dưỡng": "Nghỉ dưỡng",
        "nghi duong": "Nghỉ dưỡng",
        "thư giãn": "Nghỉ dưỡng",
        "thu gian": "Nghỉ dưỡng",
        "nghỉ dưỡng - thư giãn": "Nghỉ dưỡng",
        "nghi duong - thu gian": "Nghỉ dưỡng",
    }

    normalized = raw.replace("  ", " ").replace("—", "-")

    if normalized in mapping:
        return mapping[normalized]

    contains_rules = [
        (("biển", "đảo"), "Biển & Đảo"),
        (("núi", "cao nguyên"), "Núi & Cao nguyên"),
        (("văn hóa", "lịch sử"), "Văn hóa - Lịch sử"),
        (("sinh thái",), "Du lịch - Sinh thái"),
        (("ẩm thực",), "Ẩm thực - Chợ đêm"),
        (("chợ đêm",), "Ẩm thực - Chợ đêm"),
        (("lễ hội",), "Lễ hội - Sự kiện"),
        (("sự kiện",), "Lễ hội - Sự kiện"),
        (("nghỉ dưỡng",), "Nghỉ dưỡng"),
        (("thư giãn",), "Nghỉ dưỡng"),
    ]
    for tokens, target in contains_rules:
        if all(tok in normalized for tok in tokens):
            return target

    return None
    ###
# ----------------------------
# Bản đồ tags cho từng Category
# ----------------------------
MAP_THE_LOAI_TO_TAGS = {
    "Biển & Đảo": ["Lặn biển", "Ngắm san hô", "Thể thao dưới nước", "Chèo thuyền", "Biển đảo", "Bãi biển", "Hải sản"],
    "Núi & Cao nguyên": ["Leo núi", "Trekking", "Cắm trại", "Săn mây", "Ngắm cảnh", "Homestay", "Trải nghiệm văn hóa", "Núi", "Cao nguyên"],
    "Văn hóa - Lịch sử": ["Di tích", "Lịch sử", "Bảo tàng", "Làng nghề truyền thống", "Nghệ thuật biểu diễn", "Văn hóa", "Đền thờ", "Chùa"],
    "Du lịch - Sinh thái": ["Vườn quốc gia", "Khu bảo tồn", "Hang động", "Khám phá Hang động", "Sinh thái", "Thiên nhiên"],
    "Ẩm thực - Chợ đêm": ["Đặc sản", "Tour Ẩm thực đường phố", "Chợ đêm", "Phố ẩm thực", "Ẩm thực", "Đường phố", "Hải sản"],
    "Lễ hội - Sự kiện": ["Lễ hội Truyền thống", "Sự kiện theo Tháng", "Sự kiện theo Mùa", "Lễ hội", "Sự kiện"],
    "Nghỉ dưỡng": ["Resort", "Khách sạn Cao cấp", "Spa", "Chăm sóc Sức khỏe", "Wellness", "Retreat", "Yoga", "Nghỉ dưỡng", "Thư giãn"],
}

# ----------------------------
# View trang chủ
# ----------------------------
def home(request):
    # ------------------------------
    # 1. Lấy dữ liệu static như cũ
    # ------------------------------
    base_path = os.path.join(settings.BASE_DIR, 'travel', 'static', 'images')
    results = []
    try:
        for folder in os.listdir(base_path):
            folder_path = os.path.join(base_path, folder)
            if os.path.isdir(folder_path):
                images = [
                    f"{folder}/{img}"
                    for img in os.listdir(folder_path)
                    if img.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
                ]
                if images:
                    results.append({
                        "name": folder.title(),
                        "desc": f"Khám phá vẻ đẹp của {folder.title()}",
                        "images": images,
                        "folder": folder,
                        "img": images[0]
                    })
    except Exception as e:
        print("Error:", e)

    # ------------------------------
    # 2. Gợi ý theo Preferences
    # ------------------------------
    recommendations = []

    # CHÚ Ý: Bạn đang dùng JWT, nên ở môi trường local load trang truyền thống,
    # request.user có thể bị Anonymous. Hãy đảm bảo bạn đã làm bước login session
    # hoặc tạm thời test bằng cách bỏ check is_authenticated nếu muốn xem kết quả.

    if request.user.is_authenticated:
        # 1. Lấy tất cả sở thích của User
        prefs = TravelPreference.objects.filter(user=request.user)

        if prefs.exists():
            # Lấy danh sách string từ sở thích
            fav_locations = [p.location.strip() for p in prefs]
            fav_types = [p.travel_type.strip() for p in prefs]

            # 2. Xây dựng Query tập trung vào Location và Category
            query = Q()

            # So sánh với địa điểm (Location của Destination)
            for loc in fav_locations:
                query |= Q(destination__location__icontains=loc) | Q(destination__name__icontains=loc)

            # So sánh với loại hình (Tên của Category)
            for t in fav_types:
                # normalize_category_name là hàm bạn đã viết để khớp "Biển" thành "Biển & Đảo"
                norm_name = normalize_category_name(t)
                query |= Q(category__name__icontains=t)
                if norm_name:
                    query |= Q(category__name__icontains=norm_name)

            # 3. Thực hiện truy vấn
            recommendations = (
                TourPackage.objects
                .filter(query, is_active=True)
                .select_related('category', 'destination')
                .distinct()[:8]
            )

            # DEBUG: In ra terminal để kiểm tra có tìm thấy gì không
            print(f"DEBUG: Found {recommendations.count()} recommendations for User {request.user.email}")

    return render(request, 'travel/index.html', {
        "results": results,
        "recommendations": recommendations
    })

# --- 2. API ENDPOINT: LỌC THEO THỂ LOẠI ---
def goi_y_theo_the_loai(request):
    """
    Endpoint trả về danh sách gói tour/hoạt động phổ biến nhất theo thể loại.
    SỬ DỤNG: TourPackage
    """
    if TourPackage is None:
        return JsonResponse({"error": "Mô hình TourPackage chưa được load"}, status=500)

    the_loai_encoded = request.GET.get('the_loai', None)
    if not the_loai_encoded:
        return JsonResponse({"error": "Thiếu tham số thể loại"}, status=400)

    # Chuẩn hóa tên thể loại
    the_loai_standard = normalize_category_name(the_loai_encoded)
    if not the_loai_standard:
        return JsonResponse({"error": "Thể loại không hợp lệ"}, status=400)

    tags = MAP_THE_LOAI_TO_TAGS.get(the_loai_standard, [])
    if not tags:
        return JsonResponse({"message": "Không tìm thấy thẻ tương ứng"}, status=200)

    # 1. Tạo Q object để lọc OR trên các tags
    q_tags = Q()
    for t in tags:
        q_tags |= Q(tags__name__icontains=t) | Q(name__icontains=t)

    # 2. Truy vấn ORM: lọc theo Q object, sắp xếp theo rating của TourPackage
    qs = TourPackage.objects.filter(q_tags).order_by('-rating')[:100]

    # 3. Chuẩn bị dữ liệu trả về Json
    results = []
    for a in qs:
        tags_list = list(a.tags.all().values_list('name', flat=True)) if hasattr(a, 'tags') else []
        results.append({
            "DiemDenID": a.id,
            "TenDiaDiem": a.name,
            "MoTa": a.details,
            "URL_AnhDaiDien": a.image_main.url if a.image_main else None,
            "ChiPhi_TB": a.price,
            "Diem_ChuyenMon": a.rating,
            "KhuVuc": a.destination.name if a.destination else None,
            "TheLoai_Tags": tags_list
        })

    return JsonResponse(results, safe=False)


# --- 3. VIEW TRANG KẾT QUẢ LỌC ---
def category_detail(request):
    category_slug_param = request.GET.get('category')
    destination = request.GET.get('destination')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    date_str = request.GET.get('date')
    availability = request.GET.get('available')
    tag_filters = request.GET.getlist('tag')
    sort = request.GET.get('sort')

    qs = TourPackage.objects.filter(is_active=True)

    category_obj = None
    display_category_name = None
    category_tags_list = []

    if category_slug_param:
        category_name_key = normalize_category_name(category_slug_param)
        raw_tags = MAP_THE_LOAI_TO_TAGS.get(category_name_key, [])
        category_tags_list = [{"slug": slugify(t), "name": t} for t in raw_tags]
        display_category_name = category_name_key or category_slug_param

        if category_name_key:
            category_slug_normalized = slugify(category_name_key)
            category_obj = Category.objects.filter(slug=category_slug_normalized).first()
            if not category_obj:
                category_obj = Category.objects.filter(name__iexact=category_name_key).first()

        if category_obj:
            qs = qs.filter(Q(category=category_obj) | Q(destination__category=category_obj))
            display_category_name = category_obj.name
        elif category_tags_list:
            q_tags = Q()
            for t in category_tags_list:
                q_tags |= Q(tags__slug__iexact=t["slug"])
            qs = qs.filter(q_tags).distinct()
    else:
        display_category_name = 'Du lịch'

    if tag_filters:
        qs = qs.filter(tags__slug__in=tag_filters).distinct()

    if destination:
        qs = qs.filter(destination__name__icontains=destination)

    today = date.today()
    selected_date = None
    if date_str:
        try:
            selected_date = date.fromisoformat(date_str)
            qs = qs.filter(
                start_date__lte=selected_date,
                end_date__gte=selected_date
            )
        except ValueError:
            selected_date = date_str
    elif availability == 'today':
        today = date.today()
        qs = qs.filter(
            start_date__lte=today,
            end_date__gte=today
        )

    if price_min:
        try:
            qs = qs.filter(price__gte=int(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            max_val = int(price_max)
            qs = qs.filter(Q(price__lte=max_val) | Q(price__isnull=True))
        except ValueError:
            pass

    # Sắp xếp
    if sort == 'price_asc':
        qs = qs.order_by('price')
    elif sort == 'price_desc':
        qs = qs.order_by('-price')
    elif sort == 'latest':
        qs = qs.order_by('-id')
    else:
        qs = qs.order_by('-destination__score')

    # Lọc theo rating
    rating_min = request.GET.get('rating_min')
    if rating_min:
        try:
            rating_val = float(rating_min)
            if rating_val < 5:
                # Lọc từ rating_val đến nhỏ hơn rating_val+1, giới hạn max 5
                qs = qs.filter(destination__score__gte=rating_val, destination__score__lt=min(rating_val+1, 5))
            else:
                # Chọn 5 sao chính xác
                qs = qs.filter(destination__score=5)
        except ValueError:
            pass

    # Chuẩn bị kết quả
    results = []
    try:
        qs = qs.select_related('destination', 'category').prefetch_related('tags')
        for tour in qs[:200]:
            tags_text = ', '.join([tag.slug for tag in tour.tags.all() if tag])
            results.append({
                'id': tour.id,
                'title': tour.name,
                'description': tour.details,
                'image': tour.image_main.url if tour.image_main else None,
                'price': tour.price,
                'rating': tour.rating, 
                'destination_score': tour.destination.score if tour.destination else 0.0,
                'destination': tour.destination.name if tour.destination else 'Không rõ',
                'category': tour.category.name if tour.category else 'Không rõ',
                'tags_text': tags_text,
                'slug': tour.slug if tour.slug else None,
            })

            
    except Exception as e:
        print(f"ERROR query TourPackage: {e}")
        results = []

    context = {
        'results': results,
        'total_results': len(results),
        'category_name': display_category_name,
        'selected_destination': destination or 'Toàn quốc',
        'selected_date': selected_date,
        'active_tags': tag_filters,
        'price_min': price_min,
        'price_max': price_max,
        'active_sort': sort or 'rating',
        'category_tags': category_tags_list,
        'all_categories': Category.objects.all(),
    }

    return render(request, 'travel/category_detail.html', context)


# --- 4. VIEW CHI TIẾT TOUR ---
def tour_detail(request, tour_slug):
    """Xử lý yêu cầu hiển thị chi tiết một Tour Package."""
    tour = get_object_or_404(
        TourPackage.objects.select_related('category', 'destination').prefetch_related('tags'),
        slug=tour_slug
    )

    related_tours = TourPackage.objects.filter(
        category=tour.category
    ).exclude(pk=tour.pk).order_by('?')[:4]

    context = {
        'tour': tour,
        'related_tours': related_tours,
    }
    return render(request, 'travel/tour_detail.html', context)

# Cần sửa lại (destination chưa hoàn thiện nên để đỡ)
def destination_list(request):
    from django.db.models import F

    qs = (
        Destination.objects
        .select_related('recommendation')
        .prefetch_related('images', 'travel_type')
        .order_by(F('recommendation__overall_score').desc(nulls_last=True))
    )

    return render(request, 'travel/destination_list.html', {
            'destinations': qs
        })

# Thanh

def get_client_ip(request):
    """Lấy IP của client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def save_user_preference(user, destination):
    from users.models import TravelPreference

    for t in destination.travel_type.all():
        TravelPreference.objects.get_or_create(
            user=user,
            travel_type=t.slug,  # slug
            location=''
        )

    if destination.location:
        TravelPreference.objects.get_or_create(
            user=user,
            travel_type='__location__',
            location=destination.location
        )

# Search (sửa)
def search(request):
    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    travel_type = request.GET.get('type', '').strip()
    min_rating = request.GET.get('min_rating', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    qs = Destination.objects.all() \
        .select_related('category') \
        .prefetch_related('travel_type', 'images')

    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query)
        )

    if location:
        qs = qs.filter(location__icontains=location)

    if travel_type:
        qs = qs.filter(travel_type__slug=travel_type)

    try:
        if min_rating:
            qs = qs.filter(avg_rating__gte=float(min_rating))
    except ValueError:
        pass

    if max_price:
        qs = qs.filter(avg_price__lte=float(max_price))

    qs = qs.distinct()

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'destinations': page_obj,
        'total_results': paginator.count,
        'all_locations': Destination.objects.values_list('location', flat=True).distinct(),
        'all_types': TravelType.objects.all(),
    }
    return render(request, 'travel/search.html', context)

def destination_detail(request, destination_id):
    from .ai_engine import get_similar_destinations
    """Chi tiết địa điểm với thời tiết và đường đi"""
    destination = get_object_or_404(
        Destination.objects
        .select_related('recommendation')
        .prefetch_related('travel_type'),
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
    query = bleach.clean(request.GET.get('q', '').strip())[:100]

    if not query:
        return JsonResponse({'results': []})

    cache_key = get_cache_key('api_search', query=query.lower()[:5])

    def perform_search():
        from .utils_helpers import normalize_search_text

        destinations = (
            Destination.objects
            .select_related('recommendation')
            .prefetch_related('travel_type')
            .filter(
                Q(name__icontains=query) |
                Q(location__icontains=query)
            )[:50]
        )

        query_normalized = normalize_search_text(query)

        matching_destinations = []
        for dest in destinations:
            if (
                    query_normalized in normalize_search_text(dest.name)
                    or query_normalized in normalize_search_text(dest.location)
            ):
                matching_destinations.append(dest)

        matching_destinations.sort(
            key=lambda x: x.recommendation.overall_score if x.recommendation else 0,
            reverse=True
        )
        matching_destinations = matching_destinations[:10]

        results = []
        for dest in matching_destinations:
            rec = dest.recommendation
            results.append({
                'id': dest.id,
                'name': dest.name,
                'location': dest.location,
                'travel_type': [t.slug for t in dest.travel_type.all()], # theo slug
                'score': round(rec.overall_score, 1) if rec else 0,
                'avg_rating': round(dest.avg_rating, 1),
                'avg_price': float(dest.avg_price) if dest.avg_price else None,
            })

        return results

    return JsonResponse({
        'results': get_or_set_cache(
            cache_key,
            perform_search,
            timeout=settings.CACHE_TTL['search']
        )
    })

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
    from .ai_engine import analyze_sentiment

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

# Sửa tính điểm
def update_destination_scores(destination):
    """Cập nhật điểm gợi ý cho destination sau khi có review mới"""
    from django.db.models import Avg, Count
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Lấy thống kê reviews
        reviews = Review.objects.filter(
            destination=destination,
            status=Review.STATUS_APPROVED
        )

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

        rec, _ = RecommendationScore.objects.get_or_create(destination=destination)

        # Tính điểm tổng thể
        # Formula: 40% rating + 30% sentiment + 30% popularity
        views_score = min(rec.total_views / 1000.0, 1.0)
        favorite_score = min(rec.total_favorites / 200.0, 1.0)
        review_score = (avg_rating / 5) * 100
        sentiment_score = ((avg_sentiment + 1) / 2) * 100
        popularity_score = (views_score * 0.6 + favorite_score * 0.4) * 100

        overall_score = (
                review_score * 0.5 +
                sentiment_score * 0.3 +
                popularity_score * 0.2
        )

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
        destination.avg_rating = avg_rating
        destination.save(update_fields=['avg_rating'])

        # Refresh destination để lấy recommendation mới
        destination.refresh_from_db()

    except Exception as e:
        logger.error(f"Error updating destination scores: {str(e)}")
        raise

@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def api_search_history(request):
    """API lấy lịch sử tìm kiếm theo IP (không cần đăng nhập)"""
    client_ip = get_client_ip(request)
    limit = int(request.GET.get('limit', 10))

    # Lấy lịch sử tìm kiếm gần đây theo IP (unique queries)
    history = SearchHistory.objects.filter(
        user_ip=client_ip
    ).values('query').annotate(
        last_search=Max('created_at'),
        search_count=Count('id')
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

# Yêu thích destination
@login_required
def toggle_favorite(request, destination_id):
    destination = get_object_or_404(Destination, id=destination_id)

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        destination=destination
    )

    if not created:
        # Đã thích → bỏ thích
        favorite.delete()

    return redirect(request.META.get('HTTP_REFERER', 'travel:home'))

"""Click tim →
→ toggle_favorite →
→ nếu chưa có → tạo
→ nếu có → xóa
→ quay về trang trước"""

# List yêu thích
@login_required
def favorite_list(request):
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related('destination', 'destination__category')
        .order_by('-created_at')
    )

    return render(request, 'travel/favorites.html', {
        'favorites': favorites
    })