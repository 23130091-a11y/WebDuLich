"""
Service để tạo link tìm kiếm khách sạn và quán ăn gần đó trên Google Maps
"""
import urllib.parse

import urllib.parse

def get_nearby_hotels(lat, lon, location_name="", radius=5000):
    search_query = f"khách sạn gần {location_name}" if location_name else "khách sạn"
    
    # Sử dụng cấu trúc URL Embed chính thức của Google Maps
    # Cấu trúc: https://www.google.com/maps/search/$11
    params = {
        'q': search_query,
        'center': f"{lat},{lon}",
        'z': 15,
        'hl': 'vi',
        'output': 'embed' # Tham số quan trọng nhất để chạy trong Modal
    }
    
    # Dùng URL gốc chính thống của Google để tránh bị chặn
    google_maps_url = f"https://maps.google.com/maps?{urllib.parse.urlencode(params)}"
    
    return {
        'google_maps_url': google_maps_url,
        'search_query': search_query,
        'suggestions': [
            {'text': 'Booking.com', 'url': f"https://www.booking.com/searchresults.vi.html?ss={urllib.parse.quote(location_name)}"},
            {'text': 'Agoda', 'url': f"https://www.agoda.com/vi-vn/search?city={urllib.parse.quote(location_name)}"},
            {'text': 'Traveloka', 'url': f"https://www.traveloka.com/vi-vn/hotel/search?spec={urllib.parse.quote(location_name)}"},
        ]
    }

def get_nearby_restaurants(lat, lon, location_name="", radius=3000):
    search_query = f"quán ăn gần {location_name}" if location_name else "quán ăn"
    
    params = {
        'q': search_query,
        'center': f"{lat},{lon}",
        'z': 15,
        'hl': 'vi',
        'output': 'embed'
    }
    google_maps_url = f"https://maps.google.com/maps?{urllib.parse.urlencode(params)}"
    
    return {
        'google_maps_url': google_maps_url,
        'search_query': search_query,
        'suggestions': [
            {'text': 'Foody', 'url': f"https://www.foody.vn/search/{urllib.parse.quote(location_name)}"},
            {'text': 'ShopeeFood', 'url': f"https://shopeefood.vn/search?keyword={urllib.parse.quote(location_name)}"},
            {'text': 'GrabFood', 'url': f"https://food.grab.com/vn/vi/s?q={urllib.parse.quote(location_name)}"},
        ]
    }

def get_nearby_hotels_data(self, radius=5000):
    """Trả về link tìm kiếm khách sạn cho địa điểm này"""
    lat, lon = self.latitude, self.longitude
    location_name = self.name
    search_query = f"khách sạn gần {location_name}"
        
    return {
        'google_maps_url': f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}/@{lat},{lon},15z",
        'suggestions': [
            {'name': 'Booking.com', 'url': f"https://www.booking.com/searchresults.vi.html?ss={urllib.parse.quote(location_name)}"},
            {'name': 'Agoda', 'url': f"https://www.agoda.com/vi-vn/search?city={urllib.parse.quote(location_name)}"},
        ]
    }

def get_nearby_restaurants_data(self, radius=3000):
    """Trả về link tìm kiếm quán ăn cho địa điểm này"""
    lat, lon = self.latitude, self.longitude
    location_name = self.name
    search_query = f"quán ăn gần {location_name}"
        
    return {
        'google_maps_url': f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}/@{lat},{lon},15z",
        'suggestions': [
        {'name': 'Foody', 'url': f"https://www.foody.vn/search/{urllib.parse.quote(location_name)}"},
        {'name': 'ShopeeFood', 'url': f"https://shopeefood.vn/"},
    ]
}
