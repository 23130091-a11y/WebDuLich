"""
Management command để xóa ảnh của các địa điểm
Chỉ giữ lại ảnh cho các địa điểm có tên CHÍNH XÁC là tên tỉnh/thành phố
"""

from django.core.management.base import BaseCommand
from travel.models import Destination


class Command(BaseCommand):
    help = 'Xóa ảnh của các địa điểm, chỉ giữ lại địa điểm có tên là tỉnh/thành phố'

    # Danh sách tên địa điểm CHÍNH XÁC được giữ ảnh
    EXACT_NAMES = [
        # Cần Thơ
        'cần thơ', 'can tho',
        # Đà Nẵng
        'đà nẵng', 'da nang',
        # Đà Lạt
        'đà lạt', 'da lat', 'thành phố đà lạt',
        # Hà Nội
        'hà nội', 'ha noi',
        # Hội An
        'hội an', 'hoi an', 'phố cổ hội an',
        # Huế
        'huế', 'hue',
        # Phú Quốc
        'phú quốc', 'phu quoc', 'đảo phú quốc',
        # Quảng Bình
        'quảng bình', 'quang binh',
        # Sapa
        'sapa', 'sa pa',
        # Vĩnh Long
        'vĩnh long', 'vinh long',
    ]

    def should_keep_image(self, destination):
        """Chỉ giữ ảnh nếu TÊN địa điểm khớp chính xác với tên tỉnh/thành phố"""
        name_lower = destination.name.lower().strip()
        
        for exact_name in self.EXACT_NAMES:
            if name_lower == exact_name:
                return True
        return False

    def handle(self, *args, **options):
        destinations = Destination.objects.all()
        
        removed_count = 0
        kept_count = 0
        
        for dest in destinations:
            if dest.image:
                if self.should_keep_image(dest):
                    self.stdout.write(f"✅ Giữ ảnh: {dest.name} ({dest.location})")
                    kept_count += 1
                else:
                    self.stdout.write(f"❌ Xóa ảnh: {dest.name} ({dest.location})")
                    dest.image = None
                    dest.save(update_fields=['image'])
                    removed_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f"\n=== KẾT QUẢ ===\n"
            f"Đã xóa ảnh: {removed_count} địa điểm\n"
            f"Giữ lại ảnh: {kept_count} địa điểm"
        ))
