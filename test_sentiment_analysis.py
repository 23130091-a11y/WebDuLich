#!/usr/bin/env python
import os
import django
import sys

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.ai_engine import analyze_sentiment

def test_sentiment_cases():
    """Test sentiment analysis with problematic cases"""
    
    test_cases = [
        # Negative cases that should be detected
        ("không có gì ngoài bụi hết á", "NEGATIVE", "Chê bai, phàn nàn về bụi bẩn"),
        ("chỉ toàn bụi thôi", "NEGATIVE", "Phàn nàn về bụi"),
        ("bẩn quá, không thích", "NEGATIVE", "Chê bẩn"),
        ("tệ lắm, không nên đi", "NEGATIVE", "Đánh giá tiêu cực"),
        ("thất vọng quá", "NEGATIVE", "Thất vọng"),
        ("dở tệ", "NEGATIVE", "Chê bai"),
        ("không đáng tiền", "NEGATIVE", "Không hài lòng về giá trị"),
        
        # Positive cases
        ("đẹp lắm, nên đi", "POSITIVE", "Khen ngợi"),
        ("tuyệt vời", "POSITIVE", "Tích cực"),
        ("rất hài lòng", "POSITIVE", "Hài lòng"),
        ("view đẹp", "POSITIVE", "Khen cảnh đẹp"),
        
        # Neutral cases
        ("bình thường thôi", "NEUTRAL", "Trung tính"),
        ("cũng được", "NEUTRAL", "Trung tính"),
    ]
    
    print("="*80)
    print("TESTING SENTIMENT ANALYSIS")
    print("="*80)
    
    correct = 0
    total = len(test_cases)
    
    for text, expected, description in test_cases:
        result = analyze_sentiment(text)
        
        # analyze_sentiment returns tuple: (score, pos_kw, neg_kw, metadata)
        score, pos_keywords, neg_keywords, metadata = result
        
        # Determine predicted sentiment
        if score > 0.1:
            predicted = "POSITIVE"
        elif score < -0.1:
            predicted = "NEGATIVE"
        else:
            predicted = "NEUTRAL"
        
        is_correct = predicted == expected
        if is_correct:
            correct += 1
            status = "✅ CORRECT"
        else:
            status = "❌ WRONG"
        
        print(f"\n{status}")
        print(f"Text: '{text}'")
        print(f"Expected: {expected} | Predicted: {predicted} (score: {score:.3f})")
        print(f"Description: {description}")
        print(f"Positive keywords: {pos_keywords}")
        print(f"Negative keywords: {neg_keywords}")
        print("-" * 60)
    
    accuracy = (correct / total) * 100
    print(f"\n{'='*80}")
    print(f"ACCURACY: {correct}/{total} = {accuracy:.1f}%")
    print(f"{'='*80}")
    
    if accuracy < 70:
        print("\n⚠️  SENTIMENT ANALYSIS NEEDS IMPROVEMENT!")
        print("Suggestions:")
        print("1. Add more negative keywords to travel_sentiment_keywords.json")
        print("2. Fine-tune the PhoBERT model with more training data")
        print("3. Adjust sentiment scoring thresholds")
        print("4. Add context-aware rules for travel domain")

if __name__ == "__main__":
    test_sentiment_cases()