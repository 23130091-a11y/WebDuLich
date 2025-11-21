from django.db import models

# Create your models here.
# Bảng địa điểm
class Destination(models.Model):
    name = models.CharField(max_length=100)
    travel_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='destinations/', blank=True)