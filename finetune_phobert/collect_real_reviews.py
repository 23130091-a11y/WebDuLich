"""
Thu thập real reviews từ database để bổ sung vào training data

Script này:
1. Lấy reviews từ database
2. Sử dụng rating để tạo pseudo-labels
3. Export ra CSV để review và điều chỉnh labels
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

import pandas as pd
from travel.models import Review


def rating_to_label(rating: int, sentiment_score: float = None) -> str:
    """
    Convert rating và sentiment_score thành label
    
    Logic:
    - Rating 1-2: NEG
    - Rating 3: NEU (hoặc dựa vào sentiment_score)
    - Rating 4-5: POS (nhưng check sentiment_score)
    """
    if rating <= 2:
        return "NEG"
    elif rating == 3:
        return "NEU"
    else:  # rating 4-5
        # Nếu có sentiment_score và nó negative → có thể là mixed
        if sentiment_score is not None and sentiment_score < -0.2:
            return "NEU"  # Mixed sentiment
        return "POS"


def collect_reviews_from_db(output_file: str = "finetune_data/real_reviews.csv"):
    """Thu thập reviews từ database"""
    
    reviews = Review.objects.all().values(
        'id', 'comment', 'rating', 'sentiment_score', 
        'positive_keywords', 'negative_keywords'
    )
    
    data = []
    for review in reviews:
        comment = review['comment']
        if not comment or len(comment.strip()) < 10:
            continue
        
        # Tạo pseudo-label từ rating
        label = rating_to_label(review['rating'], review['sentiment_score'])
        
        # Check nếu có cả positive và negative keywords → likely mixed
        pos_kw = review['positive_keywords'] or []
        neg_kw = review['negative_keywords'] or []
        
        if len(pos_kw) > 0 and len(neg_kw) > 0:
            label = "NEU"  # Mixed sentiment
        
        data.append({
            'id': review['id'],
            'text': comment,
            'rating': review['rating'],
            'sentiment_score': review['sentiment_score'],
            'pseudo_label': label,
            'label': label,  # Có thể điều chỉnh thủ công
            'pos_keywords': str(pos_kw),
            'neg_keywords': str(neg_kw),
            'needs_review': 'YES' if review['rating'] == 3 else 'NO'
        })
    
    df = pd.DataFrame(data)
    
    # Save
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"=== Collected {len(df)} reviews ===")
    print(f"\nLabel Distribution:")
    for label in ['NEG', 'NEU', 'POS']:
        count = len(df[df['label'] == label])
        print(f"  {label}: {count} ({count/len(df)*100:.1f}%)")
    
    print(f"\nNeeds Review: {len(df[df['needs_review'] == 'YES'])} reviews")
    print(f"\nSaved to: {output_file}")
    print("\n⚠️  Hãy review và điều chỉnh labels trong file CSV trước khi sử dụng!")
    
    return df


def merge_with_synthetic(
    real_file: str = "finetune_data/real_reviews.csv",
    synthetic_dir: str = "finetune_data",
    output_dir: str = "finetune_data_merged"
):
    """Merge real reviews với synthetic data"""
    
    # Load real reviews
    real_df = pd.read_csv(real_file)
    real_df = real_df[['text', 'label']].copy()
    
    # Load synthetic data
    train_df = pd.read_csv(f"{synthetic_dir}/train.csv")
    val_df = pd.read_csv(f"{synthetic_dir}/val.csv")
    test_df = pd.read_csv(f"{synthetic_dir}/test.csv")
    
    # Add label_id to real data
    label_map = {'NEG': 0, 'NEU': 1, 'POS': 2}
    real_df['label_id'] = real_df['label'].map(label_map)
    
    # Split real data
    real_train = real_df.sample(frac=0.8, random_state=42)
    real_remaining = real_df.drop(real_train.index)
    real_val = real_remaining.sample(frac=0.5, random_state=42)
    real_test = real_remaining.drop(real_val.index)
    
    # Merge
    merged_train = pd.concat([train_df, real_train], ignore_index=True)
    merged_val = pd.concat([val_df, real_val], ignore_index=True)
    merged_test = pd.concat([test_df, real_test], ignore_index=True)
    
    # Shuffle
    merged_train = merged_train.sample(frac=1, random_state=42).reset_index(drop=True)
    merged_val = merged_val.sample(frac=1, random_state=42).reset_index(drop=True)
    merged_test = merged_test.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Save
    os.makedirs(output_dir, exist_ok=True)
    merged_train.to_csv(f"{output_dir}/train.csv", index=False)
    merged_val.to_csv(f"{output_dir}/val.csv", index=False)
    merged_test.to_csv(f"{output_dir}/test.csv", index=False)
    
    print(f"\n=== Merged Dataset ===")
    print(f"Train: {len(merged_train)} (synthetic: {len(train_df)}, real: {len(real_train)})")
    print(f"Val: {len(merged_val)} (synthetic: {len(val_df)}, real: {len(real_val)})")
    print(f"Test: {len(merged_test)} (synthetic: {len(test_df)}, real: {len(real_test)})")
    print(f"\nSaved to: {output_dir}/")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", action="store_true", help="Collect reviews from DB")
    parser.add_argument("--merge", action="store_true", help="Merge with synthetic data")
    args = parser.parse_args()
    
    if args.collect:
        collect_reviews_from_db()
    elif args.merge:
        merge_with_synthetic()
    else:
        print("Usage:")
        print("  python collect_real_reviews.py --collect  # Thu thập từ DB")
        print("  python collect_real_reviews.py --merge    # Merge với synthetic")
