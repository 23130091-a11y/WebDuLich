# Service lấy thông tin thời tiết từ Open-Meteo API (miễn phí)
import requests
from datetime import datetime, timedelta

def get_weather_forecast(latitude, longitude, date_str=None):
    """
    Lấy dự báo thời tiết cho một địa điểm
    - latitude, longitude: tọa độ
    - date_str: ngày cần xem (format: YYYY-MM-DD), None = hôm nay
    """
    try:
        # API Open-Meteo (miễn phí, không cần key)
        url = "https://api.open-meteo.com/v1/forecast"
        
        # Tính số ngày forecast cần (tối đa 7 ngày)
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
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max',
            'timezone': 'Asia/Bangkok',
            'forecast_days': min(days_diff + 1, 7)
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if 'daily' not in data:
            return {'error': 'Không lấy được dữ liệu thời tiết'}
        
        # Lấy dữ liệu cho ngày cụ thể
        daily = data['daily']
        date_index = days_diff if days_diff < len(daily['time']) else 0
        
        # Mã thời tiết (WMO Weather interpretation codes)
        weather_codes = {
            0: 'Trời quang đãng',
            1: 'Trời ít mây',
            2: 'Trời nhiều mây',
            3: 'Trời u ám',
            45: 'Có sương mù',
            48: 'Sương mù dày',
            51: 'Mưa phùn nhẹ',
            53: 'Mưa phùn vừa',
            55: 'Mưa phùn nặng',
            61: 'Mưa nhẹ',
            63: 'Mưa vừa',
            65: 'Mưa to',
            71: 'Tuyết nhẹ',
            73: 'Tuyết vừa',
            75: 'Tuyết nặng',
            80: 'Mưa rào nhẹ',
            81: 'Mưa rào vừa',
            82: 'Mưa rào to',
            95: 'Dông',
            96: 'Dông có mưa đá nhẹ',
            99: 'Dông có mưa đá nặng'
        }
        
        weather_code = daily['weathercode'][date_index]
        weather_desc = weather_codes.get(weather_code, 'Không xác định')
        
        # Icon thời tiết
        weather_icons = {
            0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
            45: '🌫️', 48: '🌫️',
            51: '🌦️', 53: '🌦️', 55: '🌧️',
            61: '🌧️', 63: '🌧️', 65: '⛈️',
            71: '🌨️', 73: '🌨️', 75: '❄️',
            80: '🌦️', 81: '🌧️', 82: '⛈️',
            95: '⛈️', 96: '⛈️', 99: '⛈️'
        }
        icon = weather_icons.get(weather_code, '🌡️')
        
        result = {
            'date': daily['time'][date_index],
            'temp_max': daily['temperature_2m_max'][date_index],
            'temp_min': daily['temperature_2m_min'][date_index],
            'precipitation': daily['precipitation_sum'][date_index],
            'windspeed': daily['windspeed_10m_max'][date_index],
            'weather_code': weather_code,
            'weather_desc': weather_desc,
            'icon': icon
        }
        
        return result
        
    except Exception as e:
        return {'error': f'Lỗi khi lấy thời tiết: {str(e)}'}


def get_current_weather(latitude, longitude):
    """Lấy thời tiết hiện tại"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current_weather': 'true',
            'timezone': 'Asia/Bangkok'
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        if 'current_weather' not in data:
            return {'error': 'Không lấy được dữ liệu'}
        
        current = data['current_weather']
        
        return {
            'temperature': current['temperature'],
            'windspeed': current['windspeed'],
            'weather_code': current['weathercode'],
            'time': current['time']
        }
        
    except Exception as e:
        return {'error': str(e)}
