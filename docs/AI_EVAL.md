# AI Eval — WebDuLich (rule-based fallback, 2026-10-04)

Dataset: `finetune_phobert/finetune_data/test.csv` (337 mẫu, 3 nhãn NEG/NEU/POS).

## Phát hiện quan trọng: model fine-tuned KHÔNG TỒN TẠI trong repo

`travel/phobert-travel-sentiment-final/model.safetensors` (134 bytes) là **Git LFS pointer**,
không phải weights. Chưa `git lfs pull` bao giờ → mọi request luôn rơi vào:

1. Thử load LFS pointer → `Failed to load PhoBERT model: header too large` (log mỗi request), hoặc
2. Fallback HuggingFace `wonrax/phobert-base-vietnamese-sentiment` (tải ngoài, không kiểm soát), hoặc
3. Rule-based thuần (khi offline).

**Quyết định**: không tune `_combine_scores`/threshold khi PhoBERT thật chưa chạy — mọi số đo
dưới đây là của **rule-based fallback**.

## Accuracy rule-based: 0.718 (242/337)

| actual/pred | NEG | NEU | POS |
|---|---|---|---|
| NEG (99) | 97 | 2 | 0 |
| NEU (122) | 42 | 38 | 42 |
| POS (116) | 0 | 9 | 107 |

- NEG/POS gần như hoàn hảo (không lẫn chéo NEG↔POS lần nào).
- **NEU là lỗ hổng**: chỉ 31% đúng, lẫn đều sang 2 phía. Ngưỡng ±0.18 quá hẹp so với
  biên độ rule score; neutral-soft words (`tạm`, `ok`, `ổn`) cho 0.05 nhưng intensifier
  (`rất đẹp` → POS, `quá bẩn` → NEG) đẩy qua ngưỡng ngay.
- Rating calibration (`analyze_sentiment(text, rating)`): rating=5 boost score lên ≥0.6
  khi text neutral — **bóp méo sentiment thật** để chiều lòng rating. Đề xuất: bỏ calibration,
  hiển thị text-sentiment và star-rating là 2 tín hiệu riêng.

## Việc cần làm (theo thứ tự)

1. `git lfs pull` lấy weights thật (540MB) HOẶC quyết định bỏ PhoBERT, giữ rule-based
   (0.72 accuracy, 0 dependency, nhanh) — ghi quyết định vào đây.
2. Nếu giữ PhoBERT: eval lại ma trận này với model thật rồi mới tune `_combine_scores`.
3. Bỏ rating calibration trong `analyze_sentiment()` (giữ tham số để tương thích, bỏ effect).
4. Mở rộng ngưỡng NEU (±0.18 → ±0.30) CHỈ SAU khi có eval chứng minh.
5. `spam_detector.py` (454 dòng, không ai import): wire vào `api_submit_review` thay regex
   inline hiện tại, hoặc xoá. Không để dead module mang tiếng "enterprise filter".
6. Gộp 3 bản `update_destination_scores` (views.py + calculate_scores.py + script đã xoá)
   về 1 hàm trong `travel/services/scoring_service.py`.
