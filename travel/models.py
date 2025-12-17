# D:\LT_Python\PyWeb\DoAnWeb\WebDuLich\travel\models.py
from tokenize import blank_re

from django.conf import settings
from django.db import models
from taggit.managers import TaggableManager
from users.models import User
from django.utils.text import slugify

class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

# ----------------------------------------------------------------------
# 1. Category Model
# ----------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to='categories/images/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# ----------------------------------------------------------------------
# 2. Destination Model
# ----------------------------------------------------------------------
class Destination(models.Model):
    category = models.ForeignKey(
        'Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    score = models.FloatField(default=0.0)
    is_popular = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, max_length=200)
    tags = TaggableManager()

    def __str__(self):
        return self.name

# ----------------------------------------------------------------------
# 3. DestinationImage Model
# ----------------------------------------------------------------------
class DestinationImage(models.Model):
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='destinations/images/', blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.destination.name}"

# ----------------------------------------------------------------------
# 4. TourPackage Model
# ----------------------------------------------------------------------
class TourPackage(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='tour_packages',
        null=True,    
        blank=True
    )
    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,
        related_name='packages'
    )
    name = models.CharField(max_length=255)
    duration = models.IntegerField(help_text="Duration in days")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    address_detail = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Địa chỉ đón/trả khách hoặc địa chỉ chính"
    )
    details = models.TextField()
    is_active = models.BooleanField(default=True)
    image_main = models.ImageField(upload_to='packages/main_images/', blank=True, null=True)
    tags = TaggableManager(blank=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    is_available_today = models.BooleanField(
        default=False,
        help_text="Check nếu tour này khả dụng trong ngày hiện tại hoặc tương lai gần."
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        # Nếu chưa gán category, tự động lấy từ destination
        if not self.category and self.destination and self.destination.category:
            self.category = self.destination.category

        # Nếu chưa có slug, tự động sinh từ name
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} at {self.destination.name}"

class TourImage(models.Model):
    tour = models.ForeignKey(TourPackage, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='packages/gallery/')
    caption = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Image for {self.tour.name}"