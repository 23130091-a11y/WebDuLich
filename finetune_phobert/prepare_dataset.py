"""
Chuẩn bị dataset để fine-tune PhoBERT cho Travel Sentiment Analysis

Dataset cần có:
- 3000-5000 reviews du lịch
- Labels: NEG (0), NEU (1), POS (2) hoặc 4-class với MIXED
- Đặc biệt cần nhiều cases:
  + "nhưng / tuy / mặc dù" (contrast)
  + "hơi / khá / cũng / tạm" (downtoner)
  + "không tệ / không dở" (negation of negative)
  + Chê nhẹ, khen nhẹ
"""

import os
import json
import random
import pandas as pd
from typing import List, Dict, Tuple

# Label mapping
LABEL_MAP = {
    'NEG': 0,      # Negative
    'NEU': 1,      # Neutral  
    'MIXED': 1,    # Mixed → treat as Neutral
    'POS': 2       # Positive
}

# ============================================================
# SYNTHETIC TRAINING DATA TEMPLATES
# Tạo dữ liệu training đa dạng cho các edge cases
# ============================================================

# POSITIVE templates
POSITIVE_TEMPLATES = [
    # Strong positive
    "Địa điểm {adj_pos}, {service_pos}, rất recommend!",
    "View {adj_pos}, phong cảnh {adj_pos}, đáng đi lắm!",
    "{service_pos}, {facility_pos}, sẽ quay lại!",
    "Tuyệt vời! {adj_pos}, {adj_pos}, 10 điểm!",
    "Cảnh {adj_pos}, chụp hình {adj_pos}, thích lắm!",
    
    # Medium positive
    "Địa điểm {adj_pos}, {service_pos}.",
    "View {adj_pos}, đáng để ghé thăm.",
    "{facility_pos}, {adj_pos}.",
    "Khá {adj_pos}, {service_pos}.",
    "Cũng {adj_pos}, recommend.",
]

# NEGATIVE templates
NEGATIVE_TEMPLATES = [
    # Strong negative
    "Dịch vụ {adj_neg}, {service_neg}, không bao giờ quay lại!",
    "Giá {price_neg}, {adj_neg}, thất vọng!",
    "{hygiene_neg}, {adj_neg}, không recommend!",
    "Quá {adj_neg}, {service_neg}, phí tiền!",
    "{crowd_neg}, {service_neg}, {adj_neg}!",
    
    # Medium negative
    "Hơi {adj_neg}, {service_neg}.",
    "Khá {adj_neg}, không đáng tiền.",
    "{adj_neg}, {crowd_neg}.",
    "Cũng {adj_neg}, không recommend.",
    "{service_neg}, {adj_neg}.",
]

# NEUTRAL/MIXED templates - QUAN TRỌNG NHẤT
NEUTRAL_TEMPLATES = [
    # Mixed with "nhưng"
    "Cảnh {adj_pos} nhưng {adj_neg}.",
    "View {adj_pos}, nhưng {service_neg}.",
    "{facility_pos} nhưng {price_neg}.",
    "{adj_pos} nhưng {crowd_neg}.",
    "{service_pos}, nhưng {adj_neg}.",
    
    # Mixed with "tuy/mặc dù"
    "Tuy {adj_neg} nhưng {adj_pos}.",
    "Mặc dù {price_neg}, nhưng {adj_pos}.",
    "Dù {crowd_neg}, cảnh vẫn {adj_pos}.",
    
    # Downtoner patterns
    "Cũng được, không có gì đặc biệt.",
    "Tạm ổn, bình thường.",
    "Khá ok, không quá {adj_pos}.",
    "Hơi {adj_neg}, còn lại ok.",
    "Tương đối {adj_pos}, tạm chấp nhận.",
    
    # Negation of negative (weak positive → treat as neutral)
    "Không {adj_neg} lắm, cũng được.",
    "Không quá {adj_neg}, tạm ổn.",
    "Cũng không {adj_neg}, ok.",
    
    # Soft criticism
    "Giá hơi {price_neg}, còn lại ok.",
    "Hơi {crowd_neg}, nhưng chấp nhận được.",
    "{adj_pos}, chỉ hơi {adj_neg} thôi.",
]

# Word banks
WORD_BANKS = {
    'adj_pos': ['đẹp', 'tuyệt vời', 'xuất sắc', 'tốt', 'ổn', 'ok', 'xịn', 'đỉnh', 
                'thích', 'hay', 'ấn tượng', 'mê', 'thơ mộng', 'lãng mạn'],
    'adj_neg': ['tệ', 'dở', 'kém', 'xấu', 'chán', 'thất vọng', 'tồi', 'bẩn'],
    'service_pos': ['nhân viên thân thiện', 'phục vụ tốt', 'hỗ trợ nhiệt tình', 
                    'dịch vụ chuyên nghiệp', 'nhân viên vui vẻ'],
    'service_neg': ['nhân viên thái độ kém', 'phục vụ chậm', 'không nhiệt tình',
                    'dịch vụ tệ', 'nhân viên cộc lốc'],
    'facility_pos': ['phòng sạch sẽ', 'tiện nghi đầy đủ', 'wifi mạnh', 
                     'phòng rộng rãi', 'decor đẹp'],
    'facility_neg': ['phòng bẩn', 'cơ sở vật chất cũ', 'wifi yếu', 
                     'phòng nhỏ', 'xuống cấp'],
    'price_neg': ['đắt', 'mắc', 'cao', 'chát', 'không đáng tiền'],
    'hygiene_neg': ['bẩn quá', 'wc hôi', 'rác nhiều', 'mùi khó chịu'],
    'crowd_neg': ['đông quá', 'chen chúc', 'chờ lâu', 'ồn ào', 'xếp hàng dài'],
}


def fill_template(template: str) -> str:
    """Fill template với random words từ word banks"""
    result = template
    for key, words in WORD_BANKS.items():
        placeholder = '{' + key + '}'
        while placeholder in result:
            result = result.replace(placeholder, random.choice(words), 1)
    return result


def generate_synthetic_data(num_samples: int = 3000) -> List[Dict]:
    """
    Generate synthetic training data với distribution:
    - 35% Positive
    - 35% Negative  
    - 30% Neutral/Mixed (quan trọng!)
    """
    data = []
    
    # Positive samples (35%)
    num_pos = int(num_samples * 0.35)
    for _ in range(num_pos):
        template = random.choice(POSITIVE_TEMPLATES)
        text = fill_template(template)
        data.append({'text': text, 'label': 'POS'})
    
    # Negative samples (35%)
    num_neg = int(num_samples * 0.35)
    for _ in range(num_neg):
        template = random.choice(NEGATIVE_TEMPLATES)
        text = fill_template(template)
        data.append({'text': text, 'label': 'NEG'})
    
    # Neutral/Mixed samples (30%) - QUAN TRỌNG
    num_neu = num_samples - num_pos - num_neg
    for _ in range(num_neu):
        template = random.choice(NEUTRAL_TEMPLATES)
        text = fill_template(template)
        data.append({'text': text, 'label': 'NEU'})
    
    random.shuffle(data)
    return data


# ============================================================
# SPECIAL EDGE CASES - Thêm các cases đặc biệt
# ============================================================

EDGE_CASES = [
    # Negation of negative → Weak positive/Neutral
    {"text": "Không tệ", "label": "NEU"},
    {"text": "Không dở lắm", "label": "NEU"},
    {"text": "Cũng không tệ", "label": "NEU"},
    {"text": "Không quá tệ", "label": "NEU"},
    {"text": "Không hề tệ", "label": "POS"},
    
    # Negation of positive → Negative
    {"text": "Không đẹp", "label": "NEG"},
    {"text": "Không tốt lắm", "label": "NEG"},
    {"text": "Không hay", "label": "NEG"},
    {"text": "Không ổn", "label": "NEG"},
    
    # Contrast patterns
    {"text": "Đẹp nhưng đắt", "label": "NEU"},
    {"text": "Rẻ nhưng dở", "label": "NEU"},
    {"text": "View đẹp nhưng xa", "label": "NEU"},
    {"text": "Phòng sạch nhưng nhỏ", "label": "NEU"},
    {"text": "Nhân viên thân thiện nhưng phục vụ chậm", "label": "NEU"},
    
    # Downtoner patterns
    {"text": "Hơi đắt", "label": "NEU"},
    {"text": "Khá ổn", "label": "NEU"},
    {"text": "Tương đối tốt", "label": "NEU"},
    {"text": "Cũng được", "label": "NEU"},
    {"text": "Tạm ổn", "label": "NEU"},
    {"text": "Ok thôi", "label": "NEU"},
    {"text": "Bình thường", "label": "NEU"},
    
    # Soft criticism
    {"text": "Giá hơi cao", "label": "NEU"},
    {"text": "Hơi đông", "label": "NEU"},
    {"text": "Khá xa", "label": "NEU"},
    {"text": "Cơ sở vật chất hơi cũ", "label": "NEU"},
    
    # Soft praise
    {"text": "Cũng đẹp", "label": "NEU"},
    {"text": "Khá ok", "label": "NEU"},
    {"text": "Tạm được", "label": "NEU"},
    
    # Complex mixed
    {"text": "Cảnh đẹp, giá hợp lý, nhưng đông quá", "label": "NEU"},
    {"text": "Phòng sạch, view đẹp, chỉ hơi xa trung tâm", "label": "POS"},
    {"text": "Dịch vụ tệ, nhưng cảnh đẹp bù lại", "label": "NEU"},
    {"text": "Giá đắt nhưng đáng tiền", "label": "POS"},
    {"text": "Hơi đắt nhưng đáng tiền", "label": "POS"},
    
    # Teencode
    {"text": "Dep lam, rat thich", "label": "POS"},
    {"text": "Te qua, ko bao gio quay lai", "label": "NEG"},
    {"text": "Cung dc, binh thuong", "label": "NEU"},
    {"text": "Xin xo, dinh cao", "label": "POS"},
]


def create_training_dataset(output_dir: str = "data", num_samples: int = 3000):
    """
    Tạo dataset hoàn chỉnh cho fine-tuning
    
    Output:
    - train.csv (80%)
    - val.csv (10%)
    - test.csv (10%)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate synthetic data
    print(f"Generating {num_samples} synthetic samples...")
    data = generate_synthetic_data(num_samples)
    
    # Add edge cases (multiply to increase weight)
    print(f"Adding {len(EDGE_CASES) * 10} edge cases...")
    for _ in range(10):  # Repeat edge cases 10 times
        data.extend(EDGE_CASES.copy())
    
    random.shuffle(data)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    df['label_id'] = df['label'].map(LABEL_MAP)
    
    # Split data
    total = len(df)
    train_end = int(total * 0.8)
    val_end = int(total * 0.9)
    
    train_df = df[:train_end]
    val_df = df[train_end:val_end]
    test_df = df[val_end:]
    
    # Save
    train_df.to_csv(f"{output_dir}/train.csv", index=False)
    val_df.to_csv(f"{output_dir}/val.csv", index=False)
    test_df.to_csv(f"{output_dir}/test.csv", index=False)
    
    # Print statistics
    print(f"\n=== Dataset Statistics ===")
    print(f"Total samples: {total}")
    print(f"Train: {len(train_df)} ({len(train_df)/total*100:.1f}%)")
    print(f"Val: {len(val_df)} ({len(val_df)/total*100:.1f}%)")
    print(f"Test: {len(test_df)} ({len(test_df)/total*100:.1f}%)")
    
    print(f"\n=== Label Distribution (Train) ===")
    for label in ['NEG', 'NEU', 'POS']:
        count = len(train_df[train_df['label'] == label])
        print(f"{label}: {count} ({count/len(train_df)*100:.1f}%)")
    
    print(f"\nDataset saved to {output_dir}/")
    return train_df, val_df, test_df


if __name__ == "__main__":
    create_training_dataset(output_dir="finetune_data", num_samples=3000)
