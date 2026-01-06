# KẾT QUẢ ĐÁNH GIÁ PRODUCTION - SENTIMENT ANALYSIS

**Ngày:** 04/01/2026  
**Phiên bản:** 2.1 (Enhanced Mixed Sentiment Handling)

---

## 📊 OVERALL METRICS

| Metric | Giá trị |
|--------|---------|
| **Sentiment Accuracy** | 74.1% |
| **Rating MAE** | 0.84 |
| **Total Reviews** | 594 |
| **Mismatch Cases** | 1 |

---

## 📈 RATING DISTRIBUTION

| Rating | Count | % | Avg AI Score | Std |
|--------|-------|---|--------------|-----|
| 1 | 4 | 0.7% | -0.39 | 0.37 |
| 2 | 6 | 1.0% | -0.20 | 0.34 |
| 3 | 35 | 5.9% | +0.14 | 0.23 |
| 4 | 437 | 73.6% | +0.47 | 0.40 |
| 5 | 112 | 18.9% | +0.81 | 0.26 |

**Nhận xét:**
- Rating 3 có avg score +0.14 (trong vùng neutral -0.2 đến +0.35) ✓
- Rating 4-5 có avg score positive (0.47-0.81) ✓
- Rating 1-2 có avg score negative (-0.39 đến -0.20) ✓

---

## 🔀 CONFUSION MATRIX

```
            |   NEG    |   NEU    |   POS    | Total
   ---------+----------+----------+----------+------
   NEG      |    5     |    4     |    1     | 10
   NEU      |    1     |    17    |    17    | 35
   POS      |    1     |   130    |   418    | 549
```

---

## 📋 PER-CATEGORY ACCURACY

| Category | Accuracy | Correct/Total |
|----------|----------|---------------|
| **Positive** (rating 4-5) | 76.1% | 418/549 |
| **Neutral** (rating 3) | 48.6% | 17/35 |
| **Negative** (rating 1-2) | 50.0% | 5/10 |

**Nhận xét:**
- POS accuracy cao (76.1%) - hệ thống nhận diện tốt reviews tích cực
- NEU accuracy thấp (48.6%) - rating 3 có thể là positive hoặc negative tùy context
- NEG sample size nhỏ (10 reviews) nên accuracy không đại diện

---

## ⚠️ MISMATCH CASES

Chỉ còn **1 mismatch case** (giảm từ 20 xuống 1):

| ID | Rating | AI Score | Comment | Reason |
|----|--------|----------|---------|--------|
| 588 | 4 | -0.64 | "quang cảnh không đẹp cho lắm" | "không đẹp" detected as negative |

**Phân tích:** Đây là trường hợp đặc biệt - người dùng rating 4 nhưng comment có "không đẹp". Có thể là:
- User đánh giá tổng thể tốt nhưng comment về 1 khía cạnh
- Hoặc user nhầm rating

---

## 🔧 CẢI TIẾN ĐÃ THỰC HIỆN

### 1. Mixed Sentiment Handling
- Khi có cả positive và negative keywords → giảm magnitude 40-70%
- Kéo score về neutral hơn

### 2. Contrast Words Processing
- "nhưng", "tuy nhiên" → phần sau được weight cao hơn
- Giảm 20% positive impact khi có contrast

### 3. Negative Behavior Patterns
- "không quay lại", "không recommend" → strong negative (-0.5)
- Detect patterns trong window 30 chars

### 4. Neutral Soft Words Tuning
- "ok", "được", "tạm", "ổn" → very weak positive (0.05)
- Không làm câu mixed thành positive

### 5. No Keywords Dampening
- Khi không có keywords → giảm PhoBERT score 70%
- Giữ score gần neutral

### 6. Negation Tuning
- "không tệ" → weak positive (capped at 0.20)
- Giảm từ 0.35 xuống 0.20

---

## 📝 SO SÁNH TRƯỚC VÀ SAU

| Metric | Trước | Sau | Thay đổi |
|--------|-------|-----|----------|
| Accuracy | 73.6% | 74.1% | +0.5% |
| MAE | 0.87 | 0.84 | -0.03 ✓ |
| Rating 3 Avg Score | +0.29 | +0.14 | -0.15 ✓ |
| Mismatch Cases | 20 | 1 | -19 ✓ |

---

## 💡 RECOMMENDATIONS

1. **NEU accuracy thấp** - Cần thêm context-aware analysis cho rating 3
2. **NEG sample size nhỏ** - Thu thập thêm negative reviews để balance dataset
3. **Fine-tune PhoBERT** - Train trên travel domain để cải thiện accuracy

---

## ✅ KẾT LUẬN

Hệ thống đạt **74.1% accuracy** với **MAE 0.84** trên 594 reviews. Đặc biệt:
- **Mismatch cases giảm 95%** (từ 20 xuống 1)
- **Rating 3 avg score** nằm trong vùng neutral (+0.14)
- **Rating distribution** hợp lý theo expected sentiment

Hệ thống sẵn sàng cho production với các cải tiến mixed sentiment handling.
