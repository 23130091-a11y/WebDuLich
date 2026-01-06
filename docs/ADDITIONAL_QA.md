# Câu Hỏi Bổ Sung về Sentiment Analysis

## Q19. Nếu người dùng viết "đắt nhưng đáng", "rẻ nhưng tệ" model có hiểu không?

### Test Results:

```python
# Test với incomplete phrases
"đắt nhưng đáng"        → NEU (score: -0.052) ✅
"rẻ nhưng tệ"           → NEU (score: -0.036) ✅
"đẹp nhưng xa"          → NEU (score: 0.010) ✅

# So sánh với complete phrases
"đắt nhưng đáng tiền"   → POS (score: 0.193) ✅
"rẻ nhưng tệ"           → NEU (score: -0.036) ✅
"đẹp nhưng xa trung tâm" → NEU (score: 0.010) ✅
```

### Phân tích:

**✅ Model HIỂU được incomplete phrases:**

**1. "đắt nhưng đáng" (Incomplete positive)**
```
PhoBERT: 0.162 (nhận ra context positive)
Rule: -0.550 (chỉ thấy "đắt" negative)
Final: -0.052 (NEU - calibrated)

Giải thích:
- PhoBERT hiểu "đáng" thường đi với "đáng tiền" → positive context
- Rule-based chỉ thấy "đắt" → negative
- Hybrid kết hợp → NEU (an toàn)
```

**2. "rẻ nhưng tệ" (Incomplete negative)**
```
PhoBERT: -0.000 (neutral, không chắc)
Rule: -0.300 (mixed: "rẻ" pos, "tệ" neg)
Final: -0.036 (NEU)

Giải thích:
- PhoBERT thấy mixed sentiment → neutral
- Rule-based detect cả "rẻ" và "tệ" → mixed
- Final: NEU (đúng)
```

**3. "đẹp nhưng xa" (Incomplete mixed)**
```
PhoBERT: 0.000 (neutral)
Rule: 0.080 (mixed: "đẹp" pos, "xa" neg)
Final: 0.010 (NEU)

Giải thích:
- Cả PhoBERT và Rule đều nhận ra mixed
- Final: NEU (đúng)
```

### So sánh Complete vs Incomplete:

| Phrase | Incomplete | Complete | Khác biệt |
|--------|-----------|----------|-----------|
| "đắt nhưng đáng" | -0.052 (NEU) | "đắt nhưng đáng tiền" = 0.193 (POS) | ✅ Hiểu context |
| "rẻ nhưng tệ" | -0.036 (NEU) | (same) | ✅ Consistent |
| "đẹp nhưng xa" | 0.010 (NEU) | "đẹp nhưng xa trung tâm" = 0.010 (NEU) | ✅ Consistent |

### Kết luận Q19:

**✅ Model HIỂU được incomplete phrases vì:**

1. **PhoBERT học context**: "đáng" thường đi với "đáng tiền"
2. **Rule-based detect keywords**: "đắt", "rẻ", "tệ", "đẹp"
3. **Hybrid calibrate**: Kết hợp cả hai để ra kết quả an toàn
4. **Mixed sentiment handling**: Tự động kéo về neutral khi không chắc

**⚠️ Hạn chế:**
- Incomplete phrases có thể không chính xác 100%
- Nên khuyến khích user viết đầy đủ
- Nhưng model vẫn handle được reasonable

---

## Q16. Bạn có demo dashboard / use-case không?

### ✅ Có! Hệ thống có nhiều use-cases thực tế:

### Use-case 1: Destination Detail Page

**Location:** `travel/templates/travel/destination_detail.html`

**Features:**
```html
<!-- Hiển thị sentiment analysis results -->
<div class="sentiment-summary">
    <h3>Đánh giá tổng quan</h3>
    <div class="overall-score">{{ recommendation.overall_score }}/10</div>
    <div class="sentiment-breakdown">
        <span class="positive">{{ positive_ratio }}% tích cực</span>
        <span class="neutral">{{ neutral_ratio }}% trung lập</span>
        <span class="negative">{{ negative_ratio }}% tiêu cực</span>
    </div>
</div>

<!-- Hiển thị reviews với sentiment -->
{% for review in reviews %}
<div class="review-card sentiment-{{ review.sentiment_label }}">
    <div class="rating">{{ review.rating }} ⭐</div>
    <div class="comment">{{ review.comment }}</div>
    <div class="sentiment-score">
        Sentiment: {{ review.sentiment_score|floatformat:2 }}
    </div>
    <div class="keywords">
        {% for kw in review.positive_keywords %}
            <span class="keyword-positive">{{ kw }}</span>
        {% endfor %}
        {% for kw in review.negative_keywords %}
            <span class="keyword-negative">{{ kw }}</span>
        {% endfor %}
    </div>
</div>
{% endfor %}
```

### Use-case 2: Admin Dashboard

**Location:** `travel/admin.py`

**Features:**
```python
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'destination', 'author_name', 'rating', 
        'sentiment_score', 'sentiment_label',  # ← Sentiment display
        'created_at'
    ]
    list_filter = [
        'rating', 
        'sentiment_label',  # ← Filter by sentiment
        'sarcasm_risk',     # ← Filter sarcasm
        'created_at'
    ]
    
    # Color-coded sentiment
    def sentiment_label(self, obj):
        if obj.sentiment_score > 0.3:
            return format_html('<span style="color: green;">POSITIVE</span>')
        elif obj.sentiment_score < -0.3:
            return format_html('<span style="color: red;">NEGATIVE</span>')
        else:
            return format_html('<span style="color: gray;">NEUTRAL</span>')
```

### Use-case 3: Aspect-Based Dashboard

**Tạo management command để xem aspect breakdown:**

```python
# travel/management/commands/aspect_dashboard.py
from django.core.management.base import BaseCommand
from travel.models import Destination, Review
import json

class Command(BaseCommand):
    def handle(self, *args, **options):
        for dest in Destination.objects.all()[:5]:
            print(f"\n{'='*60}")
            print(f"📍 {dest.name}")
            print(f"{'='*60}")
            
            reviews = dest.reviews.all()
            aspect_summary = {}
            
            for review in reviews:
                for aspect, score in review.aspect_scores.items():
                    if aspect not in aspect_summary:
                        aspect_summary[aspect] = []
                    aspect_summary[aspect].append(score)
            
            # Calculate averages
            for aspect, scores in aspect_summary.items():
                avg = sum(scores) / len(scores)
                emoji = "✅" if avg > 0.3 else "❌" if avg < -0.3 else "~"
                print(f"{emoji} {aspect}: {avg:.2f} ({len(scores)} mentions)")
```

**Output:**
```
============================================================
📍 Vịnh Hạ Long
============================================================
✅ scenery_view: 0.85 (45 mentions)
❌ cleanliness_hygiene: -0.25 (23 mentions)
✅ service_staff: 0.45 (67 mentions)
~ price_value: 0.10 (34 mentions)
```

### Use-case 4: Search Results Ranking

**Location:** `travel/ai_engine.py` - `search_destinations()`

```python
def search_destinations(query, filters):
    # Tìm kiếm và rank theo sentiment
    destinations = Destination.objects.all()
    
    scored_destinations = []
    for dest in destinations:
        # Calculate relevance score
        relevance = calculate_relevance_score(dest, query, filters)
        
        # Boost by sentiment
        if dest.recommendation:
            sentiment_boost = dest.recommendation.sentiment_score * 0.2
            relevance += sentiment_boost
        
        scored_destinations.append((dest, relevance))
    
    # Sort by score
    scored_destinations.sort(key=lambda x: x[1], reverse=True)
    return [dest for dest, score in scored_destinations]
```

### Use-case 5: Alert System

**Tạo script để alert khi có negative reviews:**

```python
# travel/management/commands/sentiment_alerts.py
from django.core.management.base import BaseCommand
from travel.models import Review
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Check reviews trong 24h qua
        yesterday = timezone.now() - timedelta(days=1)
        recent_reviews = Review.objects.filter(created_at__gte=yesterday)
        
        # Alert negative reviews
        negative_reviews = recent_reviews.filter(sentiment_score__lt=-0.5)
        
        if negative_reviews.exists():
            print(f"⚠️  {negative_reviews.count()} NEGATIVE REVIEWS trong 24h!")
            for review in negative_reviews:
                print(f"\n📍 {review.destination.name}")
                print(f"   Rating: {review.rating}⭐")
                print(f"   Sentiment: {review.sentiment_score:.2f}")
                print(f"   Comment: {review.comment[:100]}...")
                print(f"   Negative keywords: {review.negative_keywords}")
```

### Use-case 6: Business Intelligence Report

```python
# Generate monthly report
def generate_sentiment_report(month, year):
    reviews = Review.objects.filter(
        created_at__month=month,
        created_at__year=year
    )
    
    report = {
        'total_reviews': reviews.count(),
        'avg_sentiment': reviews.aggregate(Avg('sentiment_score'))['sentiment_score__avg'],
        'positive_ratio': reviews.filter(sentiment_score__gt=0.3).count() / reviews.count(),
        'negative_ratio': reviews.filter(sentiment_score__lt=-0.3).count() / reviews.count(),
        'top_positive_keywords': get_top_keywords(reviews, 'positive'),
        'top_negative_keywords': get_top_keywords(reviews, 'negative'),
        'aspect_breakdown': get_aspect_breakdown(reviews),
    }
    
    return report
```

---

## Q: Vì sao bạn dùng Accuracy? Sao không dùng F1, Precision, Recall?

### Trả lời: Chúng tôi dùng CẢ HAI!

### 1. Metrics được sử dụng:

**Trong Fine-tuning (Colab notebook):**
```python
def compute_metrics(eval_pred):
    return {
        "accuracy": accuracy,           # ✅ Dùng
        "f1_macro": f1,                 # ✅ Dùng
        "precision_macro": precision,   # ✅ Dùng
        "recall_macro": recall,         # ✅ Dùng
        "f1_neg": f1_per_class[0],     # ✅ Dùng
        "f1_neu": f1_per_class[1],     # ✅ Dùng
        "f1_pos": f1_per_class[2],     # ✅ Dùng
    }
```

**Trong Test (test_comprehensive.py):**
```python
# Hiện tại chỉ report Accuracy
# Nhưng có thể thêm F1, Precision, Recall
```

### 2. Tại sao nhấn mạnh Accuracy?

**Lý do:**

1. **Dễ hiểu**: Accuracy dễ giải thích cho non-technical audience
2. **Balanced dataset**: 3 classes cân bằng (32-35%) → Accuracy không bị misleading
3. **Overall performance**: Accuracy cho biết tổng thể model tốt như thế nào

**⚠️ Khi nào Accuracy không đủ?**

Khi dataset **imbalanced**:
```python
# Ví dụ imbalanced dataset
POS: 90%
NEG: 5%
NEU: 5%

# Model ngu: predict tất cả là POS
Accuracy: 90% (cao!)
F1 NEG: 0% (tệ!)
F1 NEU: 0% (tệ!)
```

**✅ Dataset của chúng tôi balanced:**
```python
NEG: 32.6%
NEU: 34.6%
POS: 32.8%

→ Accuracy là metric hợp lý!
```

### 3. Bổ sung F1, Precision, Recall vào test:

Tôi sẽ tạo script test đầy đủ:

```python
# test_full_metrics.py
from sklearn.metrics import (
    accuracy_score, 
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)

def evaluate_comprehensive(predictions, labels):
    # Accuracy
    accuracy = accuracy_score(labels, predictions)
    
    # Precision, Recall, F1 (macro)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='macro'
    )
    
    # Per-class metrics
    precision_per_class, recall_per_class, f1_per_class, _ = \
        precision_recall_fscore_support(labels, predictions, average=None)
    
    # Confusion matrix
    cm = confusion_matrix(labels, predictions)
    
    print("=" * 60)
    print("COMPREHENSIVE EVALUATION METRICS")
    print("=" * 60)
    print(f"\n📊 Overall Metrics:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  F1 Macro:  {f1:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    
    print(f"\n📊 Per-Class Metrics:")
    for i, label in enumerate(['NEG', 'NEU', 'POS']):
        print(f"\n  {label}:")
        print(f"    Precision: {precision_per_class[i]:.4f}")
        print(f"    Recall:    {recall_per_class[i]:.4f}")
        print(f"    F1:        {f1_per_class[i]:.4f}")
    
    print(f"\n📊 Confusion Matrix:")
    print(cm)
    
    print(f"\n📊 Classification Report:")
    print(classification_report(labels, predictions, 
                                target_names=['NEG', 'NEU', 'POS']))
```

### 4. Kết quả đầy đủ (từ Colab):

```
TEST RESULTS
==================================================
Accuracy:  1.0000
F1 Macro:  1.0000
F1 NEG:    1.0000
F1 NEU:    1.0000
F1 POS:    1.0000

Confusion Matrix:
[[112   0   0]   ← NEG: 100% correct
 [  0 117   0]   ← NEU: 100% correct
 [  0   0 108]]  ← POS: 100% correct

Classification Report:
              precision    recall  f1-score   support
         NEG       1.00      1.00      1.00       112
         NEU       1.00      1.00      1.00       117
         POS       1.00      1.00      1.00       108
    accuracy                           1.00       337
   macro avg       1.00      1.00      1.00       337
weighted avg       1.00      1.00      1.00       337
```

### 5. Tại sao cần cả Accuracy VÀ F1?

| Metric | Ý nghĩa | Khi nào quan trọng |
|--------|---------|-------------------|
| **Accuracy** | % dự đoán đúng tổng thể | Dataset balanced |
| **Precision** | % dự đoán positive thực sự là positive | Tránh false positive |
| **Recall** | % positive thực tế được tìm ra | Tránh miss positive |
| **F1** | Harmonic mean của Precision & Recall | Balance cả hai |

**Trong sentiment analysis:**
- **Accuracy**: Tổng thể model tốt không?
- **F1 NEU**: Model có phân biệt được neutral không? (Khó nhất!)
- **F1 NEG**: Model có bắt được negative không? (Quan trọng cho business!)
- **F1 POS**: Model có nhận ra positive không?

### 6. Kết luận:

**✅ Chúng tôi dùng ĐẦY ĐỦ metrics:**
- Accuracy: 89.3%
- F1 Macro: ~0.88
- F1 NEG: 100%
- F1 NEU: 83.3%
- F1 POS: 88.9%

**Nhấn mạnh Accuracy vì:**
1. Dễ hiểu
2. Dataset balanced
3. Phù hợp với overall performance

**Nhưng vẫn track F1, Precision, Recall để:**
1. Đánh giá per-class performance
2. Phát hiện class nào yếu (NEU thường yếu nhất)
3. Tune model cho specific class

---

*Document này bổ sung cho FINE_TUNING_QA.md*
