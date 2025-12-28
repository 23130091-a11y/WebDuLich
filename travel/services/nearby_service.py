"""
Service để tạo link tìm kiếm khách sạn và quán ăn gần đó trên Google Maps
"""
import urllib.parse


def get_nearby_hotels(lat, lon, location_name="", radius=5000, limit=5):
    """
    Tạo thông tin tìm kiếm khách sạn gần đó
    Trả về link Google Maps để người dùng tự tìm
    """
    search_query = f"khách sạn gần {location_name}" if location_name else "khách sạn"
    
    return {
        'google_maps_url': f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}/@{lat},{lon},15z",
        'search_query': search_query,
        'suggestions': [
            {'type': 'tip', 'text': 'Tìm trên Booking.com', 'url': f"https://www.booking.com/searchresults.vi.html?ss={urllib.parse.quote(location_name)}&checkin=&checkout="},
            {'type': 'tip', 'text': 'Tìm trên Agoda', 'url': f"https://www.agoda.com/vi-vn/search?city={urllib.parse.quote(location_name)}"},
            {'type': 'tip', 'text': 'Tìm trên Traveloka', 'url': f"https://www.traveloka.com/vi-vn/hotel/search?spec={urllib.parse.quote(location_name)}"},
        ]
    }


def get_nearby_restaurants(lat, lon, location_name="", radius=3000, limit=5):
    """
    Tạo thông tin tìm kiếm quán ăn gần đó
    Trả về link Google Maps để người dùng tự tìm
    """
    search_query = f"quán ăn gần {location_name}" if location_name else "quán ăn"
    
    return {
        'google_maps_url': f"https://www.google.com/maps/search/{urllib.parse.quote(search_query)}/@{lat},{lon},15z",
        'search_query': search_query,
        'suggestions': [
            {'type': 'tip', 'text': 'Tìm trên Foody', 'url': f"https://www.foody.vn/search/{urllib.parse.quote(location_name)}"},
            {'type': 'tip', 'text': 'Tìm trên ShopeeFood', 'url': f"https://shopeefood.vn/"},
            {'type': 'tip', 'text': 'Tìm trên GrabFood', 'url': f"https://food.grab.com/vn/vi/"},
        ]
    }
