"""
Script test OpenWeatherMap API
Chạy: python test_weather_api.py
"""
import requests

API_KEY = "17bfbfe5c8321e5b963303043223fca3"
LAT = 15.8801  # Hội An
LON = 108.335

url = "https://api.openweathermap.org/data/2.5/weather"
params = {
    'lat': LAT,
    'lon': LON,
    'appid': API_KEY,
    'units': 'metric',
    'lang': 'vi'
}

print("Testing OpenWeatherMap API...")
print(f"Location: Hội An ({LAT}, {LON})")
print("-" * 40)

response = requests.get(url, params=params)
data = response.json()

if response.status_code == 200:
    print(f"✅ API hoạt động!")
    print(f"Nhiệt độ: {data['main']['temp']}°C")
    print(f"Cảm giác như: {data['main']['feels_like']}°C")
    print(f"Độ ẩm: {data['main']['humidity']}%")
    print(f"Thời tiết: {data['weather'][0]['description']}")
    print(f"Địa điểm: {data['name']}")
else:
    print(f"❌ Lỗi: {data.get('message', 'Unknown error')}")
    print("API key có thể chưa được kích hoạt. Vui lòng chờ 10-30 phút sau khi xác nhận email.")
