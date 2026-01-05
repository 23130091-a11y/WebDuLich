import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.ai_engine import analyze_sentiment
from collections import Counter

# Test cases với expected sentiment (P=positive, N=negative, NEU=neutral)
test_cases = [
    # === POSITIVE CASES ===
    ("Cảnh đẹp quá, rất thích!", "P", 0.5),
    ("View đẹp, phòng sạch sẽ, nhân viên thân thiện", "P", 0.6),
    ("Đáng đi lắm, sẽ quay lại", "P", 0.7),
    ("Tuyệt vời, recommend mạnh", "P", 0.8),
    ("Địa điểm xinh xắn, chụp hình đẹp", "P", 0.5),
    
    # === NEGATIVE CASES ===
    ("Dịch vụ tệ, nhân viên thái độ kém", "N", -0.5),
    ("Giá quá đắt, không đáng tiền", "N", -0.6),
    ("Bẩn quá, wc hôi, không bao giờ quay lại", "N", -0.7),
    ("Thất vọng, không như quảng cáo", "N", -0.6),
    ("Chặt chém du khách, lừa đảo", "N", -0.9),
    
    # === NEUTRAL/MIXED CASES (quan trọng!) ===
    ("Cũng được, không có gì đặc biệt", "NEU", -0.1),
    ("Tạm ổn, giá hơi cao", "NEU", -0.1),
    ("Ok thôi, bình thường", "NEU", 0.0),
    ("Cảnh đẹp nhưng đông quá", "NEU", 0.0),
    ("Phòng sạch, nhưng wifi yếu", "NEU", 0.0),
    ("Đồ ăn ngon, giá hơi mắc", "NEU", 0.0),
    ("Nhân viên thân thiện, cơ sở vật chất hơi cũ", "NEU", 0.0),
    ("View đẹp, nhưng xa trung tâm", "NEU", 0.0),
    ("Giá rẻ nhưng phòng nhỏ", "NEU", 0.0),
    
    # === TEENCODE/SLANG ===
    ("Dep lam, rat thich", "P", 0.5),
    ("Xin xo, dinh cao", "P", 0.7),
    ("Te qua, ko bao gio quay lai", "N", -0.6),
    ("Dc, cung ok", "NEU", 0.0),
    
    # === SPECIAL CASES ===
    ("Không tệ", "P", 0.1),  # Negation of negative = weak positive
    ("Không đẹp lắm", "N", -0.3),  # Negation of positive = negative
    ("Hơi đắt nhưng đáng tiền", "P", 0.3),
    ("Cảnh thì đẹp đó, nhưng giá cả hơi mắc nha", "NEU", 0.0),
    ("xung quanh bán đồ ăn hơi đắt, còn lại ok", "NEU", 0.0),
]

print("=" * 80)
print("COMPREHENSIVE SENTIMENT ANALYSIS TEST (PhoBERT-Primary v3.2)")
print("=" * 80)

correct = 0
total = len(test_cases)
results = []
method_counter = Counter()

for comment, expected_type, expected_threshold in test_cases:
    score, pos, neg, meta = analyze_sentiment(comment)
    method = meta.get('method', 'unknown')
    method_counter[method] += 1
    
    # Determine actual type
    if score > 0.15:
        actual_type = "P"
    elif score < -0.15:
        actual_type = "N"
    else:
        actual_type = "NEU"
    
    # Check if correct
    is_correct = actual_type == expected_type
    if is_correct:
        correct += 1
        status = "✓"
    else:
        status = "✗"
    
    results.append({
        'comment': comment[:50],
        'score': score,
        'expected': expected_type,
        'actual': actual_type,
        'status': status,
        'pos': pos,
        'neg': neg,
        'method': method,
        'phobert_score': meta.get('phobert_score', 0),
        'rule_score': meta.get('rule_score', 0),
        'confidence': meta.get('confidence', 0)
    })

# Print results
print(f"\n{'Comment':<52} {'Score':>7} {'Exp':>4} {'Act':>4} {'Status':>6}")
print("-" * 80)

for r in results:
    print(f"{r['comment']:<52} {r['score']:>7.3f} {r['expected']:>4} {r['actual']:>4} {r['status']:>6}")
    if r['status'] == "✗":
        print(f"   → pos: {r['pos']}, neg: {r['neg']}")
        print(f"   → method: {r['method']}, phobert: {r['phobert_score']:.3f}, rule: {r['rule_score']:.3f}")

print("-" * 80)
print(f"\nAccuracy: {correct}/{total} ({correct/total*100:.1f}%)")

# Summary by category
print("\n=== SUMMARY BY CATEGORY ===")
categories = {"P": [], "N": [], "NEU": []}
for r in results:
    categories[r['expected']].append(r)

for cat, items in categories.items():
    cat_correct = sum(1 for i in items if i['status'] == "✓")
    cat_name = {"P": "Positive", "N": "Negative", "NEU": "Neutral/Mixed"}[cat]
    print(f"{cat_name}: {cat_correct}/{len(items)} correct")

# Method distribution - QUAN TRỌNG để thấy PhoBERT đóng vai trò chính
print("\n=== METHOD DISTRIBUTION (PhoBERT Usage) ===")
phobert_methods = 0
total_methods = sum(method_counter.values())

for method, count in sorted(method_counter.items(), key=lambda x: -x[1]):
    pct = count / total_methods * 100
    is_phobert = "phobert" in method.lower()
    marker = "🤖" if is_phobert else "📝"
    print(f"{marker} {method}: {count} ({pct:.1f}%)")
    if is_phobert:
        phobert_methods += count

print(f"\n📊 PhoBERT-Primary Methods: {phobert_methods}/{total_methods} ({phobert_methods/total_methods*100:.1f}%)")
print(f"📊 Rule-Only Methods: {total_methods - phobert_methods}/{total_methods} ({(total_methods - phobert_methods)/total_methods*100:.1f}%)")
