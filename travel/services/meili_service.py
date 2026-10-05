"""
Meilisearch integration — search engine cho Destination + TourPackage.

Dùng Meilisearch Cloud: set MEILI_HOST + MEILI_API_KEY (xem .env.example).
Khi chưa cấu hình (hoặc cloud gặp sự cố), mọi hàm ở đây đều no-op / trả None
để caller fallback về ORM search — tính năng tìm kiếm không bao giờ chết
theo Meilisearch.

Tiếng Việt không nằm trong danh sách tokenization được Charabia tối ưu
(Meilisearch dùng Latin pipeline mặc định — KHÔNG tự bỏ dấu). Vì vậy mỗi
document index kèm field `search_text` chứa bản không dấu của name/location,
tái dùng normalize_search_text() của utils_helpers. Nhờ đó query "da nang"
vẫn khớp "Đà Nẵng" qua typo tolerance của Meilisearch.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import meilisearch
    MEILI_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - chỉ khi thiếu dependency
    meilisearch = None
    MEILI_IMPORT_ERROR = exc

# Mỗi model một index — document id là DB id, prefix tránh tròn giữa các
# môi trường dùng chung một cloud project (dev/staging).
DESTINATIONS_INDEX = 'destinations_v1'
TOURS_INDEX = 'tours_v1'

_client = None


def is_enabled() -> bool:
    """Meilisearch chỉ bật khi import SDK OK + có host + có key."""
    return bool(meilisearch and settings.MEILI_HOST and settings.MEILI_API_KEY)


def get_client():
    """Client singleton. Trả None nếu chưa cấu hình / SDK chưa cài."""
    global _client
    if not is_enabled():
        return None
    if _client is None:
        try:
            _client = meilisearch.Client(
                settings.MEILI_HOST, settings.MEILI_API_KEY
            )
        except Exception as exc:
            logger.error("Không tạo được Meilisearch client: %s", exc)
            return None
    return _client


def configure_index(index_uid: str, searchable, filterable=(), sortable=()) -> bool:
    """
    Cấu hình index một lần (idempotent — task update trên Meilisearch được
    enqueue và áp dụng async; gọi lại với cùng config không tốn thêm gì).
    Trả True nếu đã gửi được task, False khi lỗi/timeout.
    """
    client = get_client()
    if client is None:
        return False
    try:
        index = client.index(index_uid)
        index.update({
            'searchableAttributes': list(searchable),
            'filterableAttributes': list(filterable),
            'sortableAttributes': list(sortable),
        })
        return True
    except Exception as exc:
        logger.warning("Cấu hình Meilisearch index %s thất bại: %s", index_uid, exc)
        return False


# ---------------------------------------------------------------------------
# Serialization — mỗi hàm map 1 object Django → document cho Meilisearch
# ---------------------------------------------------------------------------

def _dest_search_text(dest) -> str:
    """Chuỗi index chính: có dấu + không dấu + aliases địa danh."""
    from ..utils_helpers.text_utils import (
        get_search_variants, normalize_search_text,
    )
    parts = [dest.name, dest.location or '']
    parts.append(normalize_search_text(dest.name))
    parts.append(normalize_search_text(dest.location or ''))
    # Alias "sai gon" → "ho chi minh" giúp query nói trúng tên phổ biến
    variants = get_search_variants(dest.name) + get_search_variants(dest.location or '')
    parts.extend(variants)
    seen, unique = set(), []
    for p in parts:
        if p and p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
    return ' '.join(unique)


def destination_to_document(dest) -> dict:
    """Destination → document. Giá rating/score float để filter/sort."""
    try:
        rec_score = dest.recommendation.overall_score if dest.recommendation else 0.0
    except Exception:
        rec_score = 0.0
    return {
        'id': dest.id,
        'name': dest.name,
        'slug': dest.slug,
        'location': dest.location or '',
        'search_text': _dest_search_text(dest),
        'category': dest.category.name if dest.category else '',
        'travel_types': [t.slug for t in dest.travel_type.all()],
        'avg_rating': dest.avg_rating or 0.0,
        'avg_price': float(dest.avg_price) if dest.avg_price else 0.0,
        'is_popular': dest.is_popular,
        'overall_score': float(rec_score),
    }


def tour_to_document(tour) -> dict:
    """TourPackage → document."""
    try:
        rec_score = tour.recommendation.overall_score if tour.recommendation else 0.0
    except Exception:
        rec_score = 0.0
    dest = tour.destination
    variants = (
        get_variants_safe(tour.name)
        + get_variants_safe(dest.name if dest else '')
        + get_variants_safe(dest.location if dest else '')
    )
    base = [tour.name, dest.name if dest else '', dest.location if dest else '']
    return {
        'id': tour.id,
        'name': tour.name,
        'slug': tour.slug,
        'search_text': ' '.join(base + variants),
        'destination': dest.name if dest else '',
        'destination_id': dest.id if dest else None,
        'category': tour.category.name if tour.category else '',
        'avg_rating': tour.average_rating or 0.0,
        'price': float(tour.price) if tour.price else 0.0,
        'duration': tour.duration,
        'is_active': tour.is_active,
        'overall_score': float(rec_score),
    }


def get_variants_safe(text: str) -> list:
    """get_search_variants nhưng an toàn với input rỗng/None."""
    if not text:
        return []
    from ..utils_helpers.text_utils import get_search_variants
    try:
        return [v for v in get_search_variants(text) if v]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Sync DB → Meilisearch
# ---------------------------------------------------------------------------

def sync_destination(dest) -> bool:
    """Index/cập nhật 1 Destination. Best-effort, không raise."""
    client = get_client()
    if client is None:
        return False
    try:
        client.index(DESTINATIONS_INDEX).add_documents(
            [destination_to_document(dest)]
        )
        return True
    except Exception as exc:
        logger.warning(
            "Sync Meilisearch thất bại (Destination#%s): %s", dest.pk, exc
        )
        return False


def sync_tour(tour) -> bool:
    """Index/cập nhật 1 TourPackage. Best-effort, không raise."""
    client = get_client()
    if client is None:
        return False
    try:
        client.index(TOURS_INDEX).add_documents([tour_to_document(tour)])
        return True
    except Exception as exc:
        logger.warning("Sync Meilisearch thất bại (TourPackage#%s): %s", tour.pk, exc)
        return False


def delete_document(index_uid: str, obj_id) -> bool:
    """Xóa 1 document theo DB id. Best-effort, không raise."""
    client = get_client()
    if client is None:
        return False
    try:
        client.index(index_uid).delete_document(obj_id)
        return True
    except Exception as exc:
        logger.warning("Delete Meilisearch doc thất bại (%s#%s): %s", index_uid, obj_id, exc)
        return False


def bulk_reindex(batch_size: int = 500) -> dict:
    """
    Reindex toàn bộ Destination + TourPackage (dùng cho management command
    và lần chạy đầu). Trả về số lượng đã submit theo từng index.
    """
    from ..models import Destination, TourPackage

    if not is_enabled():
        return {'error': 'Meilisearch chưa cấu hình (MEILI_HOST/MEILI_API_KEY)'}

    configure_index(
        DESTINATIONS_INDEX,
        searchable=['name', 'location', 'search_text'],
        filterable=['category', 'travel_types', 'is_popular', 'avg_rating'],
        sortable=['overall_score', 'avg_rating'],
    )
    configure_index(
        TOURS_INDEX,
        searchable=['name', 'destination', 'search_text'],
        filterable=['category', 'is_active', 'avg_rating', 'price'],
        sortable=['overall_score', 'price', 'avg_rating'],
    )

    stats = {}
    dest_index = get_client().index(DESTINATIONS_INDEX)
    dest_count = 0
    dests = (
        Destination.objects
        .select_related('category', 'recommendation')
        .prefetch_related('travel_type')
        .iterator(chunk_size=batch_size)
    )
    batch = []
    for dest in dests:
        batch.append(destination_to_document(dest))
        if len(batch) >= batch_size:
            dest_index.add_documents(batch)
            dest_count += len(batch)
            batch = []
    if batch:
        dest_index.add_documents(batch)
        dest_count += len(batch)
    stats['destinations'] = dest_count

    tour_index = get_client().index(TOURS_INDEX)
    tour_count = 0
    tours = (
        TourPackage.objects
        .select_related('destination', 'category', 'recommendation')
        .iterator(chunk_size=batch_size)
    )
    batch = []
    for tour in tours:
        batch.append(tour_to_document(tour))
        if len(batch) >= batch_size:
            tour_index.add_documents(batch)
            tour_count += len(batch)
            batch = []
    if batch:
        tour_index.add_documents(batch)
        tour_count += len(batch)
    stats['tours'] = tour_count

    logger.info("Meilisearch reindex submitted: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Search — trả về list document hoặc None (để caller fallback ORM)
# ---------------------------------------------------------------------------

def _postprocess_query(query: str) -> str:
    """
    Query có dấu → thêm bản không dấu để khớp search_text đã index.
    VD: "đà nẵng" → "đà nẵng da nang". Meilisearch xử lý OR giữa các token,
    nên cả bản có dấu lẫn không dấu đều có cơ hội khớp.
    """
    from ..utils_helpers.text_utils import get_search_variants
    variants = get_search_variants(query)
    return ' '.join(variants) if variants else query


def search_destinations(query: str, limit: int = 10):
    """Tìm destinations. Trả None nếu chưa cấu hình/lỗi → caller fallback ORM."""
    client = get_client()
    if client is None:
        return None
    try:
        result = client.index(DESTINATIONS_INDEX).search(
            _postprocess_query(query),
            {'limit': limit, 'attributesToRetrieve': ['*']},
        )
        return result.get('hits', [])
    except Exception as exc:
        logger.warning("Meilisearch search destinations lỗi: %s", exc)
        return None


def search_tours(query: str, limit: int = 10):
    """Tìm tours. Trả None nếu chưa cấu hình/lỗi → caller fallback ORM."""
    client = get_client()
    if client is None:
        return None
    try:
        result = client.index(TOURS_INDEX).search(
            _postprocess_query(query),
            {'limit': limit, 'attributesToRetrieve': ['*']},
        )
        return result.get('hits', [])
    except Exception as exc:
        logger.warning("Meilisearch search tours lỗi: %s", exc)
        return None
