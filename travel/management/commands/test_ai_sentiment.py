"""
Management command để test AI sentiment analysis
"""

from django.core.management.base import BaseCommand
from travel.ai_sentiment import get_sentiment_analyzer


class Command(BaseCommand):
    help = 'Test AI sentiment analysis với các câu mẫu'

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO(
            '\n' + '='*60 + '\n'
            '🤖 TEST AI SENTIMENT ANALYSIS\n'
            '='*60 + '\n'
        ))
        
        # Test cases
        test_cases = [
            "Cảnh đẹp, dịch vụ tốt, rất hài lòng!",
            "Không đẹp, dịch vụ tệ, thất vọng",
            "Không tệ, khá ổn",
            "Đắt nhưng xứng đáng",
            "Giá hơi cao nhưng cảnh đẹp bù lại",
            "Tệ quá, không nên đi",
            "Rất tuyệt vời, recommend!",
            "Bình thường, không có gì đặc biệt",
            "Cảnh đẹp nhưng đông người quá",
            "Không như mong đợi, hơi thất vọng"
        ]
        
        analyzer = get_sentiment_analyzer()
        
        self.stdout.write('\n📝 Đang load AI model...\n')
        analyzer.load_model()
        
        if not analyzer.model_loaded:
            self.stdout.write(self.style.WARNING(
                '⚠️ AI model không load được, sử dụng rule-based\n'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✅ AI model loaded on {analyzer.device}\n'
            ))
        
        self.stdout.write('\n📊 KẾT QUẢ PHÂN TÍCH:\n')
        self.stdout.write('-' * 60 + '\n')
        
        for i, text in enumerate(test_cases, 1):
            score, confidence, label, keywords = analyzer.analyze(text)
            
            # Format output
            if label == 'positive':
                label_colored = self.style.SUCCESS(f'✓ {label.upper()}')
            elif label == 'negative':
                label_colored = self.style.ERROR(f'✗ {label.upper()}')
            else:
                label_colored = self.style.WARNING(f'○ {label.upper()}')
            
            self.stdout.write(f'\n{i}. "{text}"')
            self.stdout.write(f'   {label_colored}')
            self.stdout.write(f'   Score: {score:+.3f} | Confidence: {confidence:.2%}')
            if keywords:
                self.stdout.write(f'   Keywords: {", ".join(keywords)}')
        
        self.stdout.write('\n' + '='*60 + '\n')
        self.stdout.write(self.style.SUCCESS('✅ Test hoàn tất!\n'))
