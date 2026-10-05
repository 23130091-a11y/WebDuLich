"""
Unified AI Engine for WebDuLich
Gộp sentiment analysis và recommendation engine thành 1 module duy nhất

Features:
- PhoBERT sentiment analysis với fallback rule-based
- Enhanced rule-based với JSON keywords
- Aspect-based sentiment analysis
- Negation, intensifier, downtoner handling
- Sarcasm detection
- Recommendation scoring algorithm
- Caching system tích hợp
- Search functionality
- Retry mechanism for robustness
"""

import os
import re
import json
import torch
import logging
import hashlib
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Tuple, List, Dict, Any, Optional

from django.db.models import Q, Avg, Count
from django.core.cache import cache
from django.conf import settings
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# ==================== LOAD JSON KEYWORDS ====================

def load_json_keywords():
    """Load sentiment and aspect keywords from JSON files"""
    # Try multiple locations (prioritize travel/ directory)
    possible_dirs = [
        os.path.join(settings.BASE_DIR, 'travel'),  # WebDuLich-fix-conflic/travel/ (PREFERRED)
        settings.BASE_DIR,  # WebDuLich-fix-conflic/
        settings.BASE_DIR.parent if hasattr(settings.BASE_DIR, 'parent') else None,  # WebDuLich-fix-conflic/../
    ]
    
    sentiment_data = {}
    aspect_data = {}
    
    for base_dir in possible_dirs:
        if base_dir is None:
            continue
            
        sentiment_file = os.path.join(base_dir, 'travel_sentiment_keywords.json')
        aspect_file = os.path.join(base_dir, 'travel_aspect_keywords.json')
        
        if not sentiment_data and os.path.exists(sentiment_file):
            try:
                with open(sentiment_file, 'r', encoding='utf-8') as f:
                    sentiment_data = json.load(f)
                logger.info(f"Loaded sentiment keywords from {sentiment_file}")
            except Exception as e:
                logger.warning(f"Could not load sentiment keywords from {sentiment_file}: {e}")
        
        if not aspect_data and os.path.exists(aspect_file):
            try:
                with open(aspect_file, 'r', encoding='utf-8') as f:
                    aspect_data = json.load(f)
                logger.info(f"Loaded aspect keywords from {aspect_file}")
            except Exception as e:
                logger.warning(f"Could not load aspect keywords from {aspect_file}: {e}")
        
        if sentiment_data and aspect_data:
            break
    
    if not sentiment_data:
        logger.warning("Sentiment keywords not loaded - using empty dict")
    if not aspect_data:
        logger.warning("Aspect keywords not loaded - using empty dict")
    
    return sentiment_data, aspect_data

# Load keywords at module level
SENTIMENT_DATA, ASPECT_DATA = load_json_keywords()

# ==================== CONSTANTS ====================

# Từ phủ định (negation)
NEGATION_WORDS = [
    'không', 'ko', 'k', 'chẳng', 'chả', 'đừng', 'chưa',
    'không phải', 'không hề', 'không bao giờ', 'chẳng bao giờ',
    'không còn', 'chẳng còn', 'không thể', 'chưa bao giờ',
    'chưa từng', 'không được', 'chẳng được', 'không có',
    'thiếu', 'mất', 'hết', 'không thấy', 'chẳng thấy'
]

# Từ giảm nhẹ (downtoner)
DOWNTONERS = {
    'hơi': 0.6,
    'khá': 0.6,
    'tương đối': 0.6,
    'cũng': 0.6,
    'hơi hơi': 0.5
}

# Từ tăng cường (intensifier)
INTENSIFIERS_STRONG = {
    'cực kỳ': 1.4,
    'cực kì': 1.4,
    'siêu': 1.4,
    'vô cùng': 1.4,
    'cực': 1.4,
    'cực luôn': 1.4
}

INTENSIFIERS_MEDIUM = {
    'rất': 1.25,
    'quá': 1.25,
    'thật sự': 1.25,
    'thực sự': 1.25,
    'rất là': 1.25,
    'hoàn toàn': 1.25,
    'tuyệt đối': 1.25
}

# Merge all intensifiers
INTENSIFIERS = {**INTENSIFIERS_STRONG, **INTENSIFIERS_MEDIUM}

# Sarcasm indicators
SARCASM_INDICATORS = [
    'ha', 'haha', 'hihi', 'hehe',
    ':))', '=))', '🙂🙂', '😏', '😅',
    'nhỉ', 'nhể', 'nhở', 'nhé'
]

# Contrast words - phần sau thường quan trọng hơn
CONTRAST_WORDS = [
    'nhưng', 'tuy nhiên', 'tuy', 'mặc dù', 'dù', 'song',
    'thế nhưng', 'nhưng mà', 'tuy vậy', 'dù vậy', 'dù sao'
]

# Negative behavior patterns - chỉ báo tiêu cực mạnh
NEGATIVE_BEHAVIOR_PATTERNS = [
    ('không', 'quay lại'),
    ('không', 'recommend'),
    ('không', 'giới thiệu'),
    ('không', 'đề xuất'),
    ('không', 'nên đi'),
    ('không', 'đáng'),
    ('chẳng', 'quay lại'),
    ('sẽ không', 'quay lại'),
    ('lần sau', 'không'),
    ('không bao giờ', 'quay lại'),
    ('không bao giờ', 'đến'),
    ('thất vọng', 'hoàn toàn'),
    ('hoàn toàn', 'thất vọng'),
    # Pattern thất vọng khi thực tế không như kỳ vọng/hình ảnh
    ('nhìn hình', 'tới nơi'),
    ('nhìn hình', 'đến nơi'),
    ('hình thì', 'thực tế'),
    ('ảnh thì', 'thực tế'),
    ('xịn', 'tụt mood'),
    ('đẹp', 'tụt mood'),
    ('tới nơi', 'tụt'),
    ('đến nơi', 'tụt'),
    ('kỳ vọng', 'thất vọng'),
    ('mong đợi', 'thất vọng'),
    ('tưởng', 'thất vọng'),
    ('tưởng', 'ai ngờ'),
    ('nhìn', 'khác xa'),
    ('hình', 'khác xa'),
]

# Stopwords tiếng Việt
STOPWORDS = [
    'là', 'của', 'và', 'có', 'được', 'trong', 'với', 'cho', 'từ', 'này', 'đó',
    'một', 'các', 'những', 'để', 'khi', 'đã', 'sẽ', 'bị', 'nếu', 'như', 'thì',
    'mà', 'hay', 'hoặc', 'nhưng', 'vì', 'nên', 'lại', 'còn', 'đang'
]


# ==================== TEXT NORMALIZATION ====================

class TextNormalizer:
    """Text normalization với teencode và slang mapping"""
    
    def __init__(self):
        self.slang_map = SENTIMENT_DATA.get('slang_map', {})
        # Sort by length (longest first) for proper multi-word matching
        self.sorted_slang = sorted(self.slang_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    def normalize(self, text: str) -> str:
        """
        Chuẩn hóa text:
        - Lowercase
        - Map teencode/slang (longest-first matching)
        - Giữ dấu tiếng Việt
        - Normalize whitespace
        """
        if not text:
            return ""
        
        # Lowercase
        text = text.lower()
        
        # Normalize whitespace first
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Replace slang/teencode (longest phrases first)
        # Add padding for easier boundary matching
        text = ' ' + text + ' '
        
        for slang, standard in self.sorted_slang:
            # Add spaces around slang for word boundary matching
            slang_pattern = ' ' + slang + ' '
            standard_replace = ' ' + standard + ' '
            text = text.replace(slang_pattern, standard_replace)
        
        # Remove padding and normalize spaces
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Tách rời các dấu câu khỏi từ để tránh dính token (ví dụ: "ổn," -> "ổn ,")
        text = re.sub(r'([.,!?])', r' \1 ', text)
        
        # Normalize whitespace again after punctuation separation
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Keep Vietnamese characters and basic punctuation
        text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ.,!?]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if t]


# ==================== SENTIMENT ANALYZER ====================

class SentimentAnalyzer:
    """
    Enhanced Sentiment Analyzer với PhoBERT + Advanced Rule-based fallback
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_loaded = False
        self.normalizer = TextNormalizer()
        
        # Load keywords from JSON
        self.positive_keywords = SENTIMENT_DATA.get('positive', {})
        self.negative_keywords = SENTIMENT_DATA.get('negative', {})
        self.neutral_soft = SENTIMENT_DATA.get('neutral_soft', [])
        
    def load_model(self):
        """Load PhoBERT model (lazy loading)"""
        if self.model_loaded:
            return
        
        try:
            logger.info("Loading PhoBERT sentiment model...")

            # Try to load fine-tuned model first
            finetuned_path = os.path.join(settings.BASE_DIR, 'travel', 'phobert-travel-sentiment-final')

            if os.path.exists(finetuned_path):
                try:
                    self._load_from(finetuned_path)
                    logger.info(f"✅ Using FINE-TUNED model from: {finetuned_path}")
                    self.model_loaded = True
                    logger.info(f"PhoBERT model loaded successfully on {self.device}")
                    return
                except Exception as e:
                    # Weights hỏng/thiếu (vd: Git LFS pointer chưa pull) — không
                    # bỏ cuộc, vẫn còn model public trên HF hub làm fallback.
                    logger.error(f"Fine-tuned model failed to load: {e}")

            self._load_from("wonrax/phobert-base-vietnamese-sentiment")
            logger.info("✅ Using ORIGINAL model from HF hub (wonrax/phobert-base-vietnamese-sentiment)")
            self.model_loaded = True
            logger.info(f"PhoBERT model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load PhoBERT model: {e}")
            logger.warning("Will use rule-based sentiment analysis")
            self.model_loaded = False

    def _load_from(self, model_name: str):
        """Load tokenizer + model từ đường dẫn/HF hub và setup inference mode."""
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
    
    def analyze(self, text: str) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """
        Phân tích sentiment của text
        
        Returns:
            tuple: (sentiment_score, positive_keywords, negative_keywords, metadata)
                - sentiment_score: float từ -1 đến 1
                - positive_keywords: list từ khóa tích cực
                - negative_keywords: list từ khóa tiêu cực
                - metadata: dict chứa thông tin phân tích (aspects, sarcasm_risk, etc.)
        """
        if not text or not text.strip():
            return 0.0, [], [], {}
        
        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        cache_key = f'sentiment_v2:{text_hash}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Load model nếu chưa load
        if not self.model_loaded:
            self.load_model()
        
        # Sử dụng PhoBERT nếu có, fallback về rule-based
        if self.model_loaded:
            result = self._phobert_analysis(text)
        else:
            result = self._rule_based_analysis(text)
        
        # Cache result
        cache_timeout = getattr(settings, 'CACHE_TTL', {}).get('sentiment', 86400)
        cache.set(cache_key, result, cache_timeout)
        
        return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((RuntimeError, torch.cuda.OutOfMemoryError)),
        reraise=True
    )
    def _phobert_analysis(self, text: str) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """
        PhoBERT sentiment analysis with confidence gating and smart combine.
        
        Strategy:
        - PhoBERT chỉ win khi confidence cao
        - Rule-based win khi có keyword mạnh hoặc PhoBERT không tự tin
        - Combine weighted khi cả hai đều có giá trị
        - OVERRIDE: Negative behavior patterns force negative score
        """
        try:
            # 1. Get rule-based analysis first (always needed for keywords/aspects)
            rule_score, pos_keywords, neg_keywords, metadata = self._rule_based_analysis(text)
            
            # 1.5 CHECK NEGATIVE BEHAVIOR PATTERNS FIRST (CRITICAL!)
            # These patterns indicate clear disappointment/negative sentiment
            # and should override PhoBERT's potentially incorrect positive score
            text_normalized = self.normalizer.normalize(text)
            negative_pattern_count = 0
            matched_patterns = []
            
            for pattern in NEGATIVE_BEHAVIOR_PATTERNS:
                if len(pattern) == 2:
                    word1, word2 = pattern
                    if word1 in text_normalized and word2 in text_normalized:
                        idx1 = text_normalized.find(word1)
                        idx2 = text_normalized.find(word2)
                        # Check if pattern words appear in order within 40 chars
                        if idx1 < idx2 and idx2 - idx1 < 40:
                            negative_pattern_count += 1
                            matched_patterns.append(f"{word1} {word2}")
            
            # If multiple negative patterns detected, FORCE negative score
            if negative_pattern_count >= 2:
                # Strong override - this is clearly a negative review
                override_score = -0.6 - (negative_pattern_count * 0.1)  # More patterns = more negative
                override_score = max(-1.0, override_score)
                
                # Add matched patterns to negative keywords
                neg_keywords.extend(matched_patterns)
                neg_keywords = list(set(neg_keywords))  # Remove duplicates
                
                metadata['method'] = 'negative_pattern_override'
                metadata['matched_patterns'] = matched_patterns
                metadata['pattern_count'] = negative_pattern_count
                metadata['override_reason'] = 'Multiple disappointment patterns detected'
                
                return float(override_score), pos_keywords, neg_keywords, metadata
            
            # 2. Get PhoBERT prediction
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=-1)
            
            probs = probabilities.cpu().numpy()[0]
            
            # 3. Calculate PhoBERT score with proper scaling
            if len(probs) == 2:  # Binary classification (neg, pos)
                neg_prob, pos_prob = probs
                neu_prob = 0.0
            else:  # 3-class classification (neg, neu, pos)
                neg_prob, neu_prob, pos_prob = probs
            
            # Scale PhoBERT score properly: (pos - neg) * (1 - neu)
            # This reduces score when neutral is high
            phobert_score = (pos_prob - neg_prob) * (1 - neu_prob * 0.5)
            
            # 3.5 Apply penalty if ANY negative pattern detected
            if negative_pattern_count == 1:
                # Single pattern: apply moderate penalty
                phobert_score = phobert_score - 0.4
                if phobert_score > 0:
                    phobert_score = phobert_score * 0.5  # Reduce positive magnitude
                neg_keywords.extend(matched_patterns)
                metadata['pattern_penalty_applied'] = True
            
            # 4. Calculate confidence (top1 - top2)
            probs_sorted = sorted([pos_prob, neu_prob, neg_prob], reverse=True)
            confidence = probs_sorted[0] - probs_sorted[1]
            
            # 5. Smart combine with gating logic
            final_score, combine_method = self._combine_scores(
                rule_score, phobert_score, confidence, 
                len(pos_keywords), len(neg_keywords)
            )
            
            # Update metadata
            metadata['method'] = combine_method
            metadata['phobert_score'] = float(phobert_score)
            metadata['rule_score'] = float(rule_score)
            metadata['confidence'] = float(confidence)
            metadata['probs'] = {
                'pos': float(pos_prob),
                'neu': float(neu_prob),
                'neg': float(neg_prob)
            }
            if matched_patterns:
                metadata['matched_patterns'] = matched_patterns
            
            return float(final_score), pos_keywords, neg_keywords, metadata
            
        except Exception as e:
            logger.error(f"PhoBERT analysis failed: {e}")
            return self._rule_based_analysis(text)
    
    def _combine_scores(
        self, 
        rule_score: float, 
        phobert_score: float, 
        confidence: float,
        num_pos_keywords: int,
        num_neg_keywords: int
    ) -> Tuple[float, str]:
        """
        PhoBERT-Primary Combine Strategy (v3.2)
        
        Chiến lược: PhoBERT là PRIMARY, Rule-based là CALIBRATION
        
        Nguyên tắc:
        1. PhoBERT luôn đóng vai trò chính (55-70% weight)
        2. Rule-based dùng để calibrate và xử lý edge cases
        3. Mixed sentiment → kéo về neutral dựa trên PhoBERT
        4. Neutral soft words → giữ gần neutral (threshold 0.2)
        
        Returns:
            (final_score, method_name)
        """
        total_keywords = num_pos_keywords + num_neg_keywords
        
        # === CASE 1: Mixed sentiment (có cả pos và neg keywords) ===
        # Đây là case quan trọng nhất - cần kéo về neutral
        if num_pos_keywords > 0 and num_neg_keywords > 0:
            # PhoBERT quyết định hướng, nhưng dampen mạnh về neutral
            balance = min(num_pos_keywords, num_neg_keywords) / max(num_pos_keywords, num_neg_keywords)
            
            # Damping mạnh hơn khi balance cao (keywords cân bằng)
            damping = 0.40 + (balance * 0.30)
            
            # PhoBERT 60%, rule 40%
            combined = 0.60 * phobert_score + 0.40 * rule_score
            dampened = combined * (1 - damping)
            return max(-1.0, min(1.0, dampened)), "phobert_mixed_neutral_pull"
        
        # === CASE 2: Chỉ có neutral soft keywords (ok, được, tạm, ổn) ===
        # Rule score thấp (<0.12) thường là neutral soft only
        if total_keywords > 0 and abs(rule_score) < 0.12:
            # Neutral soft → kéo mạnh về neutral
            # PhoBERT 40%, rule 60%, rồi dampen mạnh
            combined = 0.40 * phobert_score + 0.60 * rule_score
            dampened = combined * 0.35  # Giữ 35% magnitude → gần neutral
            return max(-1.0, min(1.0, dampened)), "phobert_neutral_soft_strong_pull"
        
        # === CASE 3: Weak positive keywords (0.12 <= rule < 0.25) ===
        # Có keywords nhưng yếu → dampen về neutral hơn
        if total_keywords > 0 and 0.12 <= abs(rule_score) < 0.25:
            # PhoBERT 50%, rule 50%, dampen nhẹ
            combined = 0.50 * phobert_score + 0.50 * rule_score
            dampened = combined * 0.6  # Giữ 60%
            return max(-1.0, min(1.0, dampened)), "phobert_weak_signal_calibrated"
        
        # === CASE 4: PhoBERT confidence thấp (<0.20) ===
        if confidence < 0.20:
            # PhoBERT không chắc → mix với rule nhiều hơn
            # PhoBERT 45%, rule 55%
            final = 0.45 * phobert_score + 0.55 * rule_score
            return max(-1.0, min(1.0, final)), "phobert_low_conf_rule_assist"
        
        # === CASE 5: PhoBERT high confidence (>0.45) ===
        if confidence >= 0.45:
            # PhoBERT rất tự tin → 70% PhoBERT, 30% rule
            final = 0.70 * phobert_score + 0.30 * rule_score
            return max(-1.0, min(1.0, final)), "phobert_dominant_high_conf"
        
        # === CASE 6: Không có keywords → PhoBERT quyết định ===
        if total_keywords == 0:
            # Không có domain signal → tin PhoBERT nhưng dampen
            dampened = phobert_score * 0.70
            return max(-1.0, min(1.0, dampened)), "phobert_only_no_keywords"
        
        # === CASE 7: PhoBERT và Rule đồng thuận (cùng dấu, cùng mạnh) ===
        if (phobert_score > 0.2 and rule_score > 0.2) or (phobert_score < -0.2 and rule_score < -0.2):
            # Cả hai đồng ý mạnh → PhoBERT lead, boost
            # PhoBERT 65%, rule 35%
            final = 0.65 * phobert_score + 0.35 * rule_score
            
            # Boost khi đồng thuận rất mạnh
            if abs(phobert_score) > 0.5 and abs(rule_score) > 0.5:
                final = final * 1.15
            
            return max(-1.0, min(1.0, final)), "phobert_rule_strong_agreement"
        
        # === CASE 8: PhoBERT và Rule conflict (khác dấu) ===
        if (phobert_score > 0.15 and rule_score < -0.15) or (phobert_score < -0.15 and rule_score > 0.15):
            # Conflict → PhoBERT lead nhưng dampen mạnh
            # PhoBERT 55%, rule 45%
            final = 0.55 * phobert_score + 0.45 * rule_score
            final = final * 0.65  # Dampen 35%
            return max(-1.0, min(1.0, final)), "phobert_rule_conflict_dampen"
        
        # === DEFAULT: Balanced mix với PhoBERT lead ===
        # PhoBERT 60%, rule 40%
        final = 0.60 * phobert_score + 0.40 * rule_score
        return max(-1.0, min(1.0, final)), "phobert_primary_balanced"
    
    def _rule_based_analysis(self, text: str) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """Enhanced rule-based sentiment analysis with advanced features"""
        # Normalize text
        text_normalized = self.normalizer.normalize(text)
        
        # Split into sentences
        sentences = self._split_sentences(text_normalized)
        
        total_score = 0.0
        positive_keywords = []
        negative_keywords = []
        aspect_scores = defaultdict(list)
        sarcasm_risk = False
        
        # Check for sarcasm indicators
        for indicator in SARCASM_INDICATORS:
            if indicator in text_normalized:
                sarcasm_risk = True
                break
        
        # Check for negative behavior patterns (strong negative signal)
        negative_behavior_penalty = 0.0
        for pattern in NEGATIVE_BEHAVIOR_PATTERNS:
            if len(pattern) == 2:
                word1, word2 = pattern
                if word1 in text_normalized and word2 in text_normalized:
                    # Check if they appear in order
                    idx1 = text_normalized.find(word1)
                    idx2 = text_normalized.find(word2)
                    if idx1 < idx2 and idx2 - idx1 < 30:  # Within 30 chars
                        negative_behavior_penalty -= 0.5
                        negative_keywords.append(f"{word1} {word2}")
        
        # Check for contrast words and weight accordingly
        has_contrast = any(cw in text_normalized for cw in CONTRAST_WORDS)
        
        for sentence in sentences:
            # Process each sentence
            sentence_score, pos_kw, neg_kw, aspects = self._analyze_sentence(sentence)
            
            total_score += sentence_score
            positive_keywords.extend(pos_kw)
            negative_keywords.extend(neg_kw)
            
            # Collect aspect scores
            for aspect, score in aspects.items():
                aspect_scores[aspect].append(score)
        
        # Apply negative behavior penalty
        total_score += negative_behavior_penalty
        
        # If has contrast word and mixed sentiment, weight toward negative
        # "đẹp nhưng đắt" → phần sau (đắt) quan trọng hơn
        if has_contrast and positive_keywords and negative_keywords:
            # Reduce positive impact by 20%
            if total_score > 0:
                total_score *= 0.8
        
        # Normalize score to [-1, 1]
        sentiment_score = max(-1.0, min(1.0, total_score))
        
        # Calculate average aspect scores
        avg_aspect_scores = {
            aspect: sum(scores) / len(scores)
            for aspect, scores in aspect_scores.items()
        }
        
        metadata = {
            'aspects': avg_aspect_scores,
            'sarcasm_risk': sarcasm_risk,
            'method': 'rule_based'
        }
        
        return sentiment_score, list(set(positive_keywords)), list(set(negative_keywords)), metadata
    
    def _analyze_sentence(self, sentence: str) -> Tuple[float, List[str], List[str], Dict[str, float]]:
        """
        Analyze a single sentence with advanced rule handling
        
        Returns:
            (score, positive_keywords, negative_keywords, aspect_scores)
        """
        tokens = self.normalizer.tokenize(sentence)
        sentence_score = 0.0
        pos_keywords = []
        neg_keywords = []
        aspect_scores = defaultdict(float)
        
        # Try to match multi-word phrases first (longer phrases have priority)
        all_keywords = {**self.positive_keywords, **self.negative_keywords}
        matched_positions = set()
        
        # Sort keywords by length (descending) to match longer phrases first
        sorted_keywords = sorted(all_keywords.keys(), key=lambda x: len(x.split()), reverse=True)
        
        for keyword in sorted_keywords:
            keyword_tokens = keyword.split()
            keyword_len = len(keyword_tokens)
            
            # Find all occurrences of this keyword
            for i in range(len(tokens) - keyword_len + 1):
                # Skip if any position is already matched
                if any(pos in matched_positions for pos in range(i, i + keyword_len)):
                    continue
                
                # Phân tách token hiện tại để so sánh không tính dấu câu nếu cần
                current_phrase = ' '.join(tokens[i:i+keyword_len])
                if current_phrase == keyword:
                    # Mark positions as matched
                    for pos in range(i, i + keyword_len):
                        matched_positions.add(pos)
                    
                    # Get base score
                    base_score = all_keywords[keyword]
                    
                    # Check for modifiers (negation, intensifier, downtoner)
                    modified_score, is_negated = self._apply_modifiers(
                        tokens, i, base_score
                    )
                    
                    # Add to total
                    sentence_score += modified_score
                    
                    # Track keywords
                    if modified_score > 0:
                        if is_negated and base_score < 0:
                            pos_keywords.append(f"không {keyword}")
                        else:
                            pos_keywords.append(keyword)
                    elif modified_score < 0:
                        if is_negated and base_score > 0:
                            neg_keywords.append(f"không {keyword}")
                        else:
                            neg_keywords.append(keyword)
                    
                    # Track aspect
                    aspect = self._get_aspect(keyword)
                    if aspect:
                        aspect_scores[aspect] += modified_score
        
        # Process neutral_soft words as weak positive (ok, ổn, được, tạm...)
        # Score thấp (0.10) để không làm câu mixed thành positive
        for i, token in enumerate(tokens):
            if i in matched_positions:
                continue
            if token in self.neutral_soft:
                # Neutral soft words = very weak positive (0.05)
                # Gần như neutral, chỉ hơi positive một chút
                soft_score = 0.05
                
                # Check for negation before neutral_soft
                window_start = max(0, i - 3)
                window = tokens[window_start:i]
                is_negated = any(t in NEGATION_WORDS for t in window)
                
                if is_negated:
                    # "không ok" = weak negative
                    sentence_score -= 0.05
                    neg_keywords.append(f"không {token}")
                else:
                    sentence_score += soft_score
                    pos_keywords.append(token)
                
                matched_positions.add(i)
        
        return sentence_score, pos_keywords, neg_keywords, dict(aspect_scores)
    
    def _apply_modifiers(self, tokens: List[str], keyword_pos: int, base_score: float) -> Tuple[float, bool]:
        """
        Apply negation, intensifier, and downtoner modifiers
        
        Returns:
            (modified_score, is_negated)
        """
        # Check window before keyword (up to 3 tokens)
        window_start = max(0, keyword_pos - 3)
        window = tokens[window_start:keyword_pos]
        
        is_negated = False
        multiplier = 1.0
        
        # Check for negation (highest priority)
        for token in window:
            if token in NEGATION_WORDS:
                is_negated = True
                break
        
        # Check for intensifiers and downtoners
        for token in window:
            if token in INTENSIFIERS:
                multiplier = INTENSIFIERS[token]
                break
            elif token in DOWNTONERS:
                multiplier = DOWNTONERS[token]
                break
        
        # Apply modifications
        if is_negated:
            # Negation: flip sign and reduce magnitude
            # Special case: "không tệ" should be weak positive (but not too strong)
            if base_score < 0:
                # "không tệ" -> weak positive, capped at 0.20
                modified_score = min(abs(base_score) * 0.5, 0.20)
            else:
                # "không đẹp" -> negative
                modified_score = -base_score * 0.8
        else:
            # Apply multiplier
            modified_score = base_score * multiplier
        
        # Clamp to [-1, 1]
        modified_score = max(-1.0, min(1.0, modified_score))
        
        return modified_score, is_negated
    
    def _get_aspect(self, keyword: str) -> Optional[str]:
        """Get aspect category for a keyword"""
        aspects = ASPECT_DATA.get('aspects', {})
        
        for aspect_id, aspect_info in aspects.items():
            if keyword in aspect_info.get('keywords', []):
                return aspect_id
        
        return None
    
    
    def _split_sentences(self, text: str) -> List[str]:
        """Tách văn bản thành các câu"""
        sentences = re.split(r'[.!?;,\n]', text)
        return [s.strip() for s in sentences if s.strip()]


# ==================== RECOMMENDATION ENGINE ====================

class RecommendationEngine:
    """
    Recommendation Engine cho destinations
    Sử dụng Universal Scoring Engine cho điểm gợi ý
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        # Import scoring engine
        from .scoring_engine import get_scoring_engine
        self.scoring_engine = get_scoring_engine()
    
    def search_destinations(self, query: str, filters: Dict[str, Any]) -> List:
        """
        Tìm kiếm destinations với AI scoring
        
        Args:
            query: Search query
            filters: Dict filters (location, travel_type, max_price, etc.)
            
        Returns:
            List of destinations sorted by relevance score
        """
        from .models import Destination
        
        # Build base queryset
        queryset = Destination.objects.select_related('recommendation').prefetch_related('reviews')
        
        # Apply filters
        if filters.get('location'):
            queryset = queryset.filter(location__icontains=filters['location'])
        
        if filters.get('travel_type'):
            queryset = queryset.filter(travel_type__icontains=filters['travel_type'])
        
        # Text search
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
        
        # Calculate relevance scores
        destinations = list(queryset)
        scored_destinations = []
        
        for dest in destinations:
            relevance_score = self._calculate_relevance_score(dest, query, filters)
            scored_destinations.append((dest, relevance_score))
        
        # Sort by score
        scored_destinations.sort(key=lambda x: x[1], reverse=True)
        
        return [dest for dest, score in scored_destinations]
    
    def calculate_destination_score(self, destination) -> Dict[str, float]:
        """
        Tính toán điểm số tổng hợp cho destination
        Sử dụng Universal Scoring Engine
        
        Returns:
            Dict với các scores: overall, review, sentiment, popularity
        """
        return self.scoring_engine.calculate_score(destination)
    
    def _calculate_relevance_score(self, destination, query: str, filters: Dict) -> float:
        """Tính điểm relevance cho search results"""
        score = 0.0
        
        # Base recommendation score (50% weight)
        if hasattr(destination, 'recommendation') and destination.recommendation:
            score += destination.recommendation.overall_score * 0.5
        
        # Query relevance (30% weight)
        if query:
            query_lower = query.lower()
            name_match = query_lower in destination.name.lower()
            desc_match = query_lower in (destination.description or '').lower()
            location_match = query_lower in destination.location.lower()
            
            if name_match:
                score += 30
            elif location_match:
                score += 20
            elif desc_match:
                score += 10
        
        # Filter bonus (20% weight)
        if filters.get('travel_type') and filters['travel_type'].lower() in destination.travel_type.lower():
            score += 20
        
        return score
    
    def _calculate_price_score(self, destination) -> float:
        """Tính price competitiveness score dựa trên phí vào cổng"""
        if not destination.entrance_fee:
            return 10.0  # Miễn phí = điểm cao nhất
        
        fee = float(destination.entrance_fee)
        
        if fee == 0:
            return 10.0
        elif fee < 50000:  # < 50k VND
            return 8.0
        elif fee < 100000:  # < 100k VND
            return 6.0
        elif fee < 200000:  # < 200k VND
            return 4.0
        else:
            return 2.0


# ==================== GLOBAL INSTANCES ====================

# Singleton instances
_sentiment_analyzer = None
_recommendation_engine = None

def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get singleton sentiment analyzer instance"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    return _sentiment_analyzer

def get_recommendation_engine() -> RecommendationEngine:
    """Get singleton recommendation engine instance"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine


# ==================== PUBLIC API FUNCTIONS ====================

def analyze_sentiment(text: str, rating: int = None) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
    """
    Public API for sentiment analysis with optional post-processing
    
    Args:
        text: Text to analyze
        rating: Optional rating (1-5) for calibration
        
    Returns:
        tuple: (sentiment_score, positive_keywords, negative_keywords, metadata)
    """
    analyzer = get_sentiment_analyzer()
    score, pos_kw, neg_kw, metadata = analyzer.analyze(text)
    
    # POST-PROCESSING (v2.2 improvements)
    
    # 1. Short review boost (< 8 words with weak positive signals)
    word_count = len(text.split())
    if word_count < 8 and 0 < score < 0.15:
        # Short review with weak positive → boost slightly
        if any(kw in ['ok', 'ổn', 'được', 'tạm'] for kw in pos_kw):
            score = min(score * 1.5, 0.25)  # Boost to weak positive
            metadata['post_processing'] = 'short_review_boost'
    
    # 2. Rating-based calibration (optional, if rating is provided)
    if rating is not None:
        original_score = score
        
        # Only boost/adjust if there's no strong conflict with sentiment
        # If sentiment is strongly negative (score < -0.3), we should be more cautious
        
        if rating == 5:
            if score < 0.5 and score >= -0.1:
                # Neutral or weak positive → boost to strong positive
                score = max(score, 0.6)
                metadata['calibrated'] = True
                metadata['calibration_reason'] = f'rating_5_boost (from {original_score:.3f})'
            elif score < -0.1:
                # Clear negative sentiment but rating 5 → pull towards neutral but don't force positive
                # This handles sarcasm or "accidental" 5-star ratings with negative text
                score = score + 0.3 # Reduce negative intensity but keep it negative
                metadata['calibrated'] = True
                metadata['calibration_reason'] = f'rating_5_dampen_conflict (from {original_score:.3f})'
        
        elif rating == 4 and score < 0.15:
            if score >= -0.2:
                # Weak negative or neutral → adjust to weak positive
                score = max(score, 0.20)
                metadata['calibrated'] = True
                metadata['calibration_reason'] = f'rating_4_boost (from {original_score:.3f})'
        
        elif rating == 1 and score > -0.5:
            if score <= 0.2:
                # Weak positive or neutral → adjust to strong negative
                score = min(score, -0.6)
                metadata['calibrated'] = True
                metadata['calibration_reason'] = f'rating_1_adjust (from {original_score:.3f})'
            elif score > 0.2:
                # Strong positive text but rating 1 → pull towards neutral
                score = score - 0.4
                metadata['calibrated'] = True
                metadata['calibration_reason'] = f'rating_1_dampen_conflict (from {original_score:.3f})'
    
    return score, pos_kw, neg_kw, metadata

def search_destinations(query: str, filters: Dict[str, Any]) -> List:
    """
    Public API for destination search
    
    Args:
        query: Search query
        filters: Search filters
        
    Returns:
        List of destinations sorted by relevance
    """
    engine = get_recommendation_engine()
    return engine.search_destinations(query, filters)

def calculate_destination_score(destination) -> Dict[str, float]:
    """
    Public API for destination scoring
    
    Args:
        destination: Destination model instance
        
    Returns:
        Dict with various scores
    """
    engine = get_recommendation_engine()
    return engine.calculate_destination_score(destination)


def get_similar_destinations(destination, limit: int = 4) -> List:
    """
    Gợi ý địa điểm tương tự dựa trên:
    - Cùng loại hình du lịch
    - Cùng khu vực
    - Mức giá tương đương
    - Điểm đánh giá cao
    
    Args:
        destination: Destination hiện tại
        limit: Số lượng gợi ý tối đa
        
    Returns:
        List các destination tương tự
    """
    from .models import Destination
    from django.db.models import Q, F, Value, FloatField
    from django.db.models.functions import Abs
    
    # Tìm các địa điểm khác (không phải địa điểm hiện tại)
    queryset = Destination.objects.select_related('recommendation').exclude(id=destination.id)
    
    similar = []
    
    # 1. Cùng loại hình du lịch (ưu tiên cao nhất)
    # travel_type là ManyToManyField, cần lấy danh sách IDs
    travel_type_ids = list(destination.travel_type.values_list('id', flat=True))
    if travel_type_ids:
        same_type = queryset.filter(travel_type__in=travel_type_ids).distinct()
    else:
        same_type = queryset.none()
    
    # 2. Cùng khu vực
    same_location = queryset.filter(location=destination.location)
    
    # Gộp và tính điểm tương đồng
    candidates = {}
    
    # Điểm cho cùng loại hình
    for dest in same_type[:10]:
        candidates[dest.id] = {'dest': dest, 'score': 50}
    
    # Điểm cho cùng khu vực
    for dest in same_location[:10]:
        if dest.id in candidates:
            candidates[dest.id]['score'] += 40
        else:
            candidates[dest.id] = {'dest': dest, 'score': 40}
    
    # Thêm điểm recommendation
    for dest_id, data in candidates.items():
        dest = data['dest']
        if hasattr(dest, 'recommendation') and dest.recommendation:
            data['score'] += dest.recommendation.overall_score * 0.1
    
    # Sắp xếp theo điểm và lấy top
    sorted_candidates = sorted(candidates.values(), key=lambda x: x['score'], reverse=True)
    
    return [c['dest'] for c in sorted_candidates[:limit]]


def get_personalized_recommendations(user_preferences: Dict, limit: int = 6) -> List:
    """
    Gợi ý cá nhân hóa dựa trên sở thích người dùng
    
    Args:
        user_preferences: Dict chứa sở thích
            - travel_types: List loại hình yêu thích
            - locations: List địa điểm yêu thích
            - max_price: Ngân sách tối đa
        limit: Số lượng gợi ý
        
    Returns:
        List các destination phù hợp
    """
    from .models import Destination
    from django.db.models import Q
    
    queryset = Destination.objects.select_related('recommendation')
    
    # Filter theo sở thích
    filters = Q()
    
    travel_types = user_preferences.get('travel_types', [])
    if travel_types:
        type_filter = Q()
        for t in travel_types:
            type_filter |= Q(travel_type__icontains=t)
        filters &= type_filter
    
    locations = user_preferences.get('locations', [])
    if locations:
        loc_filter = Q()
        for loc in locations:
            loc_filter |= Q(location__icontains=loc)
        filters &= loc_filter
    
    max_price = user_preferences.get('max_price')
    # Bỏ filter theo giá vì đã chuyển sang entrance_fee
    
    if filters:
        queryset = queryset.filter(filters)
    
    # Sắp xếp theo điểm gợi ý
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])


def get_seasonal_recommendations(month: int = None, limit: int = 6) -> List:
    """
    Gợi ý theo mùa/thời điểm trong năm
    
    Args:
        month: Tháng (1-12), mặc định là tháng hiện tại
        limit: Số lượng gợi ý
        
    Returns:
        List các destination phù hợp với mùa
    """
    from .models import Destination
    from datetime import datetime
    
    if month is None:
        month = datetime.now().month
    
    queryset = Destination.objects.select_related('recommendation')
    
    # Gợi ý theo mùa ở Việt Nam
    if month in [12, 1, 2]:  # Mùa đông - Tết
        # Ưu tiên: Miền Bắc (hoa đào), Đà Lạt (hoa mai anh đào)
        queryset = queryset.filter(
            Q(location__icontains='Hà Nội') |
            Q(location__icontains='Sa Pa') |
            Q(location__icontains='Đà Lạt') |
            Q(travel_type__icontains='Núi')
        )
    elif month in [3, 4, 5]:  # Mùa xuân
        # Ưu tiên: Miền Trung, biển
        queryset = queryset.filter(
            Q(location__icontains='Đà Nẵng') |
            Q(location__icontains='Huế') |
            Q(location__icontains='Hội An') |
            Q(travel_type__icontains='Biển')
        )
    elif month in [6, 7, 8]:  # Mùa hè
        # Ưu tiên: Biển, đảo
        queryset = queryset.filter(
            Q(location__icontains='Nha Trang') |
            Q(location__icontains='Phú Quốc') |
            Q(location__icontains='Hạ Long') |
            Q(travel_type__icontains='Biển')
        )
    else:  # Mùa thu (9, 10, 11)
        # Ưu tiên: Tây Nguyên, miền Bắc
        queryset = queryset.filter(
            Q(location__icontains='Đà Lạt') |
            Q(location__icontains='Hà Nội') |
            Q(location__icontains='Ninh Bình') |
            Q(travel_type__icontains='Núi')
        )
    
    # Sắp xếp theo điểm
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])


def get_personalized_for_user(user, limit: int = 6) -> List:
    """
    Gợi ý cá nhân hóa dựa trên sở thích đã lưu của user
    
    Args:
        user: User object
        limit: Số lượng gợi ý
        
    Returns:
        List các destination phù hợp với sở thích user
    """
    from .models import Destination
    from users.models import TravelPreference
    from django.db.models import Q
    
    # Lấy sở thích của user
    preferences = TravelPreference.objects.filter(user=user)
    
    if not preferences.exists():
        # Nếu chưa có sở thích, trả về top destinations
        return list(
            Destination.objects.select_related('recommendation')
            .order_by('-recommendation__overall_score')[:limit]
        )
    
    # Lấy danh sách travel_type và location yêu thích
    travel_types = list(preferences.values_list('travel_type', flat=True).distinct())
    locations = list(preferences.values_list('location', flat=True).distinct())
    
    # Build query
    queryset = Destination.objects.select_related('recommendation')
    
    filters = Q()
    
    # Filter theo loại hình yêu thích
    if travel_types:
        type_filter = Q()
        for t in travel_types:
            if t:
                type_filter |= Q(travel_type__icontains=t)
        if type_filter:
            filters |= type_filter
    
    # Filter theo địa điểm yêu thích
    if locations:
        loc_filter = Q()
        for loc in locations:
            if loc:
                loc_filter |= Q(location__icontains=loc)
        if loc_filter:
            filters |= loc_filter
    
    if filters:
        queryset = queryset.filter(filters)
    
    # Sắp xếp theo điểm gợi ý
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])
