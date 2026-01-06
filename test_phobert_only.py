#!/usr/bin/env python
"""Test PhoBERT model directly to see its raw predictions"""
import os
import sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

import django
django.setup()

from travel.ai_engine import get_sentiment_analyzer

def test_phobert_raw():
    """Test PhoBERT model directly without rule-based combination"""
    
    analyzer = get_sentiment_analyzer()
    analyzer.load_model()  # Ensure model is loaded
    
    test_cases = [
        "không có gì ngoài bụi hết á",
        "chỉ toàn bụi thôi", 
        "bẩn quá, không thích",
        "tệ lắm, không nên đi",
        "đẹp lắm, nên đi",
        "tuyệt vời",
        "bình thường thôi",
    ]
    
    print("="*80)
    print("TESTING PhoBERT RAW PREDICTIONS")
    print("="*80)
    print(f"Model loaded: {analyzer.model_loaded}")
    print(f"Device: {analyzer.device}")
    print()
    
    for text in test_cases:
        # Get final combined score and check metadata for PhoBERT info
        final_score, pos, neg, metadata = analyzer.analyze(text)
        
        # Get rule-based prediction separately
        rule_score, pos_kw, neg_kw, _ = analyzer._rule_based_analysis(text)
        
        # Check if PhoBERT was used
        method = metadata.get('method', 'unknown')
        probs = metadata.get('probs', {})
        
        print(f"Text: '{text}'")
        if probs:
            print(f"  📊 PhoBERT probs: neg={probs.get('neg', 0):.3f}, neu={probs.get('neu', 0):.3f}, pos={probs.get('pos', 0):.3f}")
        print(f"  📋 Rule-based score: {rule_score:.3f}")
        print(f"  🎯 Final combined: {final_score:.3f}")
        print(f"  📝 Method: {method}")
        print(f"  ✅ Positive: {pos}")
        print(f"  ❌ Negative: {neg}")
        print("-" * 60)

if __name__ == "__main__":
    test_phobert_raw()
