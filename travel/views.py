import math
import os
import urllib.parse
from django.db import models
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q, Max, Count, F, Min
from django.utils.text import slugify
from .ai_engine import analyze_sentiment
from django.views.decorators.cache import never_cache

from datetime import datetime, date, timedelta
# from ratelimit.decorators import ratelimit
from django_ratelimit.decorators import ratelimit


from users.models import TravelPreference
from .services import get_weather_forecast, get_route, get_location_coordinates, get_nearby_hotels, get_nearby_restaurants, get_current_weather
from django.core.paginator import Paginator
from .models import TourPackage, Category, Destination, SearchHistory, Review, Favorite, TourReview
import bleach

from .cache_utils import get_cache_key, get_or_set_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
import logging

# Khởi tạo logger cho file hiện tại
logger = logging.getLogger(__name__)

#--Tram--#
#accountProfile
from django.shortcuts import render
from django.contrib.auth import update_session_auth_hash


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

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password_api(request):
    user = request.user
    old_password = request.data.get("old_password", "")
    new_password = request.data.get("new_password", "")

    if not user.check_password(old_password):
        return Response(
            {'message': 'Mật khẩu hiện tại không chính xác.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save()

    update_session_auth_hash(request,user)

    return Response(
        {'message': 'Đổi mật khẩu thành công.'},
        status=status.HTTP_200_OK
    )

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
from django.db.models import Q, Count
from users.models import TravelPreference # Import ở đầu file

def home(request):
    """Trang chủ đầy đủ: Ảnh static, Cache, Gợi ý AI Destination & Tour"""
    categories = Category.objects.all()
    category_slug = request.GET.get('category')
    viewed_history = request.session.get('viewed_history', [])

    # --- 1. LẤY ẢNH STATIC (Giữ nguyên logic của bạn) ---
    def get_static_images():
        base_path = os.path.join(settings.BASE_DIR, 'travel', 'static', 'images')
        results = []
        if os.path.exists(base_path):
            for folder in os.listdir(base_path):
                folder_path = os.path.join(base_path, folder)
                if os.path.isdir(folder_path):
                    images = [f"{folder}/{img}" for img in os.listdir(folder_path) 
                             if img.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                    if images:
                        results.append({
                            "name": folder.replace('-', ' ').title(),
                            "desc": f"Khám phá vẻ đẹp của {folder.title()}",
                            "images": images,
                            "folder": folder,
                            "img": images[0]
                        })
        return results

    static_results = get_or_set_cache(get_cache_key('homepage', 'images'), get_static_images, timeout=3600)

    # --- 2. TOP DESTINATIONS ---
    def get_top_destinations():
        return list(
            Destination.objects.select_related('recommendation')
            .prefetch_related('reviews')
            .annotate(num_tours=Count('packages'))
            .order_by('-recommendation__overall_score')[:6]
        )
    
    top_destinations = get_or_set_cache(get_cache_key('homepage', 'top_destinations'), get_top_destinations, timeout=600)

    # --- 3. XỬ LÝ GỢI Ý CÁ NHÂN HÓA (DESTINATION & TOUR) ---
    personalized_destinations = []
    personalized_tours = []
    user_travel_types = []
    user_locations = []

    # Lấy sở thích nếu đã đăng nhập
    if request.user.is_authenticated:
        prefs = TravelPreference.objects.filter(user=request.user)
        user_travel_types = list(prefs.exclude(travel_type='').values_list('travel_type', flat=True).distinct())
        user_locations = list(prefs.exclude(location='').values_list('location', flat=True).distinct())

    # Nếu preference trống, lấy từ lịch sử xem
    if not user_travel_types and not user_locations and viewed_history:
        recent = Destination.objects.filter(id__in=viewed_history[:5])
        # Giả sử travel_type trong Destination là CharField. Nếu là ForeignKey, dùng 'travel_type__name'
        user_travel_types = list(recent.values_list('travel_type', flat=True).distinct())
        user_locations = list(recent.values_list('location', flat=True).distinct())

    # Chỉ thực hiện lọc nếu có dữ liệu đầu vào
    if user_travel_types or user_locations:
        # Lọc Địa điểm (SỬA LỖI icontains ở đây)
        dest_q = Q()

        for t in user_travel_types:
            # travel_type là ManyToMany nên phải trỏ vào cột name của bảng TravelType
            dest_q |= Q(travel_type__name__icontains=t) 
            
        for loc in user_locations:
            # location là CharField nên chỉ cần icontains trực tiếp
            dest_q |= Q(location__icontains=loc) 

        # Thực hiện truy vấn
        personalized_destinations = (
            Destination.objects
            .select_related('recommendation')
            .annotate(num_tours=Count('packages'))
            .filter(dest_q)
            .exclude(id__in=viewed_history)
            .distinct()[:6]
        )

        # Lọc Tour
        tour_q = Q()
        for t in user_travel_types: 
            # Nếu Category.name là trường văn bản (thường là vậy)
            tour_q |= Q(category__name__icontains=t)
            
        for loc in user_locations: 
            # Đi xuyên qua ForeignKey 'destination', sau đó lọc trực tiếp trên CharField 'location'
            tour_q |= Q(destination__location__icontains=loc)
        
        personalized_tours = TourPackage.objects.select_related('destination', 'category', 'recommendation')\
            .filter(tour_q, is_active=True)\
            .exclude(destination__id__in=viewed_history)\
            .order_by('-recommendation__overall_score').distinct()[:6]

    if not personalized_tours:
        # Nếu không có gợi ý cá nhân, lấy 6 tour có điểm đánh giá cao nhất làm mặc định
        personalized_tours = TourPackage.objects.select_related('destination', 'category', 'recommendation')\
            .filter(is_active=True)\
            .order_by('-recommendation__overall_score')[:6]

    # --- 4. FEATURED TOURS (Theo danh mục) ---
    def get_featured_tours(cat_slug=None):
        qs = TourPackage.objects.select_related('destination', 'category', 'recommendation').filter(is_active=True)
        if cat_slug: qs = qs.filter(category__slug=cat_slug)
        return list(qs[:12])

    if category_slug:
        featured_tours = get_featured_tours(category_slug)
        selected_cat = categories.filter(slug=category_slug).first()
        category_name = selected_cat.name if selected_cat else "Tất cả Tour"
    else:
        featured_tours = get_or_set_cache(get_cache_key('homepage', 'featured_tours'), get_featured_tours, timeout=600)
        category_name = "Tất cả Tour"

    context = {
        "results": static_results,
        "top_destinations": top_destinations,
        "personalized_destinations": personalized_destinations,
        "personalized_tours": personalized_tours,
        "categories": categories,
        "featured_tours": featured_tours,
        "category_name": category_name,
        "selected_category": category_slug,

    }

    return render(request, 'travel/index.html', context)

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
from django.db.models import Max, F

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    
    # Query gốc: Sửa select_related để không gọi field 'overall_score'
    base_results = TourPackage.objects.filter(
        category=category, 
        is_active=True
    ).select_related('destination', 'destination__recommendation')

    # --- DỮ LIỆU ĐỂ HIỂN THỊ CÁC NÚT BẤM (UI) ---
    list_destinations = base_results.values_list('destination__name', flat=True).distinct().order_by('destination__name')
    
    price_stats = base_results.aggregate(max_p=Max('price'))
    max_price_db = price_stats['max_p'] or 10000000
    
    all_tags_raw = base_results.values_list('tags', flat=True)
    # Xử lý để tránh lỗi nếu tags là None
    unique_tags = sorted(list(set(tag for sublist in all_tags_raw if sublist for tag in sublist)))
    category_tags = [{'name': tag, 'slug': tag} for tag in unique_tags]

    # --- THỰC HIỆN LỌC KẾT QUẢ ---
    results = base_results

    # 1. Lọc địa điểm
    selected_destinations = request.GET.getlist('destination')
    if selected_destinations:
        results = results.filter(destination__name__in=selected_destinations)

    # 2. Lọc Tags
    selected_tags = request.GET.getlist('tag')
    if selected_tags:
        for tag in selected_tags:
            if tag:
                results = results.filter(tags__icontains=tag)

    # 3. Lọc Giá
    price_max = request.GET.get('price_max')
    if price_max:
        try:
            results = results.filter(price__lte=float(price_max))
        except ValueError:
            pass

    # 4. Sắp xếp
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        results = results.order_by('price')
    elif sort == 'price_desc':
        results = results.order_by('-price')
    elif sort == 'rating':
        results = results.order_by('-average_rating')
    else:
        # Mặc định theo AI Score
        results = results.order_by(F('destination__recommendation__overall_score').desc(nulls_last=True))

    return render(request, 'travel/category_detail.html', {
        'category': category,
        'category_name': category.name,
        'results': results,
        'list_destinations': list_destinations,
        'max_price_db': max_price_db,
        'category_tags': category_tags,
        'active_tags': selected_tags,
        'active_destinations': selected_destinations,
    })


# --- 4. VIEW CHI TIẾT TOUR ---
def tour_detail(request, tour_slug):
    tour = get_object_or_404(TourPackage, slug=tour_slug)
    
    # Lấy dữ liệu từ hàm trong Model
    nearby_data = tour.get_nearby_data() 
    
    context = {
        'tour': tour,
        'weather_info': nearby_data.get('weather'), 
        'related_tours': TourPackage.objects.filter(category=tour.category).exclude(id=tour.id)[:4],
    }
    return render(request, 'travel/tour_detail.html', context)

from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
@require_POST
def api_submit_tour_review(request):
    try:
        data = json.loads(request.body)
        tour_id = data.get('tour_id')
        tour = get_object_or_404(TourPackage, id=tour_id)

        # 1. LƯU REVIEW MỚI
        review = TourReview.objects.create(
            tour=tour,
            author_name=data.get('author_name', 'Khách'),
            rating=int(data.get('rating', 5)),
            comment=data.get('comment', '').strip()
        )

        # 2. CẬP NHẬT ĐIỂM TOUR (Đảm bảo .save() vào Database)
        # Gọi hàm update_rating() chúng ta vừa viết trong Model TourPackage
        tour.update_rating() 

        # 3. TRẢ VỀ JSON (Gửi kèm dữ liệu mới để JS cập nhật giao diện)
        return JsonResponse({
            'success': True,
            'review': {
                'author_name': review.author_name,
                'rating': review.rating,
                'comment': review.comment,
                'created_at': 'Vừa xong'
            },
            'new_stats': {
                'average_rating': round(tour.average_rating, 1),
                'total_reviews': tour.total_reviews
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# List destination (chưa dùng tới)
def destination_list(request):
    from django.db.models import F

    destinations = (
        Destination.objects
        .select_related('recommendation')
        .prefetch_related('images', 'travel_type')
        .order_by(F('recommendation__overall_score').desc(nulls_last=True))
    )

    return render(request, 'travel/destination_list.html', {
            'destinations': destinations
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
            travel_type='',
            location=destination.location
        )

# Search (sửa)
def search(request):
    """Trang tìm kiếm nâng cao với thời tiết và đường đi"""
    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    travel_type = request.GET.get('type', '').strip()
    min_rating = request.GET.get('min_rating', '').strip()
    max_price = request.GET.get('max_price', '').strip()

    qs = (
        Destination.objects
        .select_related('category', 'recommendation')
        .prefetch_related('images', 'travel_type')
    )

    if query:
        qs = qs.filter(
            Q(name__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query)
        )

    if location:
        qs = qs.filter(location__icontains=location)

    if travel_type:
        qs = qs.filter(travel_type__slug=travel_type)

    if min_rating:
        try:
            qs = qs.filter(avg_rating__gte=float(min_rating))
        except ValueError:
            pass

    if max_price:
        try:
            qs = qs.filter(avg_price__lte=float(max_price))
        except ValueError:
            pass

    qs = qs.distinct().order_by('-recommendation__overall_score')

    # Lưu lịch sử search
    if query:
        SearchHistory.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            user_ip=get_client_ip(request),
            results_count=qs.count()
        )

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'query': query,
        'destinations': page_obj,
        'total_results': paginator.count,
        'all_locations': Destination.objects.values_list('location', flat=True).distinct(),
        'all_types': TravelType.objects.all(),
    }
    return render(request, 'travel/search.html', context)

@never_cache
def destination_detail(request, destination_id):
    from .ai_engine import get_similar_destinations
    """Chi tiết địa điểm với thời tiết và đường đi"""
    destination = get_object_or_404(
        Destination.objects.prefetch_related('travel_type'),
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
    recommendation = RecommendationScore.objects.filter(destination=destination).first()

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

    cache_key = get_cache_key('api_search', query=query.lower()[:5]) # có thể điều chỉnh ở đây trong tương lai

    def perform_search():
        from .utils_helpers import normalize_search_text

        destinations = (
            Destination.objects
            .select_related('recommendation')
            .prefetch_related('travel_type')
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
                'avg_rating': round(dest.avg_rating, 1) if dest.avg_rating is not None else None,
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

"""review = Review.objects.create(...)
if travel_type_obj:
    review.travel_types.add(travel_type_obj)
"""
@require_POST
#@ratelimit(key='ip', rate='10/h', method='POST', block=True)
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
            # travel_types=travel_types,
            # travel_with=travel_with,
            # sentiment_score=sentiment_score,
            # positive_keywords=pos_keywords,
            # negative_keywords=neg_keywords,
            is_verified=user is not None,  # Verified if logged in
            status=Review.STATUS_APPROVED,  # Auto-approve (có thể đổi thành PENDING)
        )
        
        # Cập nhật điểm gợi ý cho destination
        rec = update_destination_scores(destination)
        

        # Lưu preference nếu user đã đăng nhập
        if user:
            save_user_preference(user, destination)
        
        logger.info(f"New review #{review.id} for {destination.name} by {author_name}")
        
        
        stats_data = {
            'avg_rating': float(rec.avg_rating if rec else destination.avg_rating or 0),
            'total_reviews': int(rec.total_reviews if rec else destination.reviews.count()),
            'overall_score': float(rec.overall_score if rec else 0),
            'positive_review_ratio': float(rec.positive_review_ratio if rec else 0)
        }

        print(f"ID Địa điểm: {destination.id} | Điểm mới: {rec.avg_rating} | Đã lưu vào DB chưa: {rec.pk is not None}")

        return JsonResponse({
            'success': True,
            'message': 'Cảm ơn bạn đã đánh giá!',
            'new_stats': stats_data
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
    """API vote review hữu ích cho cả Tour và Địa điểm"""
    import json
    from django.db.models import Q
    from .models import Review, TourReview, ReviewVote

    # 1. Đọc dữ liệu
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON không hợp lệ'}, status=400)
    else:
        data = request.POST

    review_id = data.get('review_id')
    vote_type = data.get('vote_type')
    is_tour = data.get('is_tour', False) # Flag phân biệt

    if not review_id or vote_type not in ['helpful', 'not_helpful']:
        return JsonResponse({'error': 'Tham số không hợp lệ'}, status=400)

    try:
        # 2. Xác định đối tượng Review mục tiêu
        if is_tour:
            review = TourReview.objects.get(id=int(review_id))
            vote_filter = {'tour_review': review}
        else:
            review = Review.objects.get(id=int(review_id))
            vote_filter = {'review': review}

        client_ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None

        # 3. Tìm vote cũ (Tối ưu query theo User hoặc IP)
        vote_query = Q(user_ip=client_ip)
        if user:
            vote_query |= Q(user=user)
        
        existing_vote = ReviewVote.objects.filter(vote_query, **vote_filter).first()

        # 4. Xử lý logic cập nhật hoặc tạo mới
        if existing_vote:
            old_type = existing_vote.vote_type
            if old_type == vote_type:
                return JsonResponse({
                    'success': True,
                    'message': 'Bạn đã đánh giá nội dung này rồi',
                    'helpful_count': review.helpful_count,
                    'not_helpful_count': review.not_helpful_count,
                })

            # Đổi loại vote (từ Helpful sang Not Helpful hoặc ngược lại)
            existing_vote.vote_type = vote_type
            existing_vote.save()

            if old_type == 'helpful':
                review.helpful_count = max(0, review.helpful_count - 1)
                review.not_helpful_count += 1
            else:
                review.not_helpful_count = max(0, review.not_helpful_count - 1)
                review.helpful_count += 1
        else:
            # Tạo mới ReviewVote
            create_params = {
                'user': user,
                'user_ip': client_ip,
                'vote_type': vote_type,
                **vote_filter # Tự động điền review=review hoặc tour_review=review
            }
            ReviewVote.objects.create(**create_params)

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

    except (Review.DoesNotExist, TourReview.DoesNotExist):
        return JsonResponse({'error': 'Nhận xét không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
from django.contrib.contenttypes.models import ContentType
from .models import Review, TourReview, ReviewReport
@require_POST
@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def api_report_review(request):
    import json
    # Xử lý lấy data linh hoạt
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        data = request.POST

    review_id = data.get('review_id')
    # Xử lý ép kiểu is_tour vì từ POST data nó có thể là string "true"/"false"
    is_tour_raw = data.get('is_tour', False)
    is_tour = is_tour_raw in [True, 'true', '1', 'True']
    
    reason = data.get('reason')
    description = data.get('description', '')

    # 1. Xác định Model đích
    TargetModel = TourReview if is_tour else Review

    try:
        review_obj = TargetModel.objects.get(id=int(review_id))
        content_type = ContentType.objects.get_for_model(review_obj)
        client_ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None

        # 2. Check trùng lặp (Cải tiến filter để chính xác hơn)
        report_query = Q(content_type=content_type, object_id=review_obj.id)
        if user:
            # Nếu đã login, check theo User ID
            user_check = Q(reporter_user=user)
        else:
            # Nếu khách, check theo IP và đảm bảo record đó cũng là của khách (user is null)
            user_check = Q(reporter_ip=client_ip, reporter_user__isnull=True)
        
        if ReviewReport.objects.filter(report_query & user_check).exists():
            return JsonResponse({'success': True, 'message': 'Bạn đã báo cáo đánh giá này rồi'})

        # 3. Tạo Report
        ReviewReport.objects.create(
            content_type=content_type,
            object_id=review_obj.id,
            reporter_ip=client_ip,
            reporter_user=user,
            reason=reason,
            description=bleach.clean(description)[:500] if description else ""
        )

        # 4. Cập nhật đếm và ẩn (Sử dụng F expression để tránh race condition nếu cần)
        if hasattr(review_obj, 'report_count'):
            review_obj.report_count += 1
            # Ngưỡng tự động ẩn
            if review_obj.report_count >= 3:
                # Kiểm tra xem Model có thuộc tính status không trước khi gán
                if hasattr(TargetModel, 'STATUS_PENDING'):
                    review_obj.status = TargetModel.STATUS_PENDING
                else:
                    review_obj.status = 'pending' # Hoặc 'hidden' tùy bạn đặt
            review_obj.save()

        return JsonResponse({'success': True, 'message': 'Cảm ơn bạn đã báo cáo!'})

    except (TargetModel.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'error': 'Đánh giá không tồn tại hoặc ID không hợp lệ'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# Sửa tính điểm
def update_destination_scores(destination):
    """Cập nhật điểm gợi ý và TRẢ VỀ bản ghi RecommendationScore"""
    try:
        reviews = Review.objects.filter(destination=destination)
        stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id'),
            avg_sentiment=Avg('sentiment_score')
        )
        
        avg_rating = stats['avg_rating'] or 0
        total_reviews = stats['total_reviews'] or 0
        avg_sentiment = stats['avg_sentiment'] or 0
        
        positive_reviews = reviews.filter(rating__gte=4).count()
        positive_ratio = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 0
        
        # Công thức tính Overall Score
        review_score = (avg_rating / 5) * 100
        sentiment_score = ((avg_sentiment + 1) / 2) * 100
        popularity_score = min(total_reviews * 5, 100)
        overall_score = (review_score * 0.4) + (sentiment_score * 0.3) + (popularity_score * 0.3)
        
        recommendation, _ = RecommendationScore.objects.update_or_create(
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
        
        destination.rating = avg_rating
        destination.save(update_fields=['rating'])
        return recommendation
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Lỗi update score: {e}")
        # Nếu lỗi, lấy bản ghi cũ để trả về, tránh trả về None
        rec = RecommendationScore.objects.filter(destination=destination).first()
        return rec
    
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
def toggle_destination_favorite(request, dest_id):
    destination = get_object_or_404(Destination, id=dest_id)
    fav_qs = Favorite.objects.filter(user=request.user, destination=destination)
    
    if fav_qs.exists():
        fav_qs.delete()
        is_favorite = False
    else:
        Favorite.objects.create(user=request.user, destination=destination)
        is_favorite = True
    
    return JsonResponse({'status': 'success', 'is_favorite': is_favorite})

"""Click tim →
→ toggle_favorite →
→ nếu chưa có → tạo
→ nếu có → xóa
→ quay về trang trước"""

@login_required
def toggle_tour_favorite(request, tour_id):
    tour = get_object_or_404(TourPackage, id=tour_id)
    fav_qs = Favorite.objects.filter(user=request.user, tour=tour)
    
    if fav_qs.exists():
        fav_qs.delete()
        is_favorite = False
    else:
        Favorite.objects.create(user=request.user, tour=tour)
        is_favorite = True
    
    return JsonResponse({'status': 'success', 'is_favorite': is_favorite})

# List yêu thích
@login_required
def favorite_list(request):
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related(
            'destination', 
            'destination__recommendation'
        )
        .order_by('-created_at')
    )
    return render(request, 'travel/favorites.html', {'favorites': favorites})

from django.utils.html import format_html
from django.urls import reverse

def display_review(self, obj):
    if obj.content_object:
        # Tạo URL admin cho model tương ứng (tourreview hoặc review)
        app_label = obj.content_type.app_label
        model_name = obj.content_type.model
        url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.object_id])
        return format_html('<a href="{}">[{}] {}</a>', url, model_name.upper(), obj.content_object.comment[:50])
    return "N/A"