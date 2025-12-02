"""
Script crawl đánh giá từ Google Maps
Lưu ý: Cần cài đặt thêm: pip install selenium beautifulsoup4 lxml
"""

from django.core.management.base import BaseCommand
from travel.models import Destination, Review
from travel.ai_module import analyze_sentiment
import time
import random

class Command(BaseCommand):
    help = 'Crawl đánh giá từ Google Maps (cần cài selenium)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--destination-id',
            type=int,
            help='ID của địa điểm cần crawl reviews'
        )
        parser.add_argument(
            '--max-reviews',
            type=int,
            default=20,
            help='Số lượng reviews tối đa cần crawl'
        )

    def handle(self, *args, **options):
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from bs4 import BeautifulSoup
        except ImportError:
            self.stdout.write(self.style.ERROR(
                '❌ Chưa cài đặt thư viện cần thiết!\n'
                'Chạy lệnh: pip install selenium beautifulsoup4 lxml'
            ))
            return

        destination_id = options.get('destination_id')
        max_reviews = options.get('max_reviews')

        if not destination_id:
            self.stdout.write(self.style.ERROR(
                '❌ Vui lòng chỉ định --destination-id\n'
                'VD: python manage.py crawl_reviews --destination-id=1'
            ))
            return

        try:
            destination = Destination.objects.get(id=destination_id)
        except Destination.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Không tìm thấy địa điểm với ID {destination_id}'))
            return

        self.stdout.write(f'🔍 Bắt đầu crawl reviews cho: {destination.name}')
        self.stdout.write(f'📍 Vị trí: {destination.location}')

        # Tạo search query cho Google Maps
        search_query = f"{destination.name} {destination.location} Vietnam"
        google_maps_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"

        # Cấu hình Chrome headless
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--lang=vi')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.stdout.write('🌐 Đang mở trình duyệt...')

        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(google_maps_url)
            
            # Đợi trang load
            time.sleep(3)

            # Click vào kết quả đầu tiên
            try:
                first_result = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/maps/place/"]'))
                )
                first_result.click()
                time.sleep(2)
            except:
                self.stdout.write(self.style.WARNING('⚠️ Không tìm thấy địa điểm trên Google Maps'))
                driver.quit()
                return

            # Scroll để load reviews
            self.stdout.write('📜 Đang load reviews...')
            reviews_panel = driver.find_element(By.CSS_SELECTOR, 'div[role="main"]')
            
            for _ in range(5):  # Scroll 5 lần
                driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', reviews_panel)
                time.sleep(1)

            # Parse HTML
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            # Tìm các review elements
            review_elements = soup.find_all('div', {'data-review-id': True})
            
            if not review_elements:
                self.stdout.write(self.style.WARNING('⚠️ Không tìm thấy reviews'))
                driver.quit()
                return

            self.stdout.write(f'✓ Tìm thấy {len(review_elements)} reviews')

            crawled_count = 0
            for review_elem in review_elements[:max_reviews]:
                try:
                    # Lấy tên người đánh giá
                    author_elem = review_elem.find('div', class_='d4r55')
                    author_name = author_elem.text if author_elem else 'Anonymous'

                    # Lấy rating (số sao)
                    rating_elem = review_elem.find('span', {'role': 'img', 'aria-label': True})
                    if rating_elem:
                        rating_text = rating_elem.get('aria-label', '')
                        # Extract số từ "5 sao" hoặc "5 stars"
                        rating = int(''.join(filter(str.isdigit, rating_text.split()[0])))
                    else:
                        rating = 5

                    # Lấy nội dung review
                    comment_elem = review_elem.find('span', class_='wiI7pd')
                    comment = comment_elem.text if comment_elem else ''

                    if not comment:
                        continue

                    # Phân tích sentiment
                    sentiment_score, pos_keywords, neg_keywords = analyze_sentiment(comment)

                    # Kiểm tra xem review đã tồn tại chưa (tránh duplicate)
                    existing = Review.objects.filter(
                        destination=destination,
                        author_name=author_name,
                        comment=comment
                    ).exists()

                    if not existing:
                        Review.objects.create(
                            destination=destination,
                            author_name=author_name,
                            rating=rating,
                            comment=comment,
                            sentiment_score=sentiment_score,
                            positive_keywords=pos_keywords,
                            negative_keywords=neg_keywords
                        )
                        crawled_count += 1
                        self.stdout.write(f'  ✓ {author_name}: {rating}⭐ - {comment[:50]}...')

                except Exception as e:
                    self.stdout.write(f'  ⚠️ Lỗi parse review: {str(e)}')
                    continue

            driver.quit()

            self.stdout.write(self.style.SUCCESS(f'\n✅ Crawl thành công {crawled_count} reviews!'))
            self.stdout.write('💡 Chạy lệnh sau để tính điểm gợi ý:')
            self.stdout.write('   python manage.py calculate_scores')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Lỗi: {str(e)}'))
            if 'driver' in locals():
                driver.quit()
