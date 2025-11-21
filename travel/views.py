from django.shortcuts import render

# Create your views here.
import os
from django.conf import settings
from django.shortcuts import render

from django.template.loader import get_template

get_template('travel/index.html')  # Nếu lỗi, Django sẽ báo ở đây


def home(request):
    base_path = os.path.join(settings.BASE_DIR, 'travel', 'static', 'images')
    results = []

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
                    "images": images,  # 🔹 chứa tất cả ảnh
                    "folder": folder,
                    "img": images[0]  # 🔹 ảnh đầu tiên làm thumbnail
                })

    return render(request, 'travel/index.html', {"results": results})
