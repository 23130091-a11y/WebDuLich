# Service tính đường đi sử dụng OSRM (Open Source Routing Machine)
import requests
import math

def get_route(start_lat, start_lon, end_lat, end_lon):
    """
    Lấy thông tin đường đi từ điểm A đến điểm B
    Sử dụng OSRM demo server (miễn phí)
    """
    try:
        # OSRM demo server
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data['code'] != 'Ok':
            return {'error': 'Không tìm được đường đi'}
        
        route = data['routes'][0]
        
        # Khoảng cách (km)
        distance_km = route['distance'] / 1000
        
        # Thời gian (phút)
        duration_min = route['duration'] / 60
        
        # Tọa độ đường đi (để vẽ trên bản đồ)
        geometry = route['geometry']['coordinates']
        
        # Hướng dẫn từng bước (nếu có)
        steps = []
        if 'legs' in route:
            for leg in route['legs']:
                if 'steps' in leg:
                    for step in leg['steps']:
                        if 'maneuver' in step:
                            steps.append({
                                'instruction': step['maneuver'].get('instruction', ''),
                                'distance': step['distance'],
                                'duration': step['duration']
                            })
        
        return {
            'distance_km': round(distance_km, 2),
            'duration_min': round(duration_min, 0),
            'duration_hours': round(duration_min / 60, 1),
            'geometry': geometry,
            'steps': steps[:10]  # Giới hạn 10 bước đầu
        }
        
    except Exception as e:
        # Fallback: tính khoảng cách đường chim bay
        distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        return {
            'distance_km': distance,
            'duration_min': round(distance * 1.5),  # Ước tính: 1km ~ 1.5 phút
            'duration_hours': round(distance / 60, 1),
            'geometry': [[start_lon, start_lat], [end_lon, end_lat]],
            'steps': [],
            'note': 'Khoảng cách ước tính (đường chim bay)'
        }


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa 2 điểm (Haversine formula)
    Trả về khoảng cách tính bằng km
    """
    R = 6371  # Bán kính trái đất (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return round(distance, 2)


def get_location_coordinates(location_name):
    """
    Lấy tọa độ từ tên địa điểm sử dụng Nominatim (OpenStreetMap)
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': location_name + ', Vietnam',
            'format': 'json',
            'limit': 1
        }
        headers = {
            'User-Agent': 'TravelWebApp/1.0'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        
        if data and len(data) > 0:
            return {
                'lat': float(data[0]['lat']),
                'lon': float(data[0]['lon']),
                'display_name': data[0]['display_name']
            }
        
        return None
        
    except Exception as e:
        return None
