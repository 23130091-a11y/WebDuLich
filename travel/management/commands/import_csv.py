"""
Custom Management Command: Import dữ liệu từ CSV với Enrichment từ API

Tech Stack: Pandas, Geopy, Tenacity
Input: data/bookings.csv

Quy trình:
1. Đọc và chuẩn hóa dữ liệu từ CSV
2. Tạo bản ghi cơ bản trong DB
3. Làm giàu dữ liệu (Geocoding từ Nominatim)
4. Tạo Review giả lập từ satisfaction scores

Cải thiện v2:
- Thêm validation cho rating (1-5)
- Thêm --dry-run mode
- Thêm logging
- Cải thiện error handling
"""

import os
import time
import random
import logging
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

# Import models
from travel.models import Destination, Review
from travel.ai_module import analyze_sentiment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import dữ liệu từ CSV với enrichment từ Geocoding API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='data/bookings.csv',
            help='Đường dẫn đến file CSV'
        )
        parser.add_argument(
            '--skip-enrichment',
            action='store_true',
            help='Bỏ qua bước Geocoding (nhanh hơn)'
        )
        parser.add_argument(
            '--skip-reviews',
            action='store_true',
            help='Bỏ qua bước tạo reviews'
        )
        parser.add_argument(
            '--max-reviews',
            type=int,
            default=15,
            help='Số reviews tối đa cho mỗi địa điểm'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ preview, không thực sự import'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Chỉ validate CSV, không import'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        skip_enrichment = options['skip_enrichment']
        skip_reviews = options['skip_reviews']
        max_reviews = options['max_reviews']
        dry_run = options.get('dry_run', False)
        validate_only = options.get('validate_only', False)

        self.stdout.write(self.style.HTTP_INFO(
            '\n' + '='*60 + '\n'
            '📊 IMPORT DỮ LIỆU TỪ CSV VỚI ENRICHMENT\n'
            '='*60
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ CHẾ ĐỘ DRY-RUN: Không thực sự import\n'))

        # Kiểm tra file tồn tại
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'❌ Không tìm thấy file: {csv_path}'))
            return

        # ==================== BƯỚC 1: ĐỌC VÀ CHUẨN HÓA DỮ LIỆU ====================
        self.stdout.write('\n📖 BƯỚC 1: Đọc và chuẩn hóa dữ liệu từ CSV...')
        
        try:
            import pandas as pd
        except ImportError:
            self.stdout.write(self.style.ERROR(
                '❌ Chưa cài pandas! Chạy: pip install pandas'
            ))
            return

        df = self._read_and_normalize_csv(csv_path)
        if df is None:
            return

        # Gom nhóm theo destination
        aggregated_data = self._aggregate_by_destination(df)
        self.stdout.write(self.style.SUCCESS(
            f'   ✓ Tìm thấy {len(aggregated_data)} địa điểm duy nhất'
        ))

        # Validate only mode
        if validate_only:
            self._show_validation_report(df, aggregated_data)
            return

        # Dry run mode - preview
        if dry_run:
            self._show_preview(aggregated_data, df, max_reviews)
            return

        # ==================== BƯỚC 2: TẠO BẢN GHI CƠ BẢN ====================
        self.stdout.write('\n💾 BƯỚC 2: Tạo/cập nhật bản ghi trong database...')
        
        try:
            with transaction.atomic():
                created_destinations = self._create_basic_records(aggregated_data)
                self.stdout.write(self.style.SUCCESS(
                    f'   ✓ Đã xử lý {len(created_destinations)} địa điểm'
                ))
        except Exception as e:
            logger.error(f"Lỗi tạo bản ghi: {e}")
            self.stdout.write(self.style.ERROR(f'❌ Lỗi: {e}'))
            return

        # ==================== BƯỚC 3: LÀM GIÀU DỮ LIỆU (ENRICHMENT) ====================
        if not skip_enrichment:
            self.stdout.write('\n🌍 BƯỚC 3: Làm giàu dữ liệu (Geocoding)...')
            self._enrich_with_geocoding()
        else:
            self.stdout.write('\n⏭️ BƯỚC 3: Bỏ qua Geocoding (--skip-enrichment)')

        # ==================== BƯỚC 4: TẠO REVIEW GIẢ LẬP ====================
        if not skip_reviews:
            self.stdout.write('\n📝 BƯỚC 4: Tạo reviews từ satisfaction scores...')
            self._create_reviews_from_csv(df, max_reviews)
        else:
            self.stdout.write('\n⏭️ BƯỚC 4: Bỏ qua tạo reviews (--skip-reviews)')

        # ==================== HOÀN THÀNH ====================
        self.stdout.write(self.style.SUCCESS(
            '\n' + '='*60 + '\n'
            '✅ IMPORT HOÀN TẤT!\n'
            '='*60 + '\n'
            '💡 Chạy tiếp: python manage.py calculate_scores\n'
        ))

    def _show_validation_report(self, df, aggregated_data):
        """Hiển thị báo cáo validation"""
        self.stdout.write('\n📋 BÁO CÁO VALIDATION:\n')
        
        # Thống kê cơ bản
        self.stdout.write(f'   Tổng số dòng: {len(df)}')
        self.stdout.write(f'   Địa điểm duy nhất: {len(aggregated_data)}')
        
        # Kiểm tra giá trị null
        null_counts = df.isnull().sum()
        if null_counts.any():
            self.stdout.write('\n   ⚠️ Giá trị NULL:')
            for col, count in null_counts.items():
                if count > 0:
                    self.stdout.write(f'      - {col}: {count}')
        
        # Kiểm tra satisfaction range
        if 'satisfaction' in df.columns:
            sat_min = df['satisfaction'].min()
            sat_max = df['satisfaction'].max()
            self.stdout.write(f'\n   📊 Satisfaction range: {sat_min:.2f} - {sat_max:.2f}')
            
            invalid_sat = df[(df['satisfaction'] < 1) | (df['satisfaction'] > 5)]
            if len(invalid_sat) > 0:
                self.stdout.write(self.style.WARNING(
                    f'   ⚠️ {len(invalid_sat)} dòng có satisfaction ngoài range 1-5'
                ))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Validation hoàn tất!'))

    def _show_preview(self, aggregated_data, df, max_reviews):
        """Preview dữ liệu sẽ được import"""
        self.stdout.write('\n📋 PREVIEW DỮ LIỆU:\n')
        
        self.stdout.write(f'   Sẽ tạo/cập nhật: {len(aggregated_data)} địa điểm')
        
        # Ước tính số reviews
        total_reviews = 0
        for dest in aggregated_data:
            dest_bookings = len(df[df['destination_normalized'] == dest['name']])
            total_reviews += min(dest_bookings, max_reviews)
        
        self.stdout.write(f'   Ước tính reviews: ~{total_reviews}')
        
        self.stdout.write('\n   📍 Danh sách địa điểm:')
        for d in aggregated_data[:10]:
            self.stdout.write(f'      - {d["name"]} ({d["travel_type"]}, {d["avg_price"]:,.0f}đ)')
        
        if len(aggregated_data) > 10:
            self.stdout.write(f'      ... và {len(aggregated_data) - 10} địa điểm khác')

    # ==================== HELPER METHODS ====================

    def _read_and_normalize_csv(self, csv_path):
        """
        Bước 1: Đọc CSV và chuẩn hóa dữ liệu
        - Strip spaces
        - Title case cho tên địa điểm
        - Xử lý giá trị null
        """
        import pandas as pd

        try:
            df = pd.read_csv(csv_path)
            self.stdout.write(f'   ✓ Đọc được {len(df)} dòng từ CSV')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Lỗi đọc CSV: {e}'))
            return None

        # Kiểm tra các cột cần thiết
        required_cols = ['destination', 'tour_type', 'base_price_vnd', 'satisfaction']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            self.stdout.write(self.style.ERROR(
                f'❌ Thiếu cột: {missing_cols}'
            ))
            return None

        # Chuẩn hóa tên địa điểm
        df['destination_normalized'] = df['destination'].apply(
            lambda x: self._normalize_destination_name(x) if pd.notna(x) else None
        )

        # Loại bỏ các dòng không có destination
        df = df[df['destination_normalized'].notna()]
        self.stdout.write(f'   ✓ Sau khi lọc: {len(df)} dòng hợp lệ')

        return df

    def _normalize_destination_name(self, name):
        """
        Chuẩn hóa tên địa điểm:
        - Strip spaces
        - Title case
        - Sửa lỗi chính tả phổ biến
        """
        if not name or not isinstance(name, str):
            return None

        name = name.strip()
        
        # Mapping sửa lỗi chính tả
        corrections = {
            'halongg': 'Hạ Long',
            'halong': 'Hạ Long',
            'ha long': 'Hạ Long',
            'hạ long': 'Hạ Long',
            'tp.hcm': 'TP Hồ Chí Minh',
            'tphcm': 'TP Hồ Chí Minh',
            'hcm': 'TP Hồ Chí Minh',
            'sài gòn': 'TP Hồ Chí Minh',
            'saigon': 'TP Hồ Chí Minh',
            'huế': 'Huế',
            'hue': 'Huế',
            'đà nẵng': 'Đà Nẵng',
            'da nang': 'Đà Nẵng',
            'danang': 'Đà Nẵng',
            'dnang': 'Đà Nẵng',  # Thêm mapping cho lỗi chính tả
            'đà lạt': 'Đà Lạt',
            'da lat': 'Đà Lạt',
            'dalat': 'Đà Lạt',
            'nha trang': 'Nha Trang',
            'phú quốc': 'Phú Quốc',
            'phu quoc': 'Phú Quốc',
            'phuquoc': 'Phú Quốc',
            'sapa': 'Sa Pa',
            'sa pa': 'Sa Pa',
            'hội an': 'Hội An',
            'hoi an': 'Hội An',
            'hoian': 'Hội An',
        }

        name_lower = name.lower()
        if name_lower in corrections:
            return corrections[name_lower]

        # Title case cho các tên khác
        return name.title()

    def _aggregate_by_destination(self, df):
        """
        Gom nhóm theo destination:
        - avg_price = trung bình base_price_vnd
        - travel_type = mode (giá trị xuất hiện nhiều nhất)
        """
        import pandas as pd

        aggregated = []

        for dest_name in df['destination_normalized'].unique():
            dest_df = df[df['destination_normalized'] == dest_name]

            # Tính avg_price
            avg_price = dest_df['base_price_vnd'].mean()

            # Tìm travel_type phổ biến nhất (mode)
            tour_types = dest_df['tour_type'].dropna()
            if len(tour_types) > 0:
                travel_type = tour_types.mode().iloc[0] if len(tour_types.mode()) > 0 else 'Cultural'
            else:
                travel_type = 'Cultural'

            # Mapping tour_type sang tiếng Việt
            type_mapping = {
                'Cultural': 'Văn hóa',
                'Beach': 'Biển',
                'Adventure': 'Phiêu lưu',
                'City Break': 'Thành phố',
                'Family': 'Gia đình',
                'Foodie': 'Ẩm thực',
                'bech': 'Biển',  # Sửa lỗi chính tả
            }
            travel_type_vn = type_mapping.get(travel_type, travel_type)

            aggregated.append({
                'name': dest_name,
                'avg_price': round(avg_price, 0),
                'travel_type': travel_type_vn,
                'booking_count': len(dest_df),
            })

        return aggregated

    def _create_basic_records(self, aggregated_data):
        """
        Bước 2: Tạo bản ghi cơ bản trong DB
        - Sử dụng update_or_create
        - Chưa gọi API, chỉ lưu dữ liệu thô
        """
        created_destinations = []

        for data in aggregated_data:
            dest, created = Destination.objects.update_or_create(
                name=data['name'],
                defaults={
                    'avg_price': Decimal(str(data['avg_price'])),
                    'travel_type': data['travel_type'],
                    'location': data['name'],  # Tạm thời dùng name làm location
                    'metadata': {
                        'source': 'kaggle_csv',
                        'booking_count': data['booking_count'],
                        'imported_at': datetime.now().isoformat(),
                    }
                }
            )

            status = '🆕 Tạo mới' if created else '🔄 Cập nhật'
            self.stdout.write(f'   {status}: {dest.name} ({data["travel_type"]}, {data["avg_price"]:,.0f}đ)')
            created_destinations.append(dest)

        return created_destinations

    def _enrich_with_geocoding(self):
        """
        Bước 3: Làm giàu dữ liệu với Geocoding
        - Sử dụng Geopy (Nominatim)
        - Tenacity để retry khi lỗi
        - Rate limit: 1 request/giây
        """
        try:
            from geopy.geocoders import Nominatim
            from geopy.exc import GeocoderTimedOut, GeocoderServiceError
        except ImportError:
            self.stdout.write(self.style.WARNING(
                '   ⚠️ Chưa cài geopy! Chạy: pip install geopy'
            ))
            return

        try:
            from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        except ImportError:
            self.stdout.write(self.style.WARNING(
                '   ⚠️ Chưa cài tenacity! Chạy: pip install tenacity'
            ))
            # Fallback: không dùng retry
            self._enrich_without_retry()
            return

        # Khởi tạo geocoder
        geolocator = Nominatim(
            user_agent="travel_web_app_vietnam",
            timeout=10
        )

        # Hàm geocode với retry
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((GeocoderTimedOut, GeocoderServiceError))
        )
        def geocode_with_retry(query):
            return geolocator.geocode(query)

        # Lấy các địa điểm chưa có tọa độ
        destinations_to_enrich = Destination.objects.filter(latitude__isnull=True)
        total = destinations_to_enrich.count()

        if total == 0:
            self.stdout.write('   ✓ Tất cả địa điểm đã có tọa độ')
            return

        self.stdout.write(f'   📍 Cần geocode {total} địa điểm...')

        success_count = 0
        error_count = 0

        for i, dest in enumerate(destinations_to_enrich, 1):
            try:
                # Tạo query string
                query = f"{dest.name}, Vietnam"
                self.stdout.write(f'   [{i}/{total}] Geocoding: {query}...', ending='')

                # Gọi API với retry
                location = geocode_with_retry(query)

                if location:
                    # Cập nhật database
                    dest.latitude = location.latitude
                    dest.longitude = location.longitude
                    dest.address = location.address

                    # Tạo description
                    dest.description = self._generate_description(dest)

                    # Cập nhật metadata
                    metadata = dest.metadata or {}
                    metadata.update({
                        'geo_source': 'nominatim',
                        'enriched_at': datetime.now().isoformat(),
                        'raw_address': location.address,
                    })
                    dest.metadata = metadata

                    dest.save()
                    self.stdout.write(self.style.SUCCESS(' ✓'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING(' ⚠️ Không tìm thấy'))
                    error_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f' ❌ Lỗi: {str(e)[:50]}'))
                error_count += 1
                # Tiếp tục với địa điểm tiếp theo

            # Rate limiting: 1.1 giây giữa các request
            time.sleep(1.1)

        self.stdout.write(f'   📊 Kết quả: {success_count} thành công, {error_count} lỗi')

    def _enrich_without_retry(self):
        """Fallback: Geocoding không có tenacity"""
        try:
            from geopy.geocoders import Nominatim
        except ImportError:
            return

        geolocator = Nominatim(user_agent="travel_web_app_vietnam", timeout=10)
        destinations_to_enrich = Destination.objects.filter(latitude__isnull=True)

        for dest in destinations_to_enrich:
            try:
                query = f"{dest.name}, Vietnam"
                location = geolocator.geocode(query)

                if location:
                    dest.latitude = location.latitude
                    dest.longitude = location.longitude
                    dest.address = location.address
                    dest.description = self._generate_description(dest)
                    dest.save()
                    self.stdout.write(f'   ✓ {dest.name}')

                time.sleep(1.1)

            except Exception as e:
                self.stdout.write(f'   ❌ {dest.name}: {e}')
                continue

    def _generate_description(self, dest):
        """Tạo description từ template"""
        templates = [
            f"Khám phá {dest.name} - điểm đến hấp dẫn với loại hình du lịch {dest.travel_type}. "
            f"Nơi đây mang đến những trải nghiệm tuyệt vời cho du khách.",
            
            f"{dest.name} là một trong những điểm đến du lịch {dest.travel_type} nổi tiếng tại Việt Nam. "
            f"Hãy đến và khám phá vẻ đẹp độc đáo của nơi này.",
            
            f"Đến với {dest.name}, bạn sẽ được trải nghiệm du lịch {dest.travel_type} đích thực. "
            f"Một điểm đến không thể bỏ qua trong hành trình khám phá Việt Nam.",
        ]
        return random.choice(templates)

    def _create_reviews_from_csv(self, df, max_reviews):
        """
        Bước 4: Tạo reviews từ satisfaction scores trong CSV
        - Lấy mẫu 10-20 dòng cho mỗi địa điểm
        - Tạo comment dựa trên rating
        """
        import pandas as pd

        # Lọc các dòng có satisfaction
        df_with_satisfaction = df[df['satisfaction'].notna()].copy()

        # Danh sách tên giả
        fake_names = [
            'Nguyễn Văn A', 'Trần Thị B', 'Lê Văn C', 'Phạm Thị D',
            'Hoàng Văn E', 'Vũ Thị F', 'Đỗ Văn G', 'Bùi Thị H',
            'Đinh Văn I', 'Mai Thị K', 'Phan Văn L', 'Lý Thị M',
            'Traveler_VN', 'Du khách 2024', 'Phượt thủ', 'Backpacker',
        ]

        # Comment templates theo rating
        comment_templates = {
            5: [
                "Tuyệt vời! Trải nghiệm không thể quên. Rất recommend!",
                "Xuất sắc! Dịch vụ tốt, cảnh đẹp. Sẽ quay lại!",
                "Hoàn hảo! Đáng đồng tiền bát gạo. 5 sao xứng đáng!",
                "Tuyệt vời quá! Mọi thứ đều tốt, rất hài lòng.",
            ],
            4: [
                "Rất tốt! Có vài điểm nhỏ cần cải thiện nhưng nhìn chung ok.",
                "Khá ổn, cảnh đẹp, dịch vụ tốt. Đáng để đi.",
                "Hài lòng với chuyến đi. Sẽ giới thiệu cho bạn bè.",
                "Tốt! Giá cả hợp lý, trải nghiệm đáng nhớ.",
            ],
            3: [
                "Tạm ổn, không quá đặc biệt nhưng cũng không tệ.",
                "Bình thường, có thể đi thử một lần.",
                "Ổn, giá hơi cao so với những gì nhận được.",
                "Được, nhưng kỳ vọng cao hơn một chút.",
            ],
            2: [
                "Hơi thất vọng. Không như mong đợi.",
                "Chưa hài lòng lắm. Cần cải thiện nhiều.",
                "Giá cao, chất lượng chưa tương xứng.",
            ],
            1: [
                "Tệ! Không recommend. Lãng phí tiền.",
                "Rất thất vọng. Dịch vụ kém, không đáng tiền.",
            ],
        }

        total_reviews_created = 0

        for dest_name in df_with_satisfaction['destination_normalized'].unique():
            try:
                dest = Destination.objects.get(name=dest_name)
            except Destination.DoesNotExist:
                continue

            # Lấy các booking của địa điểm này
            dest_bookings = df_with_satisfaction[
                df_with_satisfaction['destination_normalized'] == dest_name
            ]

            # Sample tối đa max_reviews dòng
            sample_size = min(len(dest_bookings), max_reviews)
            sampled = dest_bookings.sample(n=sample_size)

            reviews_created = 0
            for _, row in sampled.iterrows():
                # Chuyển satisfaction (1-5 float) thành rating (1-5 int)
                # Validate: đảm bảo rating trong range 1-5
                try:
                    satisfaction = float(row['satisfaction'])
                    # Clamp value to 1-5 range
                    satisfaction = max(1.0, min(5.0, satisfaction))
                    rating = int(round(satisfaction))
                    # Double check after rounding
                    rating = max(1, min(5, rating))
                except (ValueError, TypeError):
                    rating = 3  # Default rating nếu không parse được

                # Tạo author name
                customer_id = row.get('customer_id', '')
                if customer_id:
                    author_name = f"Khách {customer_id[-4:]}"
                else:
                    author_name = random.choice(fake_names)

                # Tạo comment
                comment = random.choice(comment_templates.get(rating, comment_templates[3]))

                # Phân tích sentiment
                sentiment_score, pos_kw, neg_kw = analyze_sentiment(comment)

                # Tạo review
                Review.objects.create(
                    destination=dest,
                    author_name=author_name,
                    rating=rating,
                    comment=comment,
                    sentiment_score=sentiment_score,
                    positive_keywords=pos_kw,
                    negative_keywords=neg_kw,
                )
                reviews_created += 1

            total_reviews_created += reviews_created
            self.stdout.write(f'   ✓ {dest_name}: {reviews_created} reviews')

        self.stdout.write(self.style.SUCCESS(
            f'   📊 Tổng cộng: {total_reviews_created} reviews được tạo'
        ))
