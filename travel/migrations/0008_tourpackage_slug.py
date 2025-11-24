# travel/migrations/0008_...py (Chỉ thêm cột, không thêm unique index)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('travel', '0007_tourpackage_address_detail_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tourpackage',
            name='slug',
            # Giữ blank=True, THÊM null=True, và TẠM THỜI BỎ unique=True
            field=models.SlugField(max_length=255, blank=True, null=True), 
        ),
    ]