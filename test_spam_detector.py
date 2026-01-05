"""
Test Spam Detection System
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.spam_detector import check_spam, get_spam_detector
from django.core.cache import cache

# Clear cache before testing
cache.clear()

print("=" * 80)
print("SPAM DETECTION SYSTEM TEST")
print("=" * 80)

# Test cases - each with unique IP to avoid rate limiting
test_cases = [
    # SHOULD BLOCK (spam)
    ("Liên hệ zalo 0912345678 để được tư vấn", "block", "phone + spam keywords", "1.1.1.1"),
    ("Mua hàng tại https://shopee.vn/abc giá rẻ", "block", "link + spam keywords", "1.1.1.2"),
    ("INBOX ĐỂ ĐƯỢC GIÁ TỐT NHẤT!!!", "pending/shadow", "spam keywords + caps", "1.1.1.3"),
    ("Đại lý chính hãng, liên hệ sđt 0987654321", "block", "phone + spam keywords", "1.1.1.4"),
    
    # SHOULD PENDING/SHADOW (suspicious)
    ("Giá rẻ nhất thị trường, khuyến mãi lớn", "pending/shadow", "spam keywords", "1.1.1.5"),
    ("ok ok ok ok ok ok", "low_quality/allow", "repeated + low quality", "1.1.1.6"),
    ("!!!!!!!!!!!!!!!", "pending/shadow", "repeated chars", "1.1.1.7"),
    
    # SHOULD ALLOW (legitimate)
    ("Địa điểm rất đẹp, view tuyệt vời, recommend mạnh!", "allow", "positive review", "1.1.1.8"),
    ("Dịch vụ tệ, nhân viên thái độ kém, không bao giờ quay lại", "allow", "negative review", "1.1.1.9"),
    ("Tạm ổn, giá hơi cao nhưng cảnh đẹp", "allow", "mixed review", "1.1.1.10"),
    ("Cảnh đẹp, phòng sạch sẽ, nhân viên thân thiện", "allow", "positive review", "1.1.1.11"),
    
    # LOW QUALITY (allow but flag)
    ("ok", "low_quality", "too short", "1.1.1.12"),
    ("tốt", "low_quality", "too short", "1.1.1.13"),
    ("...", "low_quality/shadow", "only punctuation", "1.1.1.14"),
    ("😍😍😍", "low_quality/shadow", "only emojis", "1.1.1.15"),
]

print("\n📊 TEST RESULTS:\n")
passed = 0
failed = 0

for comment, expected_action, description, ip in test_cases:
    result = check_spam(comment, user_ip=ip)
    
    # Check if action matches expected
    action = result['action']
    
    # Handle multiple expected actions (e.g., "block/pending")
    expected_actions = expected_action.split('/')
    is_pass = action in expected_actions
    
    if is_pass:
        status = "✅ PASS"
        passed += 1
    else:
        status = "❌ FAIL"
        failed += 1
    
    print(f"{status} | Expected: {expected_action:15} | Got: {action:12} | Score: {result['spam_score']:.2f}")
    print(f"       Comment: {comment[:50]}...")
    print(f"       Flags: {result['flags']}")
    print()

print("=" * 80)
print(f"SUMMARY: {passed}/{len(test_cases)} passed ({passed/len(test_cases)*100:.1f}%)")
print("=" * 80)

# Test rate limiting separately
print("\n📊 RATE LIMITING TEST:\n")
cache.clear()  # Clear cache for fresh test

test_ip = "10.0.0.99"
for i in range(12):
    result = check_spam("Test review " + str(i), user_ip=test_ip)
    if i >= 9:
        print(f"Review {i+1}: action={result['action']}, score={result['spam_score']:.2f}, flags={result['flags']}")

print("\n✅ Rate limiting working!" if result['spam_score'] > 0.3 else "\n⚠️ Rate limiting may need adjustment")
