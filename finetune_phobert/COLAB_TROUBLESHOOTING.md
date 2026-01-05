# Google Colab Troubleshooting Guide

## Lỗi: `evaluation_strategy` not found

### Nguyên nhân:
Phiên bản `transformers` cũ (< 4.30.0) sử dụng tên tham số khác.

### Giải pháp:

#### Option 1: Upgrade transformers (Khuyến nghị)
```python
# Chạy cell này TRƯỚC khi chạy các cell khác
!pip install --upgrade transformers>=4.30.0
```

Sau đó **Runtime > Restart runtime** và chạy lại từ đầu.

#### Option 2: Sửa code tương thích
Thay đổi trong cell "5️⃣ Fine-tune Model":

**Từ:**
```python
training_args = TrainingArguments(
    ...
    evaluation_strategy="epoch",  # ❌ Lỗi với version cũ
    ...
)
```

**Thành:**
```python
training_args = TrainingArguments(
    ...
    eval_strategy="epoch",  # ✅ Tương thích cả cũ và mới
    ...
)
```

---

## Lỗi: Out of Memory (OOM)

### Giải pháp:
Giảm batch size trong cell "5️⃣ Fine-tune Model":

```python
training_args = TrainingArguments(
    ...
    per_device_train_batch_size=8,  # Giảm từ 16 xuống 8
    per_device_eval_batch_size=16,  # Giảm từ 32 xuống 16
    ...
)
```

---

## Lỗi: GPU not available

### Kiểm tra:
```python
import torch
print(torch.cuda.is_available())  # Phải là True
```

### Giải pháp:
1. **Runtime > Change runtime type**
2. Chọn **Hardware accelerator: GPU**
3. Chọn **GPU type: T4** (miễn phí)
4. Click **Save**
5. Chạy lại notebook

---

## Lỗi: Session timeout

### Nguyên nhân:
Colab free có giới hạn thời gian session (~12 giờ).

### Giải pháp:
1. Chạy notebook trong 1 lần (5-10 phút)
2. Download model ngay sau khi train xong
3. Nếu bị timeout, chạy lại từ đầu

---

## Lỗi: Cannot download model

### Giải pháp:
```python
# Thay vì dùng files.download(), dùng Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Copy model to Drive
!cp -r ./phobert-travel-sentiment-final /content/drive/MyDrive/

print("✅ Model saved to Google Drive!")
```

---

## Tips để chạy nhanh hơn

### 1. Giảm số lượng data (test nhanh)
```python
# Trong cell "2️⃣ Tạo Training Dataset"
data = generate_dataset(1000)  # Giảm từ 3000 xuống 1000
```

### 2. Giảm số epochs
```python
# Trong cell "5️⃣ Fine-tune Model"
training_args = TrainingArguments(
    ...
    num_train_epochs=2,  # Giảm từ 3 xuống 2
    ...
)
```

### 3. Tăng batch size (nếu có GPU mạnh)
```python
training_args = TrainingArguments(
    ...
    per_device_train_batch_size=32,  # Tăng từ 16 lên 32
    ...
)
```

---

## Checklist trước khi chạy

- [ ] Đã bật GPU (Runtime > Change runtime type > GPU)
- [ ] Đã upgrade transformers (`!pip install --upgrade transformers>=4.30.0`)
- [ ] Đã restart runtime sau khi upgrade
- [ ] Có kết nối internet ổn định
- [ ] Đã đọc hết notebook trước khi chạy

---

## Liên hệ hỗ trợ

Nếu gặp lỗi khác, hãy:
1. Copy error message đầy đủ
2. Check phiên bản: `!pip list | grep transformers`
3. Check GPU: `!nvidia-smi`
