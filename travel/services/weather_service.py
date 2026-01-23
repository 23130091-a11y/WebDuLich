# Service lấy thông tin thời tiết
# Ưu tiên OpenWeatherMap (chính xác hơn), fallback sang Open-Meteo
import requests
import os
from datetime import datetime
from django.conf import settings

# API Key từ settings hoặc environment
OPENWEATHERMAP_API_KEY = getattr(settings, 'OPENWEATHERMAP_API_KEY', None) or os.environ.get('OPENWEATHERMAP_API_KEY', '')

# Timezone Việt Nam
VIETNAM_TIMEZONE = 'Asia/Ho_Chi_Minh'

# Mã thời tiết OpenWeatherMap
OWM_WEATHER_CODES = {
    # Thunderstorm
    200: ('Dông có mưa nhẹ', '⛈️'),
    201: ('Dông có mưa', '⛈️'),
    202: ('Dông có mưa to', '⛈️'),
    210: ('Dông nhẹ', '⛈️'),
    211: ('Dông', '⛈️'),
    212: ('Dông mạnh', '⛈️'),
    221: ('Dông rải rác', '⛈️'),
    230: ('Dông có mưa phùn nhẹ', '⛈️'),
    231: ('Dông có mưa phùn', '⛈️'),
    232: ('Dông có mưa phùn nặng', '⛈️'),
    # Drizzle
    300: ('Mưa phùn nhẹ', '🌦️'),
    301: ('Mưa phùn', '🌦️'),
    302: ('Mưa phùn nặng', '🌧️'),
    310: ('Mưa phùn nhẹ', '🌦️'),
    311: ('Mưa phùn', '🌦️'),
    312: ('Mưa phùn nặng', '🌧️'),
    313: ('Mưa rào và mưa phùn', '🌧️'),
    314: ('Mưa rào nặng và mưa phùn', '🌧️'),
    321: ('Mưa phùn rào', '🌦️'),
    # Rain
    500: ('Mưa nhẹ', '🌧️'),
    501: ('Mưa vừa', '🌧️'),
    502: ('Mưa to', '🌧️'),
    503: ('Mưa rất to', '⛈️'),
    504: ('Mưa cực to', '⛈️'),
    511: ('Mưa đóng băng', '🌧️'),
    520: ('Mưa rào nhẹ', '🌦️'),
    521: ('Mưa rào', '🌧️'),
    522: ('Mưa rào nặng', '🌧️'),
    531: ('Mưa rào rải rác', '🌦️'),
    # Snow
    600: ('Tuyết nhẹ', '🌨️'),
    601: ('Tuyết', '🌨️'),
    602: ('Tuyết nặng', '❄️'),
    611: ('Mưa tuyết', '🌨️'),
    612: ('Mưa tuyết nhẹ', '🌨️'),
    613: ('Mưa tuyết rào', '🌨️'),
    615: ('Mưa nhẹ và tuyết', '🌨️'),
    616: ('Mưa và tuyết', '🌨️'),
    620: ('Tuyết rào nhẹ', '🌨️'),
    621: ('Tuyết rào', '🌨️'),
    622: ('Tuyết rào nặng', '❄️'),
    # Atmosphere
    701: ('Sương mù nhẹ', '🌫️'),
    711: ('Khói', '🌫️'),
    721: ('Mù', '🌫️'),
    731: ('Bụi xoáy', '🌫️'),
    741: ('Sương mù', '🌫️'),
    751: ('Cát', '🌫️'),
    761: ('Bụi', '🌫️'),
    762: ('Tro núi lửa', '🌫️'),
    771: ('Gió giật', '💨'),
    781: ('Lốc xoáy', '🌪️'),
    # Clear
    800: ('Trời quang đãng', '☀️'),
    # Clouds
    801: ('Ít mây', '🌤️'),
    802: ('Mây rải rác', '⛅'),
    803: ('Nhiều mây', '🌥️'),
    804: ('U ám', '☁️'),
}

# Mã thời tiết Open-Meteo (fallback)
OM_WEATHER_CODES = {
    0: ('Trời quang đãng', '☀️'),
    1: ('Trời ít mây', '🌤️'),
    2: ('Trời nhiều mây', '⛅'),
    3: ('Trời u ám', '☁️'),
    45: ('Có sương mù', '🌫️'),
    48: ('Sương mù dày', '🌫️'),
    51: ('Mưa phùn nhẹ', '🌦️'),
    53: ('Mưa phùn vừa', '🌦️'),
    55: ('Mưa phùn nặng', '🌧️'),
    61: ('Mưa nhẹ', '🌧️'),
    63: ('Mưa vừa', '🌧️'),
    65: ('Mưa to', '⛈️'),
    80: ('Mưa rào nhẹ', '🌦️'),
    81: ('Mưa rào vừa', '🌧️'),
    82: ('Mưa rào to', '⛈️'),
    95: ('Dông', '⛈️'),
    96: ('Dông có mưa đá', '⛈️'),
    99: ('Dông có mưa đá nặng', '⛈️'),
}


def get_current_weather(latitude, longitude):
    """
    Lấy thời tiết hiện tại cho một địa điểm
    Ưu tiên OpenWeatherMap, fallback sang Open-Meteo
    """
    # Thử OpenWeatherMap trước (chính xác hơn)
    if OPENWEATHERMAP_API_KEY:
        result = _get_weather_openweathermap(latitude, longitude)
        if 'error' not in result:
            return result
    
    # Fallback sang Open-Meteo
    return _get_weather_openmeteo(latitude, longitude)


def _get_weather_openweathermap(latitude, longitude):
    """Lấy thời tiết từ OpenWeatherMap API"""
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': OPENWEATHERMAP_API_KEY,
            'units': 'metric',  # Celsius
            'lang': 'vi'  # Tiếng Việt
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {'error': f'API error: {response.status_code}'}
        
        data = response.json()
        
        weather_id = data['weather'][0]['id']
        weather_info = OWM_WEATHER_CODES.get(weather_id, ('Không xác định', '🌡️'))
        
        # Xác định ngày/đêm
        is_day = 1
        if 'sys' in data:
            current_time = data.get('dt', 0)
            sunrise = data['sys'].get('sunrise', 0)
            sunset = data['sys'].get('sunset', 0)
            is_day = 1 if sunrise < current_time < sunset else 0
        
        icon = weather_info[1]
        if weather_id == 800 and not is_day:
            icon = '🌙'
        
        return {
            'temperature': round(data['main']['temp'], 1),
            'feels_like': round(data['main']['feels_like'], 1),
            'humidity': data['main']['humidity'],
            'pressure': data['main'].get('pressure', 0),
            'windspeed': round(data['wind'].get('speed', 0) * 3.6, 1),  # m/s -> km/h
            'wind_direction': data['wind'].get('deg', 0),
            'clouds': data.get('clouds', {}).get('all', 0),
            'visibility': data.get('visibility', 10000) / 1000,  # m -> km
            'weather_code': weather_id,
            'weather_desc': data['weather'][0].get('description', weather_info[0]).capitalize(),
            'icon': icon,
            'is_day': is_day,
            'location_name': data.get('name', ''),
            'country': data.get('sys', {}).get('country', ''),
            'time': datetime.fromtimestamp(data['dt']).strftime('%Y-%m-%d %H:%M'),
            'is_current': True,
            'source': 'OpenWeatherMap'
        }
        
    except Exception as e:
        return {'error': f'OpenWeatherMap error: {str(e)}'}


def _get_weather_openmeteo(latitude, longitude):
    """Fallback: Lấy thời tiết từ Open-Meteo API"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,is_day,precipitation',
            'timezone': VIETNAM_TIMEZONE
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'current' not in data:
            return {'error': 'Không lấy được dữ liệu thời tiết'}
        
        current = data['current']
        weather_code = current.get('weather_code', 0)
        weather_info = OM_WEATHER_CODES.get(weather_code, ('Không xác định', '🌡️'))
        
        is_day = current.get('is_day', 1)
        icon = weather_info[1]
        if weather_code == 0 and not is_day:
            icon = '🌙'
        
        return {
            'temperature': round(current.get('temperature_2m', 0), 1),
            'feels_like': round(current.get('apparent_temperature', 0), 1),
            'humidity': current.get('relative_humidity_2m', 0),
            'windspeed': round(current.get('wind_speed_10m', 0), 1),
            'wind_direction': current.get('wind_direction_10m', 0),
            'precipitation': current.get('precipitation', 0),
            'weather_code': weather_code,
            'weather_desc': weather_info[0],
            'icon': icon,
            'is_day': is_day,
            'time': current.get('time', ''),
            'is_current': True,
            'source': 'Open-Meteo'
        }
        
    except Exception as e:
        return {'error': f'Lỗi khi lấy thời tiết: {str(e)}'}


def get_weather_forecast(latitude, longitude, date_str=None):
    """
    Lấy dự báo thời tiết cho một địa điểm
    """
    # Thử OpenWeatherMap trước
    if OPENWEATHERMAP_API_KEY:
        result = _get_forecast_openweathermap(latitude, longitude, date_str)
        if 'error' not in result:
            return result
    
    # Fallback sang Open-Meteo
    return _get_forecast_openmeteo(latitude, longitude, date_str)


def _get_forecast_openweathermap(latitude, longitude, date_str=None):
    """Lấy dự báo từ OpenWeatherMap"""
    try:
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': OPENWEATHERMAP_API_KEY,
            'units': 'metric',
            'lang': 'vi'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {'error': f'API error: {response.status_code}'}
        
        data = response.json()
        
        # Tìm ngày cần xem
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = datetime.now().date()
        
        # Tìm forecast cho ngày đó (lấy giờ 12h trưa)
        for item in data['list']:
            forecast_dt = datetime.fromtimestamp(item['dt'])
            if forecast_dt.date() == target_date and forecast_dt.hour >= 11 and forecast_dt.hour <= 14:
                weather_id = item['weather'][0]['id']
                weather_info = OWM_WEATHER_CODES.get(weather_id, ('Không xác định', '🌡️'))
                
                return {
                    'date': target_date.strftime('%Y-%m-%d'),
                    'temp_max': round(item['main']['temp_max'], 1),
                    'temp_min': round(item['main']['temp_min'], 1),
                    'humidity': item['main']['humidity'],
                    'windspeed': round(item['wind'].get('speed', 0) * 3.6, 1),
                    'weather_code': weather_id,
                    'weather_desc': item['weather'][0].get('description', weather_info[0]).capitalize(),
                    'icon': weather_info[1],
                    'precipitation_prob': item.get('pop', 0) * 100,
                    'source': 'OpenWeatherMap'
                }
        
        return {'error': 'Không tìm thấy dữ liệu cho ngày này'}
        
    except Exception as e:
        return {'error': f'OpenWeatherMap error: {str(e)}'}


def _get_forecast_openmeteo(latitude, longitude, date_str=None):
    """Fallback: Lấy dự báo từ Open-Meteo"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now()
            days_diff = (target_date - today).days
            
            if days_diff < 0:
                return {'error': 'Không thể xem thời tiết quá khứ'}
            elif days_diff > 7:
                return {'error': 'Chỉ có thể xem dự báo trong 7 ngày tới'}
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')
            days_diff = 0
        
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max,precipitation_probability_max',
            'timezone': VIETNAM_TIMEZONE,
            'forecast_days': min(days_diff + 1, 7)
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'daily' not in data:
            return {'error': 'Không lấy được dữ liệu thời tiết'}
        
        daily = data['daily']
        date_index = days_diff if days_diff < len(daily['time']) else 0
        
        weather_code = daily['weathercode'][date_index]
        weather_info = OM_WEATHER_CODES.get(weather_code, ('Không xác định', '🌡️'))
        
        return {
            'date': daily['time'][date_index],
            'temp_max': round(daily['temperature_2m_max'][date_index], 1),
            'temp_min': round(daily['temperature_2m_min'][date_index], 1),
            'precipitation': daily['precipitation_sum'][date_index],
            'precipitation_prob': daily.get('precipitation_probability_max', [0])[date_index] if daily.get('precipitation_probability_max') else 0,
            'windspeed': round(daily['windspeed_10m_max'][date_index], 1),
            'weather_code': weather_code,
            'weather_desc': weather_info[0],
            'icon': weather_info[1],
            'source': 'Open-Meteo'
        }
        
    except Exception as e:
        return {'error': f'Lỗi khi lấy thời tiết: {str(e)}'}


def get_weather_7days(latitude, longitude):
    """Lấy dự báo thời tiết 7 ngày tới"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max,precipitation_probability_max',
            'timezone': VIETNAM_TIMEZONE,
            'forecast_days': 7
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'daily' not in data:
            return {'error': 'Không lấy được dữ liệu thời tiết'}
        
        daily = data['daily']
        forecasts = []
        
        for i in range(len(daily['time'])):
            weather_code = daily['weathercode'][i]
            weather_info = OM_WEATHER_CODES.get(weather_code, ('Không xác định', '🌡️'))
            
            forecasts.append({
                'date': daily['time'][i],
                'temp_max': round(daily['temperature_2m_max'][i], 1),
                'temp_min': round(daily['temperature_2m_min'][i], 1),
                'precipitation': daily['precipitation_sum'][i],
                'precipitation_prob': daily.get('precipitation_probability_max', [0]*7)[i] if daily.get('precipitation_probability_max') else 0,
                'windspeed': round(daily['windspeed_10m_max'][i], 1),
                'weather_code': weather_code,
                'weather_desc': weather_info[0],
                'icon': weather_info[1]
            })
        
        return {'forecasts': forecasts}
        
    except Exception as e:
        return {'error': f'Lỗi khi lấy thời tiết: {str(e)}'}
