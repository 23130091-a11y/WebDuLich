# -*- coding: utf-8 -*-
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'myproject.settings'
import django
django.setup()

from travel.ai_engine import analyze_sentiment

test_cases = [
    "cũng tạm",
    "tạm",
    "ok",
    "được",
    "ổn",
    "bình thường",
    "rất đẹp",
    "tệ quá",
    "Đi cho biết chứ trải nghiệm thật sự không đáng như kỳ vọng",
    "không đáng tiền",
    "không như kỳ vọng",
    "thất vọng",
]

print("=" * 60)
print("TEST SENTIMENT ANALYSIS - NEUTRAL SOFT WORDS")
print("=" * 60)

for text in test_cases:
    score, pos_kw, neg_kw, meta = analyze_sentiment(text)
    method = meta.get('method', 'unknown')
    
    if score > 0.18:
        label = "Tích cực"
    elif score < -0.18:
        label = "Tiêu cực"
    else:
        label = "Trung lập"
    
    print(f"\n'{text}'")
    print(f"  Score: {score:.3f} -> {label}")
    print(f"  Method: {method}")
    print(f"  Keywords: +{pos_kw} -{neg_kw}")
