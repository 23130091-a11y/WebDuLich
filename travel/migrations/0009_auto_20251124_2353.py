# travel/migrations/0009_populate_slugs.py

from django.db import migrations
from django.utils.text import slugify

def populate_slugs(apps, schema_editor):
    TourPackage = apps.get_model('travel', 'TourPackage')

    # 1. Lấy tất cả tour cần cập nhật slug (slug=None hoặc slug='')
    for tour in TourPackage.objects.filter(slug__isnull=True) | TourPackage.objects.filter(slug=''):

        base_slug = slugify(tour.name) if tour.name else str(tour.id)
        new_slug = base_slug
        count = 1

        # 2. Đảm bảo slug là DUY NHẤT trước khi lưu
        # Logic này tránh trùng lặp giữa các tour cùng tên
        while TourPackage.objects.filter(slug=new_slug).exclude(id=tour.id).exists():
            new_slug = f"{base_slug}-{count}"
            count += 1

        tour.slug = new_slug
        tour.save(update_fields=['slug'])

class Migration(migrations.Migration):

    dependencies = [
        # THAY THẾ '0008_...' bằng tên migration đầy đủ của tệp 0008_tourpa...
        # Ví dụ:
        # ('travel', '0008_tourpackage_slug'), 
        # Hoặc
        ('travel', '0008_tourpackage_slug'), # Dùng tên gần đúng nếu bạn không biết tên đầy đủ
    ]

    operations = [
        migrations.RunPython(populate_slugs, reverse_code=migrations.RunPython.noop),
    ]