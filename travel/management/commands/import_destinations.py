"""
Script import dữ liệu địa điểm du lịch Việt Nam
Dữ liệu được tổng hợp từ nhiều nguồn công khai

Cải thiện v2:
- Thêm --dry-run để preview
- Thêm --clear để xóa dữ liệu cũ
- Thêm progress tracking
- Cải thiện error handling
- Thêm logging
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from travel.models import Destination

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import dữ liệu địa điểm du lịch Việt Nam'

    def add_arguments(self, parser):
        parser.add_argument(
            '--region',
            type=str,
            default='all',
            choices=['all', 'north', 'central', 'south'],
            help='Vùng miền: all, north (Bắc), central (Trung), south (Nam)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ preview, không thực sự import'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Xóa tất cả destinations trước khi import'
        )
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Chỉ hiển thị kết quả cuối cùng'
        )

    def handle(self, *args, **options):
        region = options.get('region')
        dry_run = options.get('dry_run')
        clear = options.get('clear')
        quiet = options.get('quiet')
        
        self.stdout.write('🗺️ Import dữ liệu địa điểm du lịch Việt Nam\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️ CHẾ ĐỘ DRY-RUN: Không thực sự import\n'))

        # Dữ liệu địa điểm du lịch Việt Nam (tổng hợp từ nhiều nguồn)
        destinations_data = self._get_destinations_data()

        # Lọc theo vùng miền
        if region != 'all':
            destinations_data = [d for d in destinations_data if d.get('region') == region]
            self.stdout.write(f'📍 Lọc theo vùng: {region} ({len(destinations_data)} địa điểm)\n')

        if dry_run:
            self._preview_data(destinations_data)
            return

        # Xóa dữ liệu cũ nếu có flag --clear
        if clear:
            deleted_count = Destination.objects.count()
            Destination.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'🗑️ Đã xóa {deleted_count} địa điểm cũ\n'))

        created_count = 0
        updated_count = 0
        error_count = 0
        total = len(destinations_data)

        try:
            with transaction.atomic():
                for i, data in enumerate(destinations_data, 1):
                    try:
                        dest, created = Destination.objects.update_or_create(
                            name=data['name'],
                            defaults={
                                'travel_type': data['travel_type'],
                                'location': data['location'],
                                'address': data.get('address', ''),
                                'description': data['description'],
                                'latitude': data.get('latitude'),
                                'longitude': data.get('longitude'),
                                'avg_price': data.get('avg_price', 0),
                            }
                        )
                        
                        if created:
                            created_count += 1
                            if not quiet:
                                self.stdout.write(f'  [{i}/{total}] ✓ Tạo mới: {dest.name}')
                        else:
                            updated_count += 1
                            if not quiet:
                                self.stdout.write(f'  [{i}/{total}] ↻ Cập nhật: {dest.name}')
                                
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Lỗi import {data.get('name', 'unknown')}: {e}")
                        self.stdout.write(self.style.ERROR(
                            f'  [{i}/{total}] ❌ Lỗi: {data.get("name", "unknown")} - {str(e)[:50]}'
                        ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Lỗi transaction: {e}'))
            return

        # Kết quả
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Hoàn thành! Tạo mới: {created_count}, Cập nhật: {updated_count}, Lỗi: {error_count}'
        ))
        self.stdout.write(f'📊 Tổng số địa điểm trong DB: {Destination.objects.count()}')
        self.stdout.write('\n💡 Bước tiếp theo:')
        self.stdout.write('   python manage.py crawl_all_reviews')
        self.stdout.write('   python manage.py calculate_scores')

    def _preview_data(self, destinations_data):
        """Preview dữ liệu sẽ được import"""
        self.stdout.write(f'\n📋 PREVIEW: {len(destinations_data)} địa điểm\n')
        
        # Thống kê theo vùng
        regions = {}
        types = {}
        for d in destinations_data:
            region = d.get('region', 'unknown')
            travel_type = d.get('travel_type', 'unknown')
            regions[region] = regions.get(region, 0) + 1
            types[travel_type] = types.get(travel_type, 0) + 1
        
        self.stdout.write('📍 Theo vùng miền:')
        for r, count in sorted(regions.items()):
            self.stdout.write(f'   - {r}: {count}')
        
        self.stdout.write('\n🏷️ Theo loại hình:')
        for t, count in sorted(types.items(), key=lambda x: -x[1]):
            self.stdout.write(f'   - {t}: {count}')
        
        self.stdout.write('\n📝 10 địa điểm đầu tiên:')
        for d in destinations_data[:10]:
            self.stdout.write(f'   - {d["name"]} ({d["location"]}) - {d["travel_type"]}')

    def _get_destinations_data(self):
        """Dữ liệu địa điểm du lịch Việt Nam - Tổng hợp từ nhiều nguồn"""
        return [
            # ==================== MIỀN BẮC ====================
            # Hà Nội
            {
                'name': 'Hồ Hoàn Kiếm',
                'travel_type': 'Thành phố',
                'location': 'Hà Nội',
                'address': 'Quận Hoàn Kiếm, Hà Nội',
                'description': 'Hồ nước ngọt nằm ở trung tâm Hà Nội, biểu tượng của thủ đô với Tháp Rùa và Đền Ngọc Sơn. Nơi đây gắn liền với truyền thuyết vua Lê Lợi trả gươm thần cho Rùa Vàng.',
                'latitude': 21.0285,
                'longitude': 105.8542,
                'avg_price': 0,
                'region': 'north'
            },
            {
                'name': 'Văn Miếu - Quốc Tử Giám',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': '58 Quốc Tử Giám, Đống Đa, Hà Nội',
                'description': 'Trường đại học đầu tiên của Việt Nam, được xây dựng năm 1070. Di tích lịch sử văn hóa quốc gia đặc biệt với 82 bia Tiến sĩ.',
                'latitude': 21.0277,
                'longitude': 105.8355,
                'avg_price': 30000,
                'region': 'north'
            },
            {
                'name': 'Chùa Một Cột',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': 'Phố Chùa Một Cột, Ba Đình, Hà Nội',
                'description': 'Ngôi chùa có kiến trúc độc đáo nhất Việt Nam, được xây dựng năm 1049 dưới thời vua Lý Thái Tông. Chùa có hình dáng như một bông sen nở trên mặt nước.',
                'latitude': 21.0359,
                'longitude': 105.8347,
                'avg_price': 0,
                'region': 'north'
            },
            {
                'name': 'Lăng Chủ tịch Hồ Chí Minh',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': '2 Hùng Vương, Điện Biên, Ba Đình, Hà Nội',
                'description': 'Công trình tưởng niệm Chủ tịch Hồ Chí Minh, nơi lưu giữ thi hài của Người. Kiến trúc trang nghiêm, uy nghi giữa Quảng trường Ba Đình lịch sử.',
                'latitude': 21.0369,
                'longitude': 105.8344,
                'avg_price': 0,
                'region': 'north'
            },
            {
                'name': 'Hoàng thành Thăng Long',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': '19C Hoàng Diệu, Ba Đình, Hà Nội',
                'description': 'Di sản văn hóa thế giới UNESCO, trung tâm quyền lực của Việt Nam suốt 13 thế kỷ. Nơi lưu giữ nhiều di tích khảo cổ quý giá.',
                'latitude': 21.0340,
                'longitude': 105.8400,
                'avg_price': 30000,
                'region': 'north'
            },
            {
                'name': 'Phố cổ Hà Nội',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': 'Quận Hoàn Kiếm, Hà Nội',
                'description': 'Khu phố cổ 36 phố phường với lịch sử hàng nghìn năm. Mỗi phố mang tên một nghề thủ công truyền thống, là nơi lưu giữ hồn cốt Hà Nội xưa.',
                'latitude': 21.0340,
                'longitude': 105.8510,
                'avg_price': 0,
                'region': 'north'
            },
            {
                'name': 'Nhà hát Lớn Hà Nội',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': '1 Tràng Tiền, Hoàn Kiếm, Hà Nội',
                'description': 'Công trình kiến trúc Pháp tiêu biểu, được xây dựng từ 1901-1911. Là một trong những nhà hát opera đẹp nhất châu Á.',
                'latitude': 21.0245,
                'longitude': 105.8573,
                'avg_price': 400000,
                'region': 'north'
            },
            {
                'name': 'Chùa Trấn Quốc',
                'travel_type': 'Văn hóa',
                'location': 'Hà Nội',
                'address': 'Thanh Niên, Tây Hồ, Hà Nội',
                'description': 'Ngôi chùa cổ nhất Hà Nội với hơn 1500 năm lịch sử, nằm trên bán đảo nhỏ của Hồ Tây. Kiến trúc độc đáo với tháp Bảo Tháp 11 tầng.',
                'latitude': 21.0478,
                'longitude': 105.8367,
                'avg_price': 0,
                'region': 'north'
            },

            # Quảng Ninh
            {
                'name': 'Vịnh Hạ Long',
                'travel_type': 'Biển',
                'location': 'Quảng Ninh',
                'address': 'TP. Hạ Long, Quảng Ninh',
                'description': 'Di sản thiên nhiên thế giới UNESCO với gần 2000 đảo đá vôi. Cảnh quan kỳ vĩ với hang động, bãi tắm và hệ sinh thái đa dạng.',
                'latitude': 20.9101,
                'longitude': 107.1839,
                'avg_price': 250000,
                'region': 'north'
            },
            {
                'name': 'Đảo Cô Tô',
                'travel_type': 'Biển',
                'location': 'Quảng Ninh',
                'address': 'Huyện Cô Tô, Quảng Ninh',
                'description': 'Quần đảo hoang sơ với bãi biển trong xanh, cát trắng mịn. Điểm đến lý tưởng cho những ai yêu thích sự yên bình và thiên nhiên nguyên sơ.',
                'latitude': 21.0500,
                'longitude': 107.7700,
                'avg_price': 500000,
                'region': 'north'
            },

            # Ninh Bình
            {
                'name': 'Tràng An',
                'travel_type': 'Sinh thái',
                'location': 'Ninh Bình',
                'address': 'Hoa Lư, Ninh Bình',
                'description': 'Di sản văn hóa và thiên nhiên thế giới UNESCO. Quần thể hang động, thung lũng và đền chùa cổ kính giữa núi non hùng vĩ.',
                'latitude': 20.2544,
                'longitude': 105.8989,
                'avg_price': 200000,
                'region': 'north'
            },
            {
                'name': 'Tam Cốc - Bích Động',
                'travel_type': 'Sinh thái',
                'location': 'Ninh Bình',
                'address': 'Hoa Lư, Ninh Bình',
                'description': 'Được mệnh danh là "Hạ Long trên cạn" với cảnh quan sông nước, núi non hữu tình. Đi thuyền qua 3 hang động tự nhiên xuyên núi.',
                'latitude': 20.2150,
                'longitude': 105.9200,
                'avg_price': 150000,
                'region': 'north'
            },
            {
                'name': 'Chùa Bái Đính',
                'travel_type': 'Văn hóa',
                'location': 'Ninh Bình',
                'address': 'Gia Sinh, Gia Viễn, Ninh Bình',
                'description': 'Quần thể chùa lớn nhất Đông Nam Á với nhiều kỷ lục: tượng Phật bằng đồng lớn nhất, hành lang La Hán dài nhất...',
                'latitude': 20.2700,
                'longitude': 105.8700,
                'avg_price': 0,
                'region': 'north'
            },

            # Lào Cai
            {
                'name': 'Sa Pa',
                'travel_type': 'Núi',
                'location': 'Lào Cai',
                'address': 'Thị xã Sa Pa, Lào Cai',
                'description': 'Thị trấn trong sương với ruộng bậc thang tuyệt đẹp, văn hóa dân tộc đa dạng. Khí hậu mát mẻ quanh năm, có tuyết vào mùa đông.',
                'latitude': 22.3364,
                'longitude': 103.8438,
                'avg_price': 0,
                'region': 'north'
            },
            {
                'name': 'Đỉnh Fansipan',
                'travel_type': 'Núi',
                'location': 'Lào Cai',
                'address': 'Sa Pa, Lào Cai',
                'description': 'Nóc nhà Đông Dương cao 3143m. Có thể chinh phục bằng cáp treo hoặc leo núi. Cảnh quan hùng vĩ với biển mây bồng bềnh.',
                'latitude': 22.3033,
                'longitude': 103.7750,
                'avg_price': 700000,
                'region': 'north'
            },

            # Hà Giang
            {
                'name': 'Cao nguyên đá Đồng Văn',
                'travel_type': 'Núi',
                'location': 'Hà Giang',
                'address': 'Đồng Văn, Hà Giang',
                'description': 'Công viên địa chất toàn cầu UNESCO với cảnh quan núi đá hùng vĩ. Cung đường đèo Mã Pí Lèng được mệnh danh là "Vua của các con đèo".',
                'latitude': 23.2800,
                'longitude': 105.3600,
                'avg_price': 0,
                'region': 'north'
            },

            # Hải Phòng
            {
                'name': 'Đảo Cát Bà',
                'travel_type': 'Biển',
                'location': 'Hải Phòng',
                'address': 'Huyện Cát Hải, Hải Phòng',
                'description': 'Đảo lớn nhất trong quần thể Vịnh Hạ Long với vườn quốc gia, bãi biển đẹp và hệ sinh thái đa dạng.',
                'latitude': 20.7300,
                'longitude': 107.0500,
                'avg_price': 0,
                'region': 'north'
            },

            # ==================== MIỀN TRUNG ====================
            # Đà Nẵng
            {
                'name': 'Bà Nà Hills',
                'travel_type': 'Núi',
                'location': 'Đà Nẵng',
                'address': 'Hòa Ninh, Hòa Vang, Đà Nẵng',
                'description': 'Khu du lịch nghỉ dưỡng trên núi với Cầu Vàng nổi tiếng thế giới. Có cáp treo dài nhất thế giới, làng Pháp cổ kính và nhiều trò chơi.',
                'latitude': 15.9959,
                'longitude': 107.9953,
                'avg_price': 900000,
                'region': 'central'
            },
            {
                'name': 'Bãi biển Mỹ Khê',
                'travel_type': 'Biển',
                'location': 'Đà Nẵng',
                'address': 'Phường Phước Mỹ, Sơn Trà, Đà Nẵng',
                'description': 'Một trong 6 bãi biển quyến rũ nhất hành tinh theo Forbes. Bãi cát trắng mịn, nước biển trong xanh, sóng êm.',
                'latitude': 16.0544,
                'longitude': 108.2478,
                'avg_price': 0,
                'region': 'central'
            },
            {
                'name': 'Cầu Rồng',
                'travel_type': 'Thành phố',
                'location': 'Đà Nẵng',
                'address': 'Cầu Rồng, Sông Hàn, Đà Nẵng',
                'description': 'Biểu tượng của Đà Nẵng với hình dáng con rồng dài 666m. Phun lửa và nước vào 21h thứ 7, Chủ nhật.',
                'latitude': 16.0610,
                'longitude': 108.2270,
                'avg_price': 0,
                'region': 'central'
            },
            {
                'name': 'Ngũ Hành Sơn',
                'travel_type': 'Văn hóa',
                'location': 'Đà Nẵng',
                'address': 'Ngũ Hành Sơn, Đà Nẵng',
                'description': 'Quần thể 5 ngọn núi đá vôi với nhiều hang động, chùa chiền cổ kính. Làng nghề điêu khắc đá nổi tiếng.',
                'latitude': 16.0030,
                'longitude': 108.2630,
                'avg_price': 40000,
                'region': 'central'
            },
            {
                'name': 'Bán đảo Sơn Trà',
                'travel_type': 'Sinh thái',
                'location': 'Đà Nẵng',
                'address': 'Quận Sơn Trà, Đà Nẵng',
                'description': 'Khu bảo tồn thiên nhiên với rừng nguyên sinh, voọc chà vá chân nâu quý hiếm. Có chùa Linh Ứng với tượng Phật Quan Âm cao 67m.',
                'latitude': 16.1200,
                'longitude': 108.2800,
                'avg_price': 0,
                'region': 'central'
            },

            # Quảng Nam
            {
                'name': 'Phố cổ Hội An',
                'travel_type': 'Văn hóa',
                'location': 'Quảng Nam',
                'address': 'TP. Hội An, Quảng Nam',
                'description': 'Di sản văn hóa thế giới UNESCO với kiến trúc cổ kính, đèn lồng rực rỡ. Thương cảng sầm uất một thời với sự giao thoa văn hóa Việt-Hoa-Nhật.',
                'latitude': 15.8801,
                'longitude': 108.3380,
                'avg_price': 120000,
                'region': 'central'
            },
            {
                'name': 'Thánh địa Mỹ Sơn',
                'travel_type': 'Văn hóa',
                'location': 'Quảng Nam',
                'address': 'Duy Phú, Duy Xuyên, Quảng Nam',
                'description': 'Di sản văn hóa thế giới UNESCO, quần thể đền tháp Chăm Pa cổ kính. Kiến trúc độc đáo với kỹ thuật xây dựng bí ẩn.',
                'latitude': 15.7640,
                'longitude': 108.1240,
                'avg_price': 150000,
                'region': 'central'
            },
            {
                'name': 'Cù Lao Chàm',
                'travel_type': 'Biển',
                'location': 'Quảng Nam',
                'address': 'Tân Hiệp, Hội An, Quảng Nam',
                'description': 'Khu dự trữ sinh quyển thế giới với san hô đa dạng, bãi biển hoang sơ. Lý tưởng cho lặn biển và khám phá thiên nhiên.',
                'latitude': 15.9500,
                'longitude': 108.5200,
                'avg_price': 500000,
                'region': 'central'
            },

            # Thừa Thiên Huế
            {
                'name': 'Đại Nội Huế',
                'travel_type': 'Văn hóa',
                'location': 'Thừa Thiên Huế',
                'address': 'Phú Hậu, TP. Huế',
                'description': 'Di sản văn hóa thế giới UNESCO, cung điện của các vua triều Nguyễn. Kiến trúc cung đình độc đáo với Ngọ Môn, Điện Thái Hòa...',
                'latitude': 16.4698,
                'longitude': 107.5790,
                'avg_price': 200000,
                'region': 'central'
            },
            {
                'name': 'Chùa Thiên Mụ',
                'travel_type': 'Văn hóa',
                'location': 'Thừa Thiên Huế',
                'address': 'Kim Long, TP. Huế',
                'description': 'Ngôi chùa cổ nhất Huế với tháp Phước Duyên 7 tầng biểu tượng. Nằm bên bờ sông Hương thơ mộng.',
                'latitude': 16.4536,
                'longitude': 107.5450,
                'avg_price': 0,
                'region': 'central'
            },
            {
                'name': 'Lăng Tự Đức',
                'travel_type': 'Văn hóa',
                'location': 'Thừa Thiên Huế',
                'address': 'Thủy Xuân, TP. Huế',
                'description': 'Lăng mộ đẹp nhất trong hệ thống lăng tẩm Huế. Kiến trúc hài hòa với thiên nhiên, hồ sen, đồi thông.',
                'latitude': 16.4580,
                'longitude': 107.5470,
                'avg_price': 150000,
                'region': 'central'
            },
            {
                'name': 'Biển Lăng Cô',
                'travel_type': 'Biển',
                'location': 'Thừa Thiên Huế',
                'address': 'Lăng Cô, Phú Lộc, Thừa Thiên Huế',
                'description': 'Một trong những vịnh đẹp nhất thế giới với bãi cát trắng dài 10km, nước biển trong xanh và đầm phá Lập An.',
                'latitude': 16.2500,
                'longitude': 108.0700,
                'avg_price': 0,
                'region': 'central'
            },

            # Khánh Hòa
            {
                'name': 'Vịnh Nha Trang',
                'travel_type': 'Biển',
                'location': 'Khánh Hòa',
                'address': 'TP. Nha Trang, Khánh Hòa',
                'description': 'Một trong 29 vịnh đẹp nhất thế giới với 19 đảo lớn nhỏ. Thiên đường biển với san hô, cá nhiệt đới đa dạng.',
                'latitude': 12.2388,
                'longitude': 109.1967,
                'avg_price': 0,
                'region': 'central'
            },
            {
                'name': 'Vinpearl Land Nha Trang',
                'travel_type': 'Giải trí',
                'location': 'Khánh Hòa',
                'address': 'Đảo Hòn Tre, Nha Trang',
                'description': 'Khu vui chơi giải trí lớn nhất Việt Nam với công viên nước, thủy cung, vườn thú và nhiều trò chơi cảm giác mạnh.',
                'latitude': 12.2200,
                'longitude': 109.2300,
                'avg_price': 880000,
                'region': 'central'
            },
            {
                'name': 'Tháp Bà Ponagar',
                'travel_type': 'Văn hóa',
                'location': 'Khánh Hòa',
                'address': '2 Tháng 4, Vĩnh Phước, Nha Trang',
                'description': 'Quần thể đền tháp Chăm Pa cổ kính trên đồi Cù Lao. Kiến trúc độc đáo thờ nữ thần Ponagar.',
                'latitude': 12.2650,
                'longitude': 109.1950,
                'avg_price': 22000,
                'region': 'central'
            },

            # Bình Thuận
            {
                'name': 'Mũi Né',
                'travel_type': 'Biển',
                'location': 'Bình Thuận',
                'address': 'Mũi Né, Phan Thiết, Bình Thuận',
                'description': 'Thiên đường nghỉ dưỡng với đồi cát bay, suối tiên và bãi biển đẹp. Điểm đến lý tưởng cho lướt ván diều.',
                'latitude': 10.9333,
                'longitude': 108.2833,
                'avg_price': 0,
                'region': 'central'
            },
            {
                'name': 'Đồi cát Mũi Né',
                'travel_type': 'Sinh thái',
                'location': 'Bình Thuận',
                'address': 'Mũi Né, Phan Thiết, Bình Thuận',
                'description': 'Đồi cát vàng và đồi cát đỏ độc đáo, thay đổi hình dạng theo gió. Trượt cát và ngắm bình minh là trải nghiệm không thể bỏ qua.',
                'latitude': 10.9400,
                'longitude': 108.3000,
                'avg_price': 50000,
                'region': 'central'
            },

            # Lâm Đồng
            {
                'name': 'Thành phố Đà Lạt',
                'travel_type': 'Núi',
                'location': 'Lâm Đồng',
                'address': 'TP. Đà Lạt, Lâm Đồng',
                'description': 'Thành phố ngàn hoa với khí hậu mát mẻ quanh năm. Kiến trúc Pháp cổ kính, hồ Xuân Hương thơ mộng và vườn hoa rực rỡ.',
                'latitude': 11.9404,
                'longitude': 108.4583,
                'avg_price': 0,
                'region': 'central'
            },
            {
                'name': 'Thung lũng Tình Yêu',
                'travel_type': 'Sinh thái',
                'location': 'Lâm Đồng',
                'address': '7 Mai Anh Đào, Phường 8, Đà Lạt',
                'description': 'Thung lũng thơ mộng với hồ nước, đồi thông và vườn hoa. Điểm đến lãng mạn cho các cặp đôi.',
                'latitude': 11.9700,
                'longitude': 108.4400,
                'avg_price': 100000,
                'region': 'central'
            },
            {
                'name': 'Đồi chè Cầu Đất',
                'travel_type': 'Sinh thái',
                'location': 'Lâm Đồng',
                'address': 'Cầu Đất, Đà Lạt, Lâm Đồng',
                'description': 'Đồi chè xanh mướt trải dài bất tận, không khí trong lành. Điểm check-in tuyệt đẹp với sương mù buổi sáng.',
                'latitude': 11.8500,
                'longitude': 108.5500,
                'avg_price': 0,
                'region': 'central'
            },

            # ==================== MIỀN NAM ====================
            # TP. Hồ Chí Minh
            {
                'name': 'Nhà thờ Đức Bà',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '01 Công xã Paris, Bến Nghé, Quận 1',
                'description': 'Nhà thờ Công giáo La Mã với kiến trúc Gothic độc đáo, được xây dựng từ 1863-1880. Biểu tượng của Sài Gòn.',
                'latitude': 10.7797,
                'longitude': 106.6990,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Dinh Độc Lập',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '135 Nam Kỳ Khởi Nghĩa, Quận 1',
                'description': 'Di tích lịch sử quốc gia đặc biệt, nơi diễn ra sự kiện lịch sử 30/4/1975. Kiến trúc hiện đại độc đáo.',
                'latitude': 10.7769,
                'longitude': 106.6955,
                'avg_price': 65000,
                'region': 'south'
            },
            {
                'name': 'Chợ Bến Thành',
                'travel_type': 'Ẩm thực',
                'location': 'TP Hồ Chí Minh',
                'address': 'Lê Lợi, Phường Bến Thành, Quận 1',
                'description': 'Chợ truyền thống biểu tượng của Sài Gòn với đa dạng hàng hóa, ẩm thực đường phố và đồ lưu niệm.',
                'latitude': 10.7720,
                'longitude': 106.6981,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Bến Nhà Rồng',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '01 Nguyễn Tất Thành, Quận 4',
                'description': 'Bến cảng lịch sử nơi Bác Hồ ra đi tìm đường cứu nước năm 1911. Nay là Bảo tàng Hồ Chí Minh.',
                'latitude': 10.7676,
                'longitude': 106.7073,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Phố đi bộ Nguyễn Huệ',
                'travel_type': 'Thành phố',
                'location': 'TP Hồ Chí Minh',
                'address': 'Đường Nguyễn Huệ, Quận 1',
                'description': 'Không gian đi bộ hiện đại với đài phun nước, tượng Bác Hồ và nhiều hoạt động văn hóa nghệ thuật.',
                'latitude': 10.7743,
                'longitude': 106.7012,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Bảo tàng Chứng tích Chiến tranh',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': '28 Võ Văn Tần, Quận 3',
                'description': 'Bảo tàng lưu giữ những chứng tích về chiến tranh Việt Nam. Một trong những bảo tàng được ghé thăm nhiều nhất.',
                'latitude': 10.7797,
                'longitude': 106.6918,
                'avg_price': 40000,
                'region': 'south'
            },
            {
                'name': 'Địa đạo Củ Chi',
                'travel_type': 'Văn hóa',
                'location': 'TP Hồ Chí Minh',
                'address': 'Phú Hiệp, Củ Chi',
                'description': 'Hệ thống địa đạo dài hơn 200km, chứng tích của cuộc kháng chiến. Trải nghiệm chui địa đạo và bắn súng.',
                'latitude': 11.1400,
                'longitude': 106.4600,
                'avg_price': 110000,
                'region': 'south'
            },

            # Kiên Giang
            {
                'name': 'Đảo Phú Quốc',
                'travel_type': 'Biển',
                'location': 'Kiên Giang',
                'address': 'Huyện Phú Quốc, Kiên Giang',
                'description': 'Đảo ngọc lớn nhất Việt Nam với bãi biển đẹp, rừng nguyên sinh và hải sản tươi ngon. Thiên đường nghỉ dưỡng.',
                'latitude': 10.2899,
                'longitude': 103.9840,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Vinpearl Safari Phú Quốc',
                'travel_type': 'Giải trí',
                'location': 'Kiên Giang',
                'address': 'Gành Dầu, Phú Quốc',
                'description': 'Vườn thú bán hoang dã lớn nhất Việt Nam với hơn 3000 cá thể động vật từ khắp nơi trên thế giới.',
                'latitude': 10.3800,
                'longitude': 103.8600,
                'avg_price': 650000,
                'region': 'south'
            },
            {
                'name': 'Bãi Sao Phú Quốc',
                'travel_type': 'Biển',
                'location': 'Kiên Giang',
                'address': 'An Thới, Phú Quốc',
                'description': 'Bãi biển đẹp nhất Phú Quốc với cát trắng mịn như bột, nước biển trong xanh như ngọc.',
                'latitude': 10.0500,
                'longitude': 104.0200,
                'avg_price': 0,
                'region': 'south'
            },

            # Cần Thơ
            {
                'name': 'Chợ nổi Cái Răng',
                'travel_type': 'Văn hóa',
                'location': 'Cần Thơ',
                'address': 'Cái Răng, Cần Thơ',
                'description': 'Chợ nổi lớn nhất miền Tây với hoạt động mua bán trên sông từ sáng sớm. Nét văn hóa đặc trưng vùng sông nước.',
                'latitude': 10.0167,
                'longitude': 105.7500,
                'avg_price': 150000,
                'region': 'south'
            },
            {
                'name': 'Bến Ninh Kiều',
                'travel_type': 'Thành phố',
                'location': 'Cần Thơ',
                'address': 'Hai Bà Trưng, Ninh Kiều, Cần Thơ',
                'description': 'Bến tàu du lịch nổi tiếng bên bờ sông Hậu. Điểm xuất phát đi chợ nổi và ngắm cảnh sông nước.',
                'latitude': 10.0333,
                'longitude': 105.7833,
                'avg_price': 0,
                'region': 'south'
            },

            # Bà Rịa - Vũng Tàu
            {
                'name': 'Bãi Sau Vũng Tàu',
                'travel_type': 'Biển',
                'location': 'Bà Rịa - Vũng Tàu',
                'address': 'Thùy Vân, TP. Vũng Tàu',
                'description': 'Bãi biển dài 8km với cát mịn, sóng êm. Điểm đến gần Sài Gòn nhất cho du lịch biển cuối tuần.',
                'latitude': 10.3400,
                'longitude': 107.0900,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Tượng Chúa Kitô Vua',
                'travel_type': 'Văn hóa',
                'location': 'Bà Rịa - Vũng Tàu',
                'address': 'Núi Nhỏ, TP. Vũng Tàu',
                'description': 'Tượng Chúa cao 32m trên đỉnh núi Nhỏ. Leo 847 bậc thang để ngắm toàn cảnh Vũng Tàu từ trên cao.',
                'latitude': 10.3267,
                'longitude': 107.0833,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Côn Đảo',
                'travel_type': 'Biển',
                'location': 'Bà Rịa - Vũng Tàu',
                'address': 'Huyện Côn Đảo',
                'description': 'Quần đảo hoang sơ với bãi biển đẹp, rừng nguyên sinh và di tích lịch sử nhà tù Côn Đảo.',
                'latitude': 8.6833,
                'longitude': 106.6000,
                'avg_price': 0,
                'region': 'south'
            },

            # An Giang
            {
                'name': 'Núi Cấm',
                'travel_type': 'Núi',
                'location': 'An Giang',
                'address': 'An Hảo, Tịnh Biên, An Giang',
                'description': 'Ngọn núi cao nhất đồng bằng sông Cửu Long với nhiều chùa chiền, hang động và khí hậu mát mẻ.',
                'latitude': 10.5167,
                'longitude': 104.9833,
                'avg_price': 0,
                'region': 'south'
            },
            {
                'name': 'Rừng tràm Trà Sư',
                'travel_type': 'Sinh thái',
                'location': 'An Giang',
                'address': 'Văn Giáo, Tịnh Biên, An Giang',
                'description': 'Rừng tràm ngập nước với hệ sinh thái đa dạng, đàn cò trắng bay rợp trời. Đi xuồng xuyên rừng tràm.',
                'latitude': 10.5500,
                'longitude': 105.0000,
                'avg_price': 100000,
                'region': 'south'
            },

            # Đồng Tháp
            {
                'name': 'Vườn quốc gia Tràm Chim',
                'travel_type': 'Sinh thái',
                'location': 'Đồng Tháp',
                'address': 'Tam Nông, Đồng Tháp',
                'description': 'Khu Ramsar thế giới với đàn sếu đầu đỏ quý hiếm. Hệ sinh thái đất ngập nước đặc trưng Đồng Tháp Mười.',
                'latitude': 10.7167,
                'longitude': 105.5167,
                'avg_price': 60000,
                'region': 'south'
            },

            # Bến Tre
            {
                'name': 'Cồn Phụng',
                'travel_type': 'Sinh thái',
                'location': 'Bến Tre',
                'address': 'Tân Thạch, Châu Thành, Bến Tre',
                'description': 'Cồn xanh giữa sông Tiền với vườn dừa, làng nghề truyền thống. Trải nghiệm đi xuồng ba lá, nghe đờn ca tài tử.',
                'latitude': 10.2833,
                'longitude': 106.4500,
                'avg_price': 150000,
                'region': 'south'
            },

            # Tây Ninh
            {
                'name': 'Núi Bà Đen',
                'travel_type': 'Núi',
                'location': 'Tây Ninh',
                'address': 'Thành phố Tây Ninh',
                'description': 'Ngọn núi cao nhất Nam Bộ (986m) với chùa Bà và cáp treo hiện đại. Điểm hành hương và du lịch tâm linh.',
                'latitude': 11.3667,
                'longitude': 106.1500,
                'avg_price': 200000,
                'region': 'south'
            },
            {
                'name': 'Tòa Thánh Cao Đài',
                'travel_type': 'Văn hóa',
                'location': 'Tây Ninh',
                'address': 'Long Hoa, Hòa Thành, Tây Ninh',
                'description': 'Thánh địa của đạo Cao Đài với kiến trúc độc đáo pha trộn Đông-Tây. Nghi lễ cúng tế đặc sắc.',
                'latitude': 11.2833,
                'longitude': 106.1167,
                'avg_price': 0,
                'region': 'south'
            },
        ]
