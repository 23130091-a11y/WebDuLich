"""
Script để detect và clean noisy labels trong real reviews

Phương pháp:
1. Detect conflicts giữa rating và sentiment
2. Manual review hoặc auto-correct
3. Export cleaned dataset
"""

import os
import sys
import django
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from travel.ai_engine import analyze_sentiment


def detect_noisy_labels(input_file='finetune_data/real_reviews.csv'):
    """
    Detect potential noisy labels
    
    Conflicts:
    1. Rating 4-5 + Negative sentiment → Noisy
    2. Rating 1-2 + Positive sentiment → Noisy
    3. Rating 3 + Extreme sentiment → Ambiguous
    """
    df = pd.read_csv(input_file)
    
    noisy_cases = []
    clean_cases = []
    ambiguous_cases = []
    
    for idx, row in df.iterrows():
        rating = row['rating']
        sentiment_score = row['sentiment_score']
        label = row['label']
        text = row['text']
        
        # Analyze with current model
        score, pos_kw, neg_kw, meta = analyze_sentiment(text)
        
        # Detect conflicts
        conflict = False
        reason = ""
        
        # Type 1: High rating + Negative sentiment
        if rating >= 4 and sentiment_score < -0.3:
            conflict = True
            reason = "High rating but negative sentiment"
        
        # Type 2: Low rating + Positive sentiment
        elif rating <= 2 and sentiment_score > 0.3:
            conflict = True
            reason = "Low rating but positive sentiment"
        
        # Type 3: Rating 3 with extreme sentiment
        elif rating == 3 and abs(sentiment_score) > 0.5:
            conflict = True
            reason = "Rating 3 but extreme sentiment"
        
        # Type 4: Mixed keywords but extreme label
        elif len(pos_kw) > 0 and len(neg_kw) > 0 and label != "NEU":
            conflict = True
            reason = "Mixed keywords but extreme label"
        
        if conflict:
            noisy_cases.append({
                'id': row.get('id', idx),
                'text': text,
                'rating': rating,
                'old_label': label,
                'sentiment_score': sentiment_score,
                'new_score': score,
                'pos_keywords': pos_kw,
                'neg_keywords': neg_kw,
                'reason': reason,
                'suggested_label': 'POS' if score > 0.15 else 'NEG' if score < -0.15 else 'NEU'
            })
        elif rating == 3:
            ambiguous_cases.append({
                'id': row.get('id', idx),
                'text': text,
                'rating': rating,
                'label': label,
                'sentiment_score': sentiment_score,
                'new_score': score,
            })
        else:
            clean_cases.append(row.to_dict())
    
    return noisy_cases, clean_cases, ambiguous_cases


def print_noisy_report(noisy_cases, clean_cases, ambiguous_cases):
    """Print report về noisy labels"""
    total = len(noisy_cases) + len(clean_cases) + len(ambiguous_cases)
    
    print("=" * 80)
    print("NOISY LABELS DETECTION REPORT")
    print("=" * 80)
    
    print(f"\n📊 Summary:")
    print(f"  Total reviews: {total}")
    print(f"  ✅ Clean: {len(clean_cases)} ({len(clean_cases)/total*100:.1f}%)")
    print(f"  ⚠️  Ambiguous (rating 3): {len(ambiguous_cases)} ({len(ambiguous_cases)/total*100:.1f}%)")
    print(f"  ❌ Noisy: {len(noisy_cases)} ({len(noisy_cases)/total*100:.1f}%)")
    
    if noisy_cases:
        print(f"\n❌ Noisy Cases (need correction):")
        print("-" * 80)
        for i, case in enumerate(noisy_cases[:10], 1):  # Show first 10
            print(f"\n{i}. ID: {case['id']}")
            print(f"   Text: {case['text'][:80]}...")
            print(f"   Rating: {case['rating']}⭐")
            print(f"   Old label: {case['old_label']}")
            print(f"   Suggested: {case['suggested_label']}")
            print(f"   Reason: {case['reason']}")
            print(f"   Keywords: pos={case['pos_keywords']}, neg={case['neg_keywords']}")
        
        if len(noisy_cases) > 10:
            print(f"\n   ... and {len(noisy_cases) - 10} more")
    
    if ambiguous_cases:
        print(f"\n⚠️  Ambiguous Cases (rating 3):")
        print(f"  Total: {len(ambiguous_cases)} cases")
        print(f"  Recommendation: Manual review or use model prediction")


def auto_correct_labels(noisy_cases, clean_cases, ambiguous_cases, 
                       output_file='finetune_data/real_reviews_cleaned.csv'):
    """
    Auto-correct noisy labels
    
    Strategy:
    1. Noisy cases → Use model prediction
    2. Ambiguous cases → Use model prediction
    3. Clean cases → Keep original
    """
    corrected_data = []
    
    # Clean cases - keep original
    for case in clean_cases:
        corrected_data.append(case)
    
    # Noisy cases - use suggested label
    for case in noisy_cases:
        corrected_data.append({
            'id': case['id'],
            'text': case['text'],
            'rating': case['rating'],
            'sentiment_score': case['new_score'],
            'label': case['suggested_label'],  # ← Corrected
            'label_id': {'NEG': 0, 'NEU': 1, 'POS': 2}[case['suggested_label']],
            'corrected': True,
            'old_label': case['old_label']
        })
    
    # Ambiguous cases - use model prediction
    for case in ambiguous_cases:
        suggested = 'POS' if case['new_score'] > 0.15 else 'NEG' if case['new_score'] < -0.15 else 'NEU'
        corrected_data.append({
            'id': case['id'],
            'text': case['text'],
            'rating': case['rating'],
            'sentiment_score': case['new_score'],
            'label': suggested,  # ← Corrected
            'label_id': {'NEG': 0, 'NEU': 1, 'POS': 2}[suggested],
            'corrected': True,
            'old_label': case['label']
        })
    
    # Save
    df = pd.DataFrame(corrected_data)
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Cleaned data saved to: {output_file}")
    print(f"   Total: {len(df)} reviews")
    print(f"   Corrected: {df['corrected'].sum() if 'corrected' in df.columns else 0}")
    
    return df


def manual_review_interface(noisy_cases):
    """
    Interactive interface để manual review noisy cases
    """
    print("\n" + "=" * 80)
    print("MANUAL REVIEW INTERFACE")
    print("=" * 80)
    print("Commands: [P]ositive, [N]egative, [U]neutral, [S]kip, [Q]uit")
    
    corrected = []
    
    for i, case in enumerate(noisy_cases, 1):
        print(f"\n[{i}/{len(noisy_cases)}]")
        print(f"Text: {case['text']}")
        print(f"Rating: {case['rating']}⭐")
        print(f"Old label: {case['old_label']}")
        print(f"Suggested: {case['suggested_label']}")
        print(f"Reason: {case['reason']}")
        
        while True:
            choice = input("\nYour label [P/N/U/S/Q]: ").strip().upper()
            
            if choice == 'Q':
                print("Quitting...")
                return corrected
            elif choice == 'S':
                break
            elif choice in ['P', 'N', 'U']:
                label_map = {'P': 'POS', 'N': 'NEG', 'U': 'NEU'}
                case['corrected_label'] = label_map[choice]
                corrected.append(case)
                print(f"✅ Labeled as {label_map[choice]}")
                break
            else:
                print("Invalid choice. Try again.")
    
    return corrected


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['detect', 'auto', 'manual'], default='detect',
                       help='Mode: detect, auto-correct, or manual review')
    parser.add_argument('--input', default='finetune_data/real_reviews.csv',
                       help='Input file')
    parser.add_argument('--output', default='finetune_data/real_reviews_cleaned.csv',
                       help='Output file')
    args = parser.parse_args()
    
    # Detect noisy labels
    print("🔍 Detecting noisy labels...")
    noisy_cases, clean_cases, ambiguous_cases = detect_noisy_labels(args.input)
    
    # Print report
    print_noisy_report(noisy_cases, clean_cases, ambiguous_cases)
    
    if args.mode == 'auto':
        # Auto-correct
        print("\n🤖 Auto-correcting labels...")
        auto_correct_labels(noisy_cases, clean_cases, ambiguous_cases, args.output)
    
    elif args.mode == 'manual':
        # Manual review
        corrected = manual_review_interface(noisy_cases)
        
        if corrected:
            # Save manually corrected
            for case in corrected:
                # Update in clean_cases
                clean_cases.append({
                    'id': case['id'],
                    'text': case['text'],
                    'rating': case['rating'],
                    'label': case['corrected_label'],
                    'label_id': {'NEG': 0, 'NEU': 1, 'POS': 2}[case['corrected_label']],
                })
            
            df = pd.DataFrame(clean_cases)
            df.to_csv(args.output, index=False)
            print(f"\n✅ Manually corrected data saved to: {args.output}")


if __name__ == "__main__":
    main()
