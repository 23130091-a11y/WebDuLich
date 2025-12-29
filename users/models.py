from django.contrib.auth.models import AbstractUser
from django.db import models

# -----------------------------
# Bảng người dùng chính
# -----------------------------
class User(AbstractUser):
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # có yêu cầu username

# -----------------------------
# Bảng lấy thông tin user chọn
# -----------------------------
class TravelPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='preferences')
    travel_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100)

    class Meta:
        unique_together = ('user', 'travel_type', 'location')
