import os
import urllib.parse
import datetime
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q
from django.utils.text import slugify

from .models import TourPackage, Category

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

    return name

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
    base_path = os.path.join(settings.BASE_DIR, 'travel', 'static', 'images')
    results = []
    try:
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
    except Exception as e:
        print(f"Lỗi khi đọc thư mục static/images: {e}")

    return render(request, 'travel/index.html', {"results": results})

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

    today = datetime.date.today()
    selected_date = None
    if date_str:
        if date_str == 'today':
            qs = qs.filter(is_available_today=True)
            selected_date = today.isoformat()
        elif date_str == 'tomorrow':
            tomorrow = today + datetime.timedelta(days=1)
            selected_date = tomorrow.isoformat()
        else:
            try:
                parsed_date = datetime.date.fromisoformat(date_str)
                selected_date = parsed_date.isoformat()
                if parsed_date == today:
                    qs = qs.filter(is_available_today=True)
            except ValueError:
                selected_date = date_str
    elif availability == 'today':
        qs = qs.filter(is_available_today=True)
        selected_date = today.isoformat()

    if price_min:
        try:
            qs = qs.filter(price__gte=int(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            qs = qs.filter(price__lte=int(price_max))
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
        qs = qs.order_by('-rating')  # sửa lại dùng rating của TourPackage

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