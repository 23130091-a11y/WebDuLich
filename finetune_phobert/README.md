# Fine-tune PhoBERT cho Travel Sentiment Analysis

## Tổng quan

Thư mục này chứa các scripts để fine-tune PhoBERT model trên dữ liệu travel reviews tiếng Việt.

## Tại sao cần Fine-tune?

PhoBERT gốc (`wonrax/phobert-base-vietnamese-sentiment`) được train trên general Vietnamese text, không phải travel domain. Điều này dẫn đến:

- ❌ Không hiểu các từ chuyên ngành du lịch
- ❌ Xử lý kém các câu mixed sentiment ("đẹp nhưng đắt")
- ❌ Không nhận diện tốt neutral soft words ("tạm ổn", "cũng được")
- ❌ Sai với negation patterns ("không tệ")

## Cấu trúc thư mục

```
finetune_phobert/
├── README.md                      # File này
├── prepare_dataset.py             # Tạo training dataset
├── finetune_phobert.py           # Script fine-tuning chính
├── integrate_finetuned_model.py  # Tích hợp model vào project
└── finetune_data/                # Dataset (sau khi chạy prepare_dataset.py)
    ├── train.csv
    ├── val.csv
    └── test.csv
```

## Hướng dẫn sử dụng

### Bước 1: Chuẩn bị dataset

```bash
cd finetune_phobert
python prepare_dataset.py
```

Kết quả:
- `finetune_data/train.csv` (80% - ~2400 samples)
- `finetune_data/val.csv` (10% - ~300 samples)
- `finetune_data/test.csv` (10% - ~300 samples)

### Bước 2: Fine-tune model

```bash
python finetune_phobert.py
```

Thời gian: ~30-60 phút (GPU) hoặc 2-4 giờ (CPU)

Kết quả:
- Model được lưu tại `./phobert-travel-sentiment/`

### Bước 3: Tích hợp vào project

```bash
python integrate_finetuned_model.py --copy
```

Sau đó update `ai_engine.py` theo hướng dẫn.

## Dataset Design

### Label Distribution
- **35% Positive**: Câu khen rõ ràng
- **35% Negative**: Câu chê rõ ràng
- **30% Neutral/Mixed**: Câu trung lập hoặc mixed (QUAN TRỌNG!)

### Edge Cases (được nhấn mạnh)

1. **Contrast patterns** ("nhưng", "tuy", "mặc dù"):
   - "Cảnh đẹp nhưng đông quá" → NEU
   - "View đẹp, nhưng xa trung tâm" → NEU

2. **Downtoner patterns** ("hơi", "khá", "cũng", "tạm"):
   - "Hơi đắt" → NEU
   - "Khá ổn" → NEU
   - "Tạm được" → NEU

3. **Negation of negative** ("không tệ"):
   - "Không tệ" → NEU (weak positive)
   - "Không dở lắm" → NEU

4. **Soft criticism/praise**:
   - "Giá hơi cao" → NEU
   - "Cũng đẹp" → NEU

## Expected Results

### Trước Fine-tune (PhoBERT gốc)
| Metric | Value |
|--------|-------|
| Overall Accuracy | 82.1% |
| F1 NEU | ~60% |
| Mixed sentiment | Sai nhiều |

### Sau Fine-tune (Expected)
| Metric | Value |
|--------|-------|
| Overall Accuracy | 90-95% |
| F1 NEU | 85-90% |
| Mixed sentiment | Xử lý tốt |

## Hyperparameters

```python
FinetuneConfig(
    model_name="wonrax/phobert-base-vietnamese-sentiment",
    num_train_epochs=5,
    per_device_train_batch_size=16,
    learning_rate=2e-5,
    weight_decay=0.01,
    warmup_ratio=0.1,
    max_length=256,
)
```

## Mở rộng Dataset

Để có kết quả tốt hơn, bạn có thể:

1. **Thu thập real reviews** từ:
   - Google Maps reviews
   - TripAdvisor
   - Booking.com
   - Traveloka

2. **Label thủ công** với guidelines:
   - POS: Khen rõ ràng, recommend
   - NEG: Chê rõ ràng, không recommend
   - NEU: Mixed, trung lập, không rõ ràng

3. **Tăng số lượng** lên 5000-10000 samples

## Domain-Adaptive Pretraining (Advanced)

Nếu muốn kết quả tốt nhất:

1. Thu thập 50k-500k travel reviews (không cần label)
2. Tiếp tục pretrain PhoBERT với Masked LM trên corpus này
3. Sau đó fine-tune sentiment

```python
# Pseudo-code
from transformers import AutoModelForMaskedLM

model = AutoModelForMaskedLM.from_pretrained("vinai/phobert-base")
# Continue pretraining on travel corpus
# Then fine-tune for sentiment
```

## Troubleshooting

### Out of Memory
- Giảm `per_device_train_batch_size` xuống 8 hoặc 4
- Sử dụng `fp16=True` nếu có GPU

### Overfitting
- Tăng `weight_decay`
- Giảm `num_train_epochs`
- Thêm data augmentation

### Low F1 NEU
- Tăng số lượng neutral samples trong dataset
- Thêm nhiều edge cases hơn
- Kiểm tra label quality

## References

- [PhoBERT Paper](https://arxiv.org/abs/2003.00744)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [Fine-tuning BERT for Sentiment Analysis](https://huggingface.co/blog/sentiment-analysis-python)
