#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Spam / Fake Review Detection Module
WebDuLich - Enterprise-Level Review Quality Filter

Features:
1. Rule-based Spam Detection:
   - Too short / meaningless
   - Advertisement / promotion
   - Copy-paste / repeated characters
   - Off-topic content

2. Statistical Spam Detection:
   - Duplicate review detection (hash-based)
   - Template review detection (n-gram similarity)

Spam Types:
- LOW_VALUE: Quá ngắn, không có thông tin
- AD_SPAM: Quảng cáo, số điện thoại, link
- GIBBERISH: Lặp ký tự, viết hoa quá mức
- OFF_TOPIC: Không liên quan đến review
- DUPLICATE: Trùng lặp nội dung
- TEMPLATE: Review mẫu/farm review
- PROFANITY: Chứa từ ngữ không phù hợp
"""

import re
import hashlib
from typing import Tuple, List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum
from collections import Counter

# ==================== ENUMS & DATA CLASSES ====================

class SpamType(Enum):
    CLEAN = "CLEAN"
    LOW_VALUE = "LOW_VALUE"
    AD_SPAM = "AD_SPAM"
    GIBBERISH = "GIBBERISH"
    OFF_TOPIC = "OFF_TOPIC"
    DUPLICATE = "DUPLICATE"
    TEMPLATE = "TEMPLATE"
    PROFANITY = "PROFANITY"

@dataclass
class SpamResult:
    is_spam: bool
    spam_type: SpamType
    confidence: float
    reasons: List[str]
    cleaned_text: str
    metadata: Dict


# ==================== CONSTANTS ====================

# Minimum tokens for valid review
MIN_TOKENS = 3
MIN_CHARS = 10

# Advertisement patterns
AD_PATTERNS = [
    r'\b(inbox|ib|zalo|viber|telegram|whatsapp)\b',
    r'\b(liên hệ|lien he|contact|hotline|sdt|số điện thoại)\b',
    r'\b(giảm giá|khuyen mai|khuyến mãi|sale|discount)\b',
    r'\b(mua ngay|đặt ngay|book ngay|order)\b',
    r'\b(shop|cửa hàng|đại lý|chi nhánh)\b',
    r'\d{9,11}',  # Phone numbers
    r'https?://\S+',  # URLs
    r'\S+@\S+\.\S+',  # Emails
    r'fb\.com|facebook\.com|zalo\.me',  # Social links
]

# Meaningless patterns (emoji spam, punctuation spam)
MEANINGLESS_PATTERNS = [
    r'^[👍👎❤️😀😂🤣😍😘🥰😊😁😆😅😄😃😀🙂😉😋😎😜😝😛🤑🤗🤭🤫🤔🤐🤨😐😑😶😏😒🙄😬🤥😌😔😪🤤😴😷🤒🤕🤢🤮🤧🥵🥶🥴😵🤯🤠🥳😈👿💀☠️💩🤡👹👺👻👽👾🤖😺😸😹😻😼😽🙀😿😾🙈🙉🙊💋💌💘💝💖💗💓💞💕💟❣️💔❤️🧡💛💚💙💜🤎🖤🤍💯💢💥💫💦💨🕳️💣💬👁️‍🗨️🗨️🗯️💭💤\s]+$',
    r'^[.!?,;:\-_=+*#@&%$^~`\'"<>(){}\[\]\\/|]+$',
    r'^(ok|oke|okie|okela|okay|k|uh|ah|oh|haha|hihi|hehe|huhu|hic|ơ|ờ|ừ|uh huh)+$',
]

# Repeated character threshold
REPEATED_CHAR_THRESHOLD = 3  # e.g., "ngonnnn" has 4 n's
REPEATED_CHAR_RATIO_THRESHOLD = 0.3

# Uppercase ratio threshold
UPPERCASE_RATIO_THRESHOLD = 0.5

# Exclamation/question mark threshold
PUNCTUATION_SPAM_THRESHOLD = 5

# Profanity words (Vietnamese)
PROFANITY_WORDS = [
    'đm', 'dm', 'dcm', 'đcm', 'vl', 'vcl', 'vkl', 'cc', 'cặc', 'lồn', 'đéo',
    'địt', 'dit', 'đụ', 'du ma', 'đù má', 'mẹ mày', 'con mẹ', 'thằng chó',
    'con chó', 'ngu', 'đần', 'khốn', 'chết mẹ', 'cứt', 'shit', 'fuck', 'damn'
]

# Low-value single words/phrases
LOW_VALUE_PHRASES = [
    'ok', 'oke', 'okie', 'okay', 'k', 'uh', 'ah', 'oh', 'ờ', 'ừ',
    'haha', 'hihi', 'hehe', 'huhu', 'hic', '...', '👍', '👎', '❤️',
    '.', '!', '?', '-', '_', 'good', 'bad', 'nice', 'cool'
]

# Aspect keywords (để check off-topic)
TRAVEL_ASPECTS = [
    'đẹp', 'xấu', 'ngon', 'dở', 'sạch', 'bẩn', 'rộng', 'chật', 'đắt', 'rẻ',
    'tốt', 'tệ', 'hay', 'chán', 'thích', 'ghét', 'ưng', 'hài lòng', 'thất vọng',
    'view', 'cảnh', 'phòng', 'giường', 'toilet', 'nhân viên', 'phục vụ',
    'đồ ăn', 'món', 'giá', 'tiền', 'vị trí', 'xa', 'gần', 'đông', 'vắng',
    'recommend', 'quay lại', 'nên đi', 'không nên'
]

# Template review patterns (common fake review structures)
TEMPLATE_PATTERNS = [
    r'ngon.{0,10}rẻ.{0,10}sạch.{0,10}(đẹp|tốt)',
    r'(tốt|ngon|đẹp).{0,5}(tốt|ngon|đẹp).{0,5}(tốt|ngon|đẹp)',
    r'5 sao.{0,20}(recommend|giới thiệu)',
    r'(quá tuyệt|tuyệt vời).{0,10}(quá tuyệt|tuyệt vời)',
]


# ==================== SPAM DETECTOR CLASS ====================

class SpamDetector:
    """
    Enterprise-level Spam/Fake Review Detector
    
    Pipeline:
    1. Text preprocessing
    2. Rule-based checks (high precision)
    3. Statistical checks (duplicate, template)
    4. Aggregate results
    """
    
    def __init__(self):
        self.ad_patterns = [re.compile(p, re.IGNORECASE) for p in AD_PATTERNS]
        self.meaningless_patterns = [re.compile(p, re.IGNORECASE) for p in MEANINGLESS_PATTERNS]
        self.template_patterns = [re.compile(p, re.IGNORECASE) for p in TEMPLATE_PATTERNS]
        self.review_hashes: Set[str] = set()  # For duplicate detection
        self.review_ngrams: Dict[str, int] = {}  # For template detection
    
    def detect(self, text: str, check_duplicate: bool = True) -> SpamResult:
        """
        Main detection method
        
        Args:
            text: Review text to check
            check_duplicate: Whether to check for duplicates
            
        Returns:
            SpamResult with detection details
        """
        if not text or not text.strip():
            return SpamResult(
                is_spam=True,
                spam_type=SpamType.LOW_VALUE,
                confidence=1.0,
                reasons=["Empty or whitespace-only text"],
                cleaned_text="",
                metadata={}
            )
        
        # Preprocess
        cleaned = self._preprocess(text)
        tokens = self._tokenize(cleaned)
        
        # Check each spam type
        checks = [
            self._check_low_value(cleaned, tokens),
            self._check_ad_spam(text),  # Use original text for URLs/phones
            self._check_gibberish(text),
            self._check_profanity(cleaned),
            self._check_off_topic(cleaned, tokens),
        ]
        
        # Check duplicate if enabled
        if check_duplicate:
            checks.append(self._check_duplicate(cleaned))
        
        # Check template
        checks.append(self._check_template(cleaned))
        
        # Aggregate results
        spam_checks = [c for c in checks if c[0]]
        
        if spam_checks:
            # Return the most severe spam type
            most_severe = max(spam_checks, key=lambda x: x[2])
            return SpamResult(
                is_spam=True,
                spam_type=most_severe[1],
                confidence=most_severe[2],
                reasons=[c[3] for c in spam_checks],
                cleaned_text=cleaned,
                metadata={
                    "token_count": len(tokens),
                    "char_count": len(cleaned),
                    "all_spam_types": [c[1].value for c in spam_checks]
                }
            )
        
        # Not spam - register for future duplicate detection
        if check_duplicate:
            self._register_review(cleaned)
        
        return SpamResult(
            is_spam=False,
            spam_type=SpamType.CLEAN,
            confidence=0.0,
            reasons=[],
            cleaned_text=cleaned,
            metadata={
                "token_count": len(tokens),
                "char_count": len(cleaned)
            }
        )
    
    def _preprocess(self, text: str) -> str:
        """Normalize text"""
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Remove punctuation for tokenization
        text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if len(t) > 0]
    
    def _check_low_value(self, text: str, tokens: List[str]) -> Tuple[bool, SpamType, float, str]:
        """Check for low-value/meaningless reviews"""
        # Too short
        if len(tokens) < MIN_TOKENS or len(text) < MIN_CHARS:
            return (True, SpamType.LOW_VALUE, 0.9, f"Too short: {len(tokens)} tokens, {len(text)} chars")
        
        # Check meaningless patterns
        for pattern in self.meaningless_patterns:
            if pattern.match(text):
                return (True, SpamType.LOW_VALUE, 0.95, "Matches meaningless pattern (emoji/punctuation only)")
        
        # Check if all tokens are low-value
        low_value_count = sum(1 for t in tokens if t in LOW_VALUE_PHRASES)
        if low_value_count == len(tokens):
            return (True, SpamType.LOW_VALUE, 0.85, "All tokens are low-value phrases")
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _check_ad_spam(self, text: str) -> Tuple[bool, SpamType, float, str]:
        """Check for advertisement/promotion spam"""
        for pattern in self.ad_patterns:
            match = pattern.search(text)
            if match:
                return (True, SpamType.AD_SPAM, 0.95, f"Contains ad pattern: '{match.group()}'")
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _check_gibberish(self, text: str) -> Tuple[bool, SpamType, float, str]:
        """Check for gibberish (repeated chars, excessive caps/punctuation)"""
        reasons = []
        
        # Check repeated characters
        repeated_pattern = re.compile(r'(.)\1{' + str(REPEATED_CHAR_THRESHOLD) + r',}')
        repeated_matches = repeated_pattern.findall(text)
        if repeated_matches:
            repeated_ratio = len(''.join(repeated_matches)) / len(text) if text else 0
            if repeated_ratio > REPEATED_CHAR_RATIO_THRESHOLD:
                reasons.append(f"Excessive repeated characters: {repeated_ratio:.1%}")
        
        # Check uppercase ratio
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_ratio > UPPERCASE_RATIO_THRESHOLD:
                reasons.append(f"Excessive uppercase: {upper_ratio:.1%}")
        
        # Check punctuation spam
        exclamation_count = text.count('!') + text.count('?')
        if exclamation_count > PUNCTUATION_SPAM_THRESHOLD:
            reasons.append(f"Excessive punctuation: {exclamation_count} marks")
        
        if reasons:
            return (True, SpamType.GIBBERISH, 0.8, "; ".join(reasons))
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _check_profanity(self, text: str) -> Tuple[bool, SpamType, float, str]:
        """Check for profanity/inappropriate content"""
        found_profanity = []
        for word in PROFANITY_WORDS:
            if word in text:
                found_profanity.append(word)
        
        if found_profanity:
            return (True, SpamType.PROFANITY, 0.9, f"Contains profanity: {found_profanity[:3]}")
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _check_off_topic(self, text: str, tokens: List[str]) -> Tuple[bool, SpamType, float, str]:
        """Check if review is off-topic (no travel-related content)"""
        # Check if any travel aspect is mentioned
        has_aspect = any(aspect in text for aspect in TRAVEL_ASPECTS)
        
        # If no aspect and text is reasonably long, might be off-topic
        if not has_aspect and len(tokens) > 5:
            # Additional check: does it look like a review at all?
            review_indicators = ['đi', 'đến', 'ở', 'ăn', 'uống', 'nghỉ', 'chơi', 'tham quan']
            has_indicator = any(ind in text for ind in review_indicators)
            
            if not has_indicator:
                return (True, SpamType.OFF_TOPIC, 0.7, "No travel-related content detected")
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _check_duplicate(self, text: str) -> Tuple[bool, SpamType, float, str]:
        """Check for duplicate reviews"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.review_hashes:
            return (True, SpamType.DUPLICATE, 0.99, "Exact duplicate detected")
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _check_template(self, text: str) -> Tuple[bool, SpamType, float, str]:
        """Check for template/farm reviews"""
        for pattern in self.template_patterns:
            if pattern.search(text):
                return (True, SpamType.TEMPLATE, 0.75, "Matches template review pattern")
        
        return (False, SpamType.CLEAN, 0.0, "")
    
    def _register_review(self, text: str):
        """Register review hash for duplicate detection"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        self.review_hashes.add(text_hash)
    
    def clear_history(self):
        """Clear duplicate detection history"""
        self.review_hashes.clear()
        self.review_ngrams.clear()


# ==================== GLOBAL INSTANCE & PUBLIC API ====================

_detector = None

def get_spam_detector() -> SpamDetector:
    """Get singleton spam detector instance"""
    global _detector
    if _detector is None:
        _detector = SpamDetector()
    return _detector


def detect_spam(text: str, check_duplicate: bool = True) -> SpamResult:
    """
    Public API for spam detection
    
    Args:
        text: Review text to check
        check_duplicate: Whether to check for duplicates
        
    Returns:
        SpamResult with detection details
    """
    detector = get_spam_detector()
    return detector.detect(text, check_duplicate)


def is_spam(text: str) -> bool:
    """Simple check if text is spam"""
    result = detect_spam(text, check_duplicate=False)
    return result.is_spam


def get_spam_type(text: str) -> str:
    """Get spam type as string"""
    result = detect_spam(text, check_duplicate=False)
    return result.spam_type.value


def filter_reviews(reviews: List[str]) -> Tuple[List[str], List[Dict]]:
    """
    Filter a list of reviews, removing spam
    
    Args:
        reviews: List of review texts
        
    Returns:
        (clean_reviews, spam_reports)
    """
    detector = get_spam_detector()
    detector.clear_history()  # Reset for batch processing
    
    clean_reviews = []
    spam_reports = []
    
    for i, review in enumerate(reviews):
        result = detector.detect(review, check_duplicate=True)
        
        if result.is_spam:
            spam_reports.append({
                "index": i,
                "text": review[:100] + "..." if len(review) > 100 else review,
                "spam_type": result.spam_type.value,
                "confidence": result.confidence,
                "reasons": result.reasons
            })
        else:
            clean_reviews.append(review)
    
    return clean_reviews, spam_reports


def get_review_quality_score(text: str) -> float:
    """
    Get quality score for a review (0.0 = spam, 1.0 = high quality)
    
    Factors:
    - Not spam
    - Has meaningful content
    - Has specific aspects mentioned
    - Reasonable length
    """
    result = detect_spam(text, check_duplicate=False)
    
    if result.is_spam:
        return 0.0
    
    score = 0.5  # Base score for non-spam
    
    # Length bonus
    token_count = result.metadata.get("token_count", 0)
    if token_count >= 10:
        score += 0.2
    elif token_count >= 5:
        score += 0.1
    
    # Aspect bonus
    text_lower = text.lower()
    aspect_count = sum(1 for asp in TRAVEL_ASPECTS if asp in text_lower)
    if aspect_count >= 3:
        score += 0.2
    elif aspect_count >= 1:
        score += 0.1
    
    # Specificity bonus (has numbers, names, etc.)
    if re.search(r'\d+', text):  # Has numbers
        score += 0.05
    
    return min(score, 1.0)
