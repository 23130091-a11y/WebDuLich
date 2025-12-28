"""
Gán ảnh cho các địa điểm du lịch từ thư mục static/images
Chạy: python manage.py assign_images
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from travel.models import Destination
import os
import shutil


class Command(BaseCommand):
    help = 'Gán ảnh cho các địa điểm du lịch'

    def handle(self, *args, **options):
        # Mapping tên địa điểm với thư mục ảnh
        image_mapping = {
            'Hà Nội': 'hanoi',
            'Ha Noi': 'hanoi',
            'Đà Nẵng': 'danang',
            'Da Nang': 'danang',
            'Đà Lạt': 'dalat',
            'Da Lat': 'dalat',
            'Huế': 'hue',
            'Hue': 'hue',
            'Hội An': 'hoian',
            'Hoi An': 'hoian',
            'Nha Trang': 'nhatrang',
            'Phú Quốc': 'phuquoc',
            'Phu Quoc': 'phuquoc',
            'Sa Pa': 'sapa',
            'Sapa': 'sapa',
            'Hạ Long': 'vinhalong',
            'Ha Long': 'vinhalong',
            'Vịnh Hạ Long': 'vinhalong',
            'Cần Thơ': 'cantho',
            'Can Tho': 'cantho',
            'Quảng Bình': 'quangbinh',
            'Quang Binh': 'quangbinh',
            'TP Hồ Chí Minh': 'hanoi',  # Dùng tạm
            'Tp Hcm': 'hanoi',
            'Ho Chi Minh City': 'hanoi',
        }
        
        static_images_path = os.path.join(settings.BASE_DIR, 'travel', 'static', 'images')
        media_path = os.path.join(settings.BASE_DIR, 'media', 'destinations')
        
        # Tạo thư mục media nếu chưa có
        os.makedirs(media_path, exist_ok=True)
        
        destinations = Destination.objects.all()
        updated = 0
        
        self.stdout.write(f'📷 Đang gán ảnh cho {destinations.count()} địa điểm...\n')
        
        for dest in destinations:
            # Tìm thư mục ảnh phù hợp
            folder = None
            
            # Kiểm tra theo tên
            for key, value in image_mapping.items():
                if key.lower() in dest.name.lower() or key.lower() in dest.location.lower():
                    folder = value
                    break
            
            if not folder:
                # Thử tìm theo location
                for key, value in image_mapping.items():
                    if key.lower() in dest.location.lower():
                        folder = value
                        break
            
            if folder:
                folder_path = os.path.join(static_images_path, folder)
                if os.path.exists(folder_path):
                    # Lấy ảnh đầu tiên trong thư mục
                    images = [f for f in os.listdir(folder_path) 
                              if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                    
                    if images:
                        # Copy ảnh vào media
                        src_image = os.path.join(folder_path, images[0])
                        dest_filename = f"{dest.id}_{folder}.jpg"
                        dest_image = os.path.join(media_path, dest_filename)
                        
                        try:
                            shutil.copy2(src_image, dest_image)
                            
                            # Cập nhật database
                            dest.image = f"destinations/{dest_filename}"
                            dest.save(update_fields=['image'])
                            
                            self.stdout.write(f'  ✓ {dest.name} → {folder}/{images[0]}')
                            updated += 1
                        except Exception as e:
                            self.stdout.write(f'  ✗ {dest.name}: {str(e)}')
            else:
                self.stdout.write(f'  ⚠ {dest.name} ({dest.location}) - Không tìm thấy ảnh phù hợp')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Đã gán ảnh cho {updated}/{destinations.count()} địa điểm'))
