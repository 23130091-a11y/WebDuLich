# Distance Helper - Wrapper functions cho distance calculation
# Requirements: 2.1, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5

import logging
from datetime import datetime
from .routing_service import get_location_coordinates, calculate_distance

logger = logging.getLogger(__name__)

# Tọa độ cứng cho các tỉnh thành phổ biến (tránh gọi API)
VIETNAM_COORDINATES = {
    'hà nội': {'lat': 21.0285, 'lon': 105.8542, 'display_name': 'Hà Nội'},
    'ha noi': {'lat': 21.0285, 'lon': 105.8542, 'display_name': 'Hà Nội'},
    'tp hồ chí minh': {'lat': 10.8231, 'lon': 106.6297, 'display_name': 'TP Hồ Chí Minh'},
    'hồ chí minh': {'lat': 10.8231, 'lon': 106.6297, 'display_name': 'TP Hồ Chí Minh'},
    'hcm': {'lat': 10.8231, 'lon': 106.6297, 'display_name': 'TP Hồ Chí Minh'},
    'sài gòn': {'lat': 10.8231, 'lon': 106.6297, 'display_name': 'TP Hồ Chí Minh'},
    'đà nẵng': {'lat': 16.0544, 'lon': 108.2022, 'display_name': 'Đà Nẵng'},
    'da nang': {'lat': 16.0544, 'lon': 108.2022, 'display_name': 'Đà Nẵng'},
    'hải phòng': {'lat': 20.8449, 'lon': 106.6881, 'display_name': 'Hải Phòng'},
    'cần thơ': {'lat': 10.0452, 'lon': 105.7469, 'display_name': 'Cần Thơ'},
    'đà lạt': {'lat': 11.9404, 'lon': 108.4583, 'display_name': 'Đà Lạt'},
    'da lat': {'lat': 11.9404, 'lon': 108.4583, 'display_name': 'Đà Lạt'},
    'nha trang': {'lat': 12.2388, 'lon': 109.1967, 'display_name': 'Nha Trang'},
    'huế': {'lat': 16.4637, 'lon': 107.5909, 'display_name': 'Huế'},
    'hue': {'lat': 16.4637, 'lon': 107.5909, 'display_name': 'Huế'},
    'hội an': {'lat': 15.8801, 'lon': 108.3380, 'display_name': 'Hội An'},
    'hoi an': {'lat': 15.8801, 'lon': 108.3380, 'display_name': 'Hội An'},
    'phú quốc': {'lat': 10.2899, 'lon': 103.9840, 'display_name': 'Phú Quốc'},
    'phu quoc': {'lat': 10.2899, 'lon': 103.9840, 'display_name': 'Phú Quốc'},
    'hạ long': {'lat': 20.9101, 'lon': 107.1839, 'display_name': 'Hạ Long'},
    'ha long': {'lat': 20.9101, 'lon': 107.1839, 'display_name': 'Hạ Long'},
    'quảng ninh': {'lat': 20.9101, 'lon': 107.1839, 'display_name': 'Quảng Ninh'},
    'sa pa': {'lat': 22.3364, 'lon': 103.8438, 'display_name': 'Sa Pa'},
    'sapa': {'lat': 22.3364, 'lon': 103.8438, 'display_name': 'Sa Pa'},
    'hà giang': {'lat': 22.8233, 'lon': 104.9836, 'display_name': 'Hà Giang'},
    'ha giang': {'lat': 22.8233, 'lon': 104.9836, 'display_name': 'Hà Giang'},
    'đồng văn': {'lat': 23.2767, 'lon': 105.3633, 'display_name': 'Đồng Văn, Hà Giang'},
    'dong van': {'lat': 23.2767, 'lon': 105.3633, 'display_name': 'Đồng Văn, Hà Giang'},
    'ninh bình': {'lat': 20.2506, 'lon': 105.9745, 'display_name': 'Ninh Bình'},
    'ninh binh': {'lat': 20.2506, 'lon': 105.9745, 'display_name': 'Ninh Bình'},
    'quảng bình': {'lat': 17.4656, 'lon': 106.6222, 'display_name': 'Quảng Bình'},
    'quang binh': {'lat': 17.4656, 'lon': 106.6222, 'display_name': 'Quảng Bình'},
    'quảng ngãi': {'lat': 15.1214, 'lon': 108.8044, 'display_name': 'Quảng Ngãi'},
    'quang ngai': {'lat': 15.1214, 'lon': 108.8044, 'display_name': 'Quảng Ngãi'},
    'quy nhơn': {'lat': 13.7830, 'lon': 109.2197, 'display_name': 'Quy Nhơn'},
    'quy nhon': {'lat': 13.7830, 'lon': 109.2197, 'display_name': 'Quy Nhơn'},
    'bình định': {'lat': 13.7830, 'lon': 109.2197, 'display_name': 'Bình Định'},
    'vũng tàu': {'lat': 10.4114, 'lon': 107.1362, 'display_name': 'Vũng Tàu'},
    'vung tau': {'lat': 10.4114, 'lon': 107.1362, 'display_name': 'Vũng Tàu'},
    'phan thiết': {'lat': 10.9289, 'lon': 108.1021, 'display_name': 'Phan Thiết'},
    'phan thiet': {'lat': 10.9289, 'lon': 108.1021, 'display_name': 'Phan Thiết'},
    'mũi né': {'lat': 10.9333, 'lon': 108.2833, 'display_name': 'Mũi Né'},
    'mui ne': {'lat': 10.9333, 'lon': 108.2833, 'display_name': 'Mũi Né'},
}

# Cache cho geocoding API
_geocode_cache = {}

# Cache cho route API
_route_cache = {}


def get_location_coordinates_safe(location_name):
    """
    Lấy tọa độ từ tên địa điểm. Ưu tiên dùng tọa độ cứng, fallback sang API.
    
    Args:
        location_name: Tên địa điểm (string)
        
    Returns:
        dict với 'lat', 'lon', 'display_name' hoặc None nếu lỗi
        
    Requirements: 2.1, 2.3, 2.4
    """
    if not location_name or not location_name.strip():
        return None
    
    location_key = location_name.strip().lower()
    
    # Kiểm tra tọa độ cứng trước
    if location_key in VIETNAM_COORDINATES:
        return VIETNAM_COORDINATES[location_key]
    
    # Kiểm tra cache
    if location_key in _geocode_cache:
        return _geocode_cache[location_key]
    
    # Gọi API geocoding
    try:
        result = get_location_coordinates(location_name.strip())
        _geocode_cache[location_key] = result
        return result
    except Exception as e:
        logger.warning(f"Geocoding error for '{location_name}': {e}")
        _geocode_cache[location_key] = None
        return None


def get_route_safe(start_lat, start_lon, end_lat, end_lon):
    """
    Tính khoảng cách đường bộ sử dụng OSRM API.
    Có cache và fallback sang Haversine nếu API fail.
    
    Args:
        start_lat, start_lon: Tọa độ điểm xuất phát
        end_lat, end_lon: Tọa độ điểm đến
        
    Returns:
        dict với 'distance_km', 'duration_min', 'duration_hours', và có thể có 'note'
    """
    import requests
    
    # Tạo cache key
    cache_key = f"{start_lat:.4f},{start_lon:.4f}-{end_lat:.4f},{end_lon:.4f}"
    
    # Kiểm tra cache
    if cache_key in _route_cache:
        return _route_cache[cache_key]
    
    # Thử dùng OSRM API
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {'overview': 'false'}  # Không cần geometry để nhanh hơn
        
        response = requests.get(url, params=params, timeout=3)  # Timeout 3s
        data = response.json()
        
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            distance_km = route['distance'] / 1000
            duration_min = route['duration'] / 60
            
            # Điều chỉnh thời gian: OSRM tính theo tốc độ lý tưởng
            # Nhân với 1.8 để phù hợp với thực tế đường Việt Nam (đường núi, giao thông)
            adjusted_duration_min = duration_min * 1.8
            
            result = {
                'distance_km': round(distance_km, 2),
                'duration_min': int(adjusted_duration_min),
                'duration_hours': round(adjusted_duration_min / 60, 1),
                'note': None,
                'error': None
            }
            _route_cache[cache_key] = result
            return result
            
    except Exception as e:
        logger.warning(f"OSRM API error: {e}")
    
    # Fallback: Haversine với hệ số điều chỉnh
    try:
        haversine_distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)
        
        # Hệ số điều chỉnh x1.2 cho đường bộ
        estimated_distance = haversine_distance * 1.2
        # Tốc độ trung bình 45km/h cho đường Việt Nam
        duration_hours = estimated_distance / 45
        
        result = {
            'distance_km': round(estimated_distance, 2),
            'duration_min': int(duration_hours * 60),
            'duration_hours': round(duration_hours, 1),
            'note': 'Ước tính',
            'error': None
        }
        _route_cache[cache_key] = result
        return result
        
    except Exception as e:
        logger.error(f"Distance calculation error: {e}")
        return {
            'distance_km': None,
            'duration_min': None,
            'duration_hours': None,
            'error': 'Không thể tính khoảng cách'
        }


def calculate_distance_for_destination(from_coords, destination):
    """
    Tính khoảng cách từ vị trí người dùng đến destination.
    
    Args:
        from_coords: dict với 'lat', 'lon'
        destination: Destination object
        
    Returns:
        dict với 'distance_km', 'duration_min', 'duration_hours', 'error'
    """
    if not from_coords:
        return {'error': 'Không có tọa độ điểm xuất phát'}
    
    if not destination.latitude or not destination.longitude:
        return {'error': 'Địa điểm không có tọa độ'}
    
    return get_route_safe(
        from_coords['lat'],
        from_coords['lon'],
        destination.latitude,
        destination.longitude
    )


def calculate_distance_for_tour(from_coords, tour):
    """
    Tính khoảng cách từ vị trí người dùng đến tour.
    Ưu tiên dùng tọa độ start của tour, fallback sang destination.
    
    Args:
        from_coords: dict với 'lat', 'lon'
        tour: TourPackage object
        
    Returns:
        dict với 'distance_km', 'duration_min', 'duration_hours', 'error'
    """
    if not from_coords:
        return {'error': 'Không có tọa độ điểm xuất phát'}
    
    # Ưu tiên tọa độ start của tour
    end_lat = None
    end_lon = None
    
    if tour.start_latitude and tour.start_longitude:
        end_lat = float(tour.start_latitude)
        end_lon = float(tour.start_longitude)
    elif tour.destination and tour.destination.latitude and tour.destination.longitude:
        end_lat = tour.destination.latitude
        end_lon = tour.destination.longitude
    
    if not end_lat or not end_lon:
        return {'error': 'Tour không có tọa độ'}
    
    return get_route_safe(
        from_coords['lat'],
        from_coords['lon'],
        end_lat,
        end_lon
    )


def calculate_distances_for_results(from_coords, destinations, tours):
    """
    Tính khoảng cách cho danh sách kết quả tìm kiếm.
    
    Args:
        from_coords: dict với 'lat', 'lon' hoặc None
        destinations: QuerySet hoặc list của Destination objects
        tours: QuerySet hoặc list của TourPackage objects
        
    Returns:
        dict với key là 'dest_{id}' hoặc 'tour_{id}', value là distance info
        
    Requirements: 4.1, 4.2, 4.5
    """
    if not from_coords:
        return {}
    
    distance_info = {}
    
    # Giới hạn số lượng tính toán để tránh chậm
    max_calculations = 12
    count = 0
    
    # Tính cho destinations
    for dest in destinations:
        if count >= max_calculations:
            break
        key = f'dest_{dest.id}'
        distance_info[key] = calculate_distance_for_destination(from_coords, dest)
        count += 1
    
    # Tính cho tours
    for tour in tours:
        if count >= max_calculations:
            break
        key = f'tour_{tour.id}'
        distance_info[key] = calculate_distance_for_tour(from_coords, tour)
        count += 1
    
    return distance_info


def parse_travel_date(date_string):
    """
    Parse và validate travel_date từ string.
    
    Args:
        date_string: String dạng 'YYYY-MM-DD'
        
    Returns:
        date object hoặc None nếu invalid
        
    Requirements: 6.3
    """
    if not date_string or not date_string.strip():
        return None
    
    try:
        return datetime.strptime(date_string.strip(), '%Y-%m-%d').date()
    except ValueError:
        logger.warning(f"Invalid date format: {date_string}")
        return None


def format_duration(duration_min):
    """
    Format duration từ phút sang string dễ đọc.
    
    Args:
        duration_min: Số phút (int hoặc float)
        
    Returns:
        String dạng "X giờ Y phút" hoặc "Y phút"
    """
    if not duration_min:
        return ""
    
    duration_min = int(duration_min)
    
    if duration_min < 60:
        return f"{duration_min} phút"
    
    hours = duration_min // 60
    minutes = duration_min % 60
    
    if minutes == 0:
        return f"{hours} giờ"
    
    return f"{hours} giờ {minutes} phút"
