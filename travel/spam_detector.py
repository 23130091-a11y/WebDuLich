"""
Spam Detection System - 3-Layer Defense
Layer A: Hard block (links, phone, obvious spam)
Layer B: Spam scoring (pending/shadow-ban)
Layer C: Behavior-based (rate limit, duplicate)
"""
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
import hashlib


# ==================== CONSTANTS ====================

# Layer A: Hard block patterns
LINK_PATTERNS = [
    r'https?://',
    r'www\.',
    r'\.com\b', r'\.vn\b', r'\.net\b', r'\.org\b',
    r'fb\.com', r't\.me', r'zalo\.me',
    r'shopee', r'lazada', r'tiktok',
    r'bit\.ly', r'goo\.gl',
]

PHONE_PATTERNS = [
    r'0\d{9,10}',  # 0912345678 or 09123456789
    r'\+84\d{9,10}',  # +84912345678
    r'84\d{9,10}',  # 84912345678
]

# Layer B: Spam keywords (Vietnamese)
SPAM_KEYWORDS_HIGH = [  # +0.4 each
    'inbox', 'ib', 'liên hệ', 'lien he',
    'zalo', 'sđt', 'sdt', 'call', 'gọi ngay',
    'đại lý', 'dai ly', 'phân phối',
]

SPAM_KEYWORDS_MEDIUM = [  # +0.2 each
    'giá rẻ', 'gia re', 'sale', 'khuyến mãi', 'khuyen mai',
    'đặt hàng', 'dat hang', 'ship', 'free ship',
    'giảm giá', 'giam gia', 'ưu đãi', 'uu dai',
    'mua ngay', 'click', 'link',
]

# Low quality indicators
LOW_QUALITY_ONLY = [
    'ok', 'oke', 'okie', 'hay', 'tốt', 'tot', 'đẹp', 'dep',
    '.', '...', '!', '!!!', 'good', 'nice', 'wow',
]


class SpamDetector:
    """
    Spam detection with 3-layer defense system
    """
    
    def __init__(self):
        self.link_regex = re.compile('|'.join(LINK_PATTERNS), re.IGNORECASE)
        self.phone_regex = re.compile('|'.join(PHONE_PATTERNS))
    
    def analyze(self, comment: str, user_ip: str = None, user_id: int = None,
                destination_id: int = None) -> Dict:
        """
        Analyze comment for spam
        
        Returns:
            {
                'spam_score': float (0-1),
                'is_spam': bool,
                'is_low_quality': bool,
                'action': 'allow' | 'pending' | 'block' | 'shadow',
                'flags': list of triggered rules,
                'details': dict with rule details
            }
        """
        result = {
            'spam_score': 0.0,
            'is_spam': False,
            'is_low_quality': False,
            'action': 'allow',
            'flags': [],
            'details': {}
        }
        
        if not comment:
            result['is_low_quality'] = True
            result['flags'].append('empty_comment')
            return result
        
        comment_lower = comment.lower().strip()
        
        # Layer A: Hard block checks
        layer_a_result = self._check_layer_a(comment_lower)
        if layer_a_result['hard_block']:
            result['spam_score'] = 1.0
            result['is_spam'] = True
            result['action'] = 'block'
            result['flags'].extend(layer_a_result['flags'])
            return result
        
        result['spam_score'] += layer_a_result['score']
        result['flags'].extend(layer_a_result['flags'])
        
        # Layer B: Spam scoring
        layer_b_result = self._check_layer_b(comment_lower)
        result['spam_score'] += layer_b_result['score']
        result['flags'].extend(layer_b_result['flags'])
        result['is_low_quality'] = layer_b_result.get('is_low_quality', False)
        
        # Layer C: Behavior checks (if IP/user provided)
        if user_ip or user_id:
            layer_c_result = self._check_layer_c(
                comment_lower, user_ip, user_id, destination_id
            )
            result['spam_score'] += layer_c_result['score']
            result['flags'].extend(layer_c_result['flags'])
        
        # Clamp score
        result['spam_score'] = min(1.0, result['spam_score'])
        
        # Determine action
        if result['spam_score'] >= 0.8:
            result['is_spam'] = True
            result['action'] = 'block'
        elif result['spam_score'] >= 0.5:
            result['is_spam'] = True
            result['action'] = 'pending'
        elif result['spam_score'] >= 0.3:
            result['action'] = 'shadow'
        elif result['is_low_quality']:
            result['action'] = 'low_quality'
        else:
            result['action'] = 'allow'
        
        return result
    
    def _check_layer_a(self, comment: str) -> Dict:
        """Layer A: Hard block patterns (links, phone numbers)"""
        result = {'hard_block': False, 'score': 0.0, 'flags': []}
        
        # Check for links
        if self.link_regex.search(comment):
            result['score'] += 0.7
            result['flags'].append('contains_link')
            # Hard block if link + short comment
            if len(comment.split()) < 10:
                result['hard_block'] = True
        
        # Check for phone numbers
        if self.phone_regex.search(comment):
            result['score'] += 0.7
            result['flags'].append('contains_phone')
            # Hard block if phone + spam keywords
            if any(kw in comment for kw in SPAM_KEYWORDS_HIGH):
                result['hard_block'] = True
        
        return result
    
    def _check_layer_b(self, comment: str) -> Dict:
        """Layer B: Spam scoring based on content"""
        result = {'score': 0.0, 'flags': [], 'is_low_quality': False}
        
        words = comment.split()
        word_count = len(words)
        
        # 1. High-risk spam keywords (+0.4 each, max 0.8)
        high_kw_count = sum(1 for kw in SPAM_KEYWORDS_HIGH if kw in comment)
        if high_kw_count > 0:
            result['score'] += min(high_kw_count * 0.4, 0.8)
            result['flags'].append(f'spam_keywords_high:{high_kw_count}')
        
        # 2. Medium-risk spam keywords (+0.2 each, max 0.4)
        med_kw_count = sum(1 for kw in SPAM_KEYWORDS_MEDIUM if kw in comment)
        if med_kw_count > 0:
            result['score'] += min(med_kw_count * 0.2, 0.4)
            result['flags'].append(f'spam_keywords_medium:{med_kw_count}')
        
        # 3. Comment too short (+0.2)
        if word_count < 3:
            result['score'] += 0.2
            result['flags'].append('too_short')
            result['is_low_quality'] = True
        elif word_count < 6:
            result['is_low_quality'] = True
            result['flags'].append('short_comment')
        
        # 4. Emoji ratio > 60% (+0.2)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        emojis = emoji_pattern.findall(comment)
        emoji_chars = sum(len(e) for e in emojis)
        if len(comment) > 0 and emoji_chars / len(comment) > 0.6:
            result['score'] += 0.2
            result['flags'].append('high_emoji_ratio')
            result['is_low_quality'] = True
        
        # 5. Repeated characters (!!!! / ???? / )))))) (+0.2)
        if re.search(r'(.)\1{4,}', comment):
            result['score'] += 0.2
            result['flags'].append('repeated_chars')
        
        # 6. ALL CAPS (+0.1)
        alpha_chars = [c for c in comment if c.isalpha()]
        if len(alpha_chars) > 5 and sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars) > 0.8:
            result['score'] += 0.1
            result['flags'].append('all_caps')
        
        # 7. Only low-quality words
        if word_count <= 3 and all(w in LOW_QUALITY_ONLY for w in words):
            result['is_low_quality'] = True
            result['flags'].append('only_generic_words')
        
        return result
    
    def _check_layer_c(self, comment: str, user_ip: str, user_id: int,
                       destination_id: int) -> Dict:
        """Layer C: Behavior-based checks (rate limit, duplicate)"""
        result = {'score': 0.0, 'flags': []}
        
        # Generate cache keys
        ip_key = f"spam_ip:{user_ip}" if user_ip else None
        user_key = f"spam_user:{user_id}" if user_id else None
        comment_hash = hashlib.md5(comment.encode()).hexdigest()[:16]
        
        # 1. Rate limiting - check burst behavior
        if ip_key:
            # Count reviews from this IP in last hour
            ip_count = cache.get(ip_key, 0)
            if ip_count >= 10:
                result['score'] += 0.6
                result['flags'].append('burst_ip_hour')
            elif ip_count >= 5:
                result['score'] += 0.3
                result['flags'].append('high_frequency_ip')
            
            # Increment counter (expires in 1 hour)
            cache.set(ip_key, ip_count + 1, 3600)
        
        # 2. Duplicate detection
        dup_key = f"spam_dup:{comment_hash}"
        dup_count = cache.get(dup_key, 0)
        if dup_count > 0:
            result['score'] += 0.8
            result['flags'].append(f'duplicate_comment:{dup_count}')
        
        # Store comment hash (expires in 24 hours)
        cache.set(dup_key, dup_count + 1, 86400)
        
        # 3. Same destination check (if destination_id provided)
        if destination_id and (user_ip or user_id):
            dest_key = f"spam_dest:{destination_id}:{user_ip or user_id}"
            if cache.get(dest_key):
                result['score'] += 0.4
                result['flags'].append('same_destination_recent')
            else:
                # Mark this destination as reviewed (24 hours)
                cache.set(dest_key, True, 86400)
        
        return result
    
    def get_spam_summary(self, result: Dict) -> str:
        """Get human-readable summary of spam detection result"""
        if result['action'] == 'block':
            return f"🚫 BLOCKED (score: {result['spam_score']:.2f}) - {', '.join(result['flags'])}"
        elif result['action'] == 'pending':
            return f"⏳ PENDING (score: {result['spam_score']:.2f}) - {', '.join(result['flags'])}"
        elif result['action'] == 'shadow':
            return f"👻 SHADOW (score: {result['spam_score']:.2f}) - {', '.join(result['flags'])}"
        elif result['action'] == 'low_quality':
            return f"📉 LOW QUALITY - {', '.join(result['flags'])}"
        else:
            return f"✅ ALLOWED (score: {result['spam_score']:.2f})"


# Singleton instance
_spam_detector = None

def get_spam_detector() -> SpamDetector:
    """Get singleton spam detector instance"""
    global _spam_detector
    if _spam_detector is None:
        _spam_detector = SpamDetector()
    return _spam_detector


def check_spam(comment: str, user_ip: str = None, user_id: int = None,
               destination_id: int = None) -> Dict:
    """
    Public API for spam detection
    
    Returns:
        {
            'spam_score': float (0-1),
            'is_spam': bool,
            'is_low_quality': bool,
            'action': 'allow' | 'pending' | 'block' | 'shadow' | 'low_quality',
            'flags': list of triggered rules
        }
    """
    detector = get_spam_detector()
    return detector.analyze(comment, user_ip, user_id, destination_id)
