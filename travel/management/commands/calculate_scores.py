# Script tính toán điểm gợi ý (chạy định kỳ)

from django.core.management.base import BaseCommand
from travel.ai_module import recalculate_all_scores

class Command(BaseCommand):
    help = 'Tính toán lại điểm gợi ý cho tất cả địa điểm'

    def handle(self, *args, **kwargs):
        self.stdout.write('Bắt đầu tính toán điểm gợi ý...')
        
        results = recalculate_all_scores()
        
        self.stdout.write('\nKết quả:')
        for result in results:
            self.stdout.write(f"  {result['destination']}: {result['score']:.2f} điểm")
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Đã tính toán {len(results)} địa điểm!'))
