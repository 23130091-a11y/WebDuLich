"""
Service để tạo link tìm kiếm khách sạn và quán ăn gần đó trên Google Maps
"""
import urllib.parse

def get_nearby_hotels(lat, lon, location_name="", radius=5000):
    search_query = f"khách sạn gần {location_name}" if location_name else "khách sạn"
    
    # URL embed tìm kiếm khách sạn - sẽ hiển thị các markers khách sạn xung quanh
    encoded_query = urllib.parse.quote(search_query)
    embed_url = f"https://maps.google.com/maps?q={encoded_query}&ll={lat},{lon}&z=14&output=embed&hl=vi"
    
    # URL mở trong tab mới
    search_url = f"https://www.google.com/maps/search/{encoded_query}/@{lat},{lon},14z"
    
    return {
        'google_maps_url': embed_url,
        'search_url': search_url,
        'search_query': search_query,
        'center_lat': lat,
        'center_lon': lon,
        'location_name': location_name,
        'suggestions': [
            {'text': 'Booking.com', 'url': f"https://www.booking.com/searchresults.vi.html?ss={urllib.parse.quote(location_name)}"},
            {'text': 'Agoda', 'url': f"https://www.agoda.com/vi-vn/search?city={urllib.parse.quote(location_name)}"},
            {'text': 'Traveloka', 'url': f"https://www.traveloka.com/vi-vn/hotel/search?spec={urllib.parse.quote(location_name)}"},
        ]
    }

def get_nearby_restaurants(lat, lon, location_name="", radius=3000):
    search_query = f"quán ăn gần {location_name}" if location_name else "quán ăn"
    
    # URL embed tìm kiếm quán ăn - sẽ hiển thị các markers quán ăn xung quanh
    encoded_query = urllib.parse.quote(search_query)
    embed_url = f"https://maps.google.com/maps?q={encoded_query}&ll={lat},{lon}&z=14&output=embed&hl=vi"
    
    # URL mở trong tab mới
    search_url = f"https://www.google.com/maps/search/{encoded_query}/@{lat},{lon},14z"
    
    return {
        'google_maps_url': embed_url,
        'search_url': search_url,
        'search_query': search_query,
        'center_lat': lat,
        'center_lon': lon,
        'location_name': location_name,
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
    
    # URL embed tìm kiếm khách sạn - hiển thị markers khách sạn xung quanh địa điểm
    encoded_query = urllib.parse.quote(search_query)
    embed_url = f"https://maps.google.com/maps?q={encoded_query}&ll={lat},{lon}&z=14&output=embed&hl=vi"
    search_url = f"https://www.google.com/maps/search/{encoded_query}/@{lat},{lon},14z"
        
    return {
        'google_maps_url': embed_url,
        'search_url': search_url,
        'center_lat': lat,
        'center_lon': lon,
        'location_name': location_name,
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
    
    # URL embed tìm kiếm quán ăn - hiển thị markers quán ăn xung quanh địa điểm
    encoded_query = urllib.parse.quote(search_query)
    embed_url = f"https://maps.google.com/maps?q={encoded_query}&ll={lat},{lon}&z=14&output=embed&hl=vi"
    search_url = f"https://www.google.com/maps/search/{encoded_query}/@{lat},{lon},14z"
        
    return {
        'google_maps_url': embed_url,
        'search_url': search_url,
        'center_lat': lat,
        'center_lon': lon,
        'location_name': location_name,
        'suggestions': [
            {'name': 'Foody', 'url': f"https://www.foody.vn/search/{urllib.parse.quote(location_name)}"},
            {'name': 'ShopeeFood', 'url': f"https://shopeefood.vn/"},
        ]
    }
