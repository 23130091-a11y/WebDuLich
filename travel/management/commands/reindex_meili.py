"""
Reindex toàn bộ Destination + TourPackage lên Meilisearch Cloud.

Dùng khi: lần cấu hình Meilisearch đầu tiên, hoặc index bị lệch với DB
(ví dụ cloud reset, hoặc từng tắt sync bằng cách xóa env).

Usage:
    python manage.py reindex_meili
    python manage.py reindex_meili --batch-size 1000

Yêu cầu MEILI_HOST + MEILI_API_KEY đã set trong .env. Thiếu → hiện
hướng dẫn rồi thoát lỗi (không index gì cả).
"""

from django.core.management.base import BaseCommand, CommandError

from travel.services import meili_service


class Command(BaseCommand):
    help = 'Reindex toàn bộ Destination + TourPackage lên Meilisearch Cloud'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', type=int, default=500,
            help='Số document gửi mỗi batch (mặc định 500)',
        )

    def handle(self, *args, **options):
        if not meili_service.is_enabled():
            raise CommandError(
                'Meilisearch chưa cấu hình. Set MEILI_HOST và MEILI_API_KEY '
                'trong .env (lấy từ https://cloud.meilisearch.com) rồi chạy lại.'
            )

        self.stdout.write('Đang submit documents lên Meilisearch...')
        stats = meili_service.bulk_reindex(batch_size=options['batch_size'])

        if 'error' in stats:
            raise CommandError(stats['error'])

        self.stdout.write(self.style.SUCCESS(
            f"Done: {stats['destinations']} destinations, "
            f"{stats['tours']} tours đã submit. "
            "Meilisearch sẽ index async trong vài giây."
        ))
