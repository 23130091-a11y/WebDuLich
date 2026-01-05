"""
Test các edge cases đặc biệt
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.ai_engine import analyze_sentiment

# Test cases đặc biệt
test_cases = [
    # Q19: Incomplete phrases
    ("đắt nhưng đáng", "Incomplete positive"),
    ("rẻ nhưng tệ", "Incomplete negative"),
    ("đẹp nhưng xa", "Incomplete mixed"),
    
    # Complete versions
    ("đắt nhưng đáng tiền", "Complete positive"),
    ("rẻ nhưng tệ", "Complete negative"),
    ("đẹp nhưng xa trung tâm", "Complete mixed"),
    
    # More edge cases
    ("không tệ", "Negation of negative"),
    ("không đẹp", "Negation of positive"),
    ("cũng được", "Neutral soft"),
    ("tạm ổn", "Neutral soft"),
    ("ok", "Very short neutral"),
    ("tệ", "Very short negative"),
    ("đẹp", "Very short positive"),
]

print("=" * 80)
print("EDGE CASES TEST")
print("=" * 80)

for text, description in test_cases:
    score, pos_kw, neg_kw, meta = analyze_sentiment(text)
    
    # Determine sentiment
    if score > 0.15:
        sentiment = "POS"
    elif score < -0.15:
        sentiment = "NEG"
    else:
        sentiment = "NEU"
    
    print(f"\n'{text}' ({description})")
    print(f"  → Sentiment: {sentiment} (score: {score:.3f})")
    print(f"  → PhoBERT: {meta.get('phobert_score', 0):.3f}, Rule: {meta.get('rule_score', 0):.3f}")
    print(f"  → Method: {meta.get('method', 'unknown')}")
    print(f"  → Keywords: pos={pos_kw}, neg={neg_kw}")
