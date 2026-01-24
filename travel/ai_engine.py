"""
Unified AI Engine for WebDuLich
Gá»™p sentiment analysis vÃ  recommendation engine thÃ nh 1 module duy nháº¥t

Features:
- PhoBERT sentiment analysis vá»›i fallback rule-based
- Enhanced rule-based vá»›i JSON keywords
- Aspect-based sentiment analysis
- Negation, intensifier, downtoner handling
- Sarcasm detection
- Recommendation scoring algorithm
- Caching system tÃ­ch há»£p
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

# Tá»« phá»§ Ä‘á»‹nh (negation)
NEGATION_WORDS = [
    'khÃ´ng', 'ko', 'k', 'cháº³ng', 'cháº£', 'Ä‘á»«ng', 'chÆ°a',
    'khÃ´ng pháº£i', 'khÃ´ng há»', 'khÃ´ng bao giá»', 'cháº³ng bao giá»',
    'khÃ´ng cÃ²n', 'cháº³ng cÃ²n', 'khÃ´ng thá»ƒ', 'chÆ°a bao giá»',
    'chÆ°a tá»«ng', 'khÃ´ng Ä‘Æ°á»£c', 'cháº³ng Ä‘Æ°á»£c', 'khÃ´ng cÃ³',
    'thiáº¿u', 'máº¥t', 'háº¿t', 'khÃ´ng tháº¥y', 'cháº³ng tháº¥y'
]

# Tá»« giáº£m nháº¹ (downtoner)
DOWNTONERS = {
    'hÆ¡i': 0.6,
    'khÃ¡': 0.6,
    'tÆ°Æ¡ng Ä‘á»‘i': 0.6,
    'cÅ©ng': 0.6,
    'hÆ¡i hÆ¡i': 0.5
}

# Tá»« tÄƒng cÆ°á»ng (intensifier)
INTENSIFIERS_STRONG = {
    'cá»±c ká»³': 1.4,
    'cá»±c kÃ¬': 1.4,
    'siÃªu': 1.4,
    'vÃ´ cÃ¹ng': 1.4,
    'cá»±c': 1.4,
    'cá»±c luÃ´n': 1.4
}

INTENSIFIERS_MEDIUM = {
    'ráº¥t': 1.25,
    'quÃ¡': 1.25,
    'tháº­t sá»±': 1.25,
    'thá»±c sá»±': 1.25,
    'ráº¥t lÃ ': 1.25,
    'hoÃ n toÃ n': 1.25,
    'tuyá»‡t Ä‘á»‘i': 1.25
}

# Merge all intensifiers
INTENSIFIERS = {**INTENSIFIERS_STRONG, **INTENSIFIERS_MEDIUM}

# Sarcasm indicators
SARCASM_INDICATORS = [
    'ha', 'haha', 'hihi', 'hehe',
    ':))', '=))', 'ðŸ™‚ðŸ™‚', 'ðŸ˜', 'ðŸ˜…',
    'nhá»‰', 'nhá»ƒ', 'nhá»Ÿ', 'nhÃ©'
]

# Contrast words - pháº§n sau thÆ°á»ng quan trá»ng hÆ¡n
CONTRAST_WORDS = [
    'nhÆ°ng', 'tuy nhiÃªn', 'tuy', 'máº·c dÃ¹', 'dÃ¹', 'song',
    'tháº¿ nhÆ°ng', 'nhÆ°ng mÃ ', 'tuy váº­y', 'dÃ¹ váº­y', 'dÃ¹ sao'
]

# Negative behavior patterns - chá»‰ bÃ¡o tiÃªu cá»±c máº¡nh
NEGATIVE_BEHAVIOR_PATTERNS = [
    ('khÃ´ng', 'quay láº¡i'),
    ('khÃ´ng', 'recommend'),
    ('khÃ´ng', 'giá»›i thiá»‡u'),
    ('khÃ´ng', 'Ä‘á» xuáº¥t'),
    ('khÃ´ng', 'nÃªn Ä‘i'),
    ('khÃ´ng', 'Ä‘Ã¡ng'),
    ('cháº³ng', 'quay láº¡i'),
    ('sáº½ khÃ´ng', 'quay láº¡i'),
    ('láº§n sau', 'khÃ´ng'),
    ('khÃ´ng bao giá»', 'quay láº¡i'),
    ('khÃ´ng bao giá»', 'Ä‘áº¿n'),
    ('tháº¥t vá»ng', 'hoÃ n toÃ n'),
    ('hoÃ n toÃ n', 'tháº¥t vá»ng'),
]

# Stopwords tiáº¿ng Viá»‡t
STOPWORDS = [
    'lÃ ', 'cá»§a', 'vÃ ', 'cÃ³', 'Ä‘Æ°á»£c', 'trong', 'vá»›i', 'cho', 'tá»«', 'nÃ y', 'Ä‘Ã³',
    'má»™t', 'cÃ¡c', 'nhá»¯ng', 'Ä‘á»ƒ', 'khi', 'Ä‘Ã£', 'sáº½', 'bá»‹', 'náº¿u', 'nhÆ°', 'thÃ¬',
    'mÃ ', 'hay', 'hoáº·c', 'nhÆ°ng', 'vÃ¬', 'nÃªn', 'láº¡i', 'cÃ²n', 'Ä‘ang'
]


# ==================== TEXT NORMALIZATION ====================

class TextNormalizer:
    """Text normalization vá»›i teencode vÃ  slang mapping"""
    
    def __init__(self):
        self.slang_map = SENTIMENT_DATA.get('slang_map', {})
        # Sort by length (longest first) for proper multi-word matching
        self.sorted_slang = sorted(self.slang_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    def normalize(self, text: str) -> str:
        """
        Chuáº©n hÃ³a text:
        - Lowercase
        - Map teencode/slang (longest-first matching)
        - Giá»¯ dáº¥u tiáº¿ng Viá»‡t
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
        # Keep Vietnamese characters and basic punctuation
        text = re.sub(r'[^\w\sÃ Ã¡áº¡áº£Ã£Ã¢áº§áº¥áº­áº©áº«Äƒáº±áº¯áº·áº³áºµÃ¨Ã©áº¹áº»áº½Ãªá»áº¿á»‡á»ƒá»…Ã¬Ã­á»‹á»‰Ä©Ã²Ã³á»á»ÃµÃ´á»“á»‘á»™á»•á»—Æ¡á»á»›á»£á»Ÿá»¡Ã¹Ãºá»¥á»§Å©Æ°á»«á»©á»±á»­á»¯á»³Ã½á»µá»·á»¹Ä‘.,!?]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if t]


# ==================== SENTIMENT ANALYZER ====================

class SentimentAnalyzer:
    """
    Enhanced Sentiment Analyzer vá»›i PhoBERT + Advanced Rule-based fallback
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
                model_name = finetuned_path
                logger.info(f"âœ… Using FINE-TUNED model from: {finetuned_path}")
            else:
                # Fallback to original model
                model_name = "wonrax/phobert-base-vietnamese-sentiment"
                logger.info(f"âš ï¸  Fine-tuned model not found, using original: {model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            
            self.model_loaded = True
            logger.info(f"PhoBERT model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load PhoBERT model: {e}")
            logger.warning("Will use rule-based sentiment analysis")
            self.model_loaded = False
    
    def analyze(self, text: str) -> Tuple[float, List[str], List[str], Dict[str, Any]]:
        """
        PhÃ¢n tÃ­ch sentiment cá»§a text
        
        Returns:
            tuple: (sentiment_score, positive_keywords, negative_keywords, metadata)
                - sentiment_score: float tá»« -1 Ä‘áº¿n 1
                - positive_keywords: list tá»« khÃ³a tÃ­ch cá»±c
                - negative_keywords: list tá»« khÃ³a tiÃªu cá»±c
                - metadata: dict chá»©a thÃ´ng tin phÃ¢n tÃ­ch (aspects, sarcasm_risk, etc.)
        """
        if not text or not text.strip():
            return 0.0, [], [], {}
        
        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        cache_key = f'sentiment_v2:{text_hash}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Load model náº¿u chÆ°a load
        if not self.model_loaded:
            self.load_model()
        
        # Sá»­ dá»¥ng PhoBERT náº¿u cÃ³, fallback vá» rule-based
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
        - PhoBERT chá»‰ win khi confidence cao
        - Rule-based win khi cÃ³ keyword máº¡nh hoáº·c PhoBERT khÃ´ng tá»± tin
        - Combine weighted khi cáº£ hai Ä‘á»u cÃ³ giÃ¡ trá»‹
        """
        try:
            # 1. Get rule-based analysis first (always needed for keywords/aspects)
            rule_score, pos_keywords, neg_keywords, metadata = self._rule_based_analysis(text)
            
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
        
        Chiáº¿n lÆ°á»£c: PhoBERT lÃ  PRIMARY, Rule-based lÃ  CALIBRATION
        
        NguyÃªn táº¯c:
        1. PhoBERT luÃ´n Ä‘Ã³ng vai trÃ² chÃ­nh (55-70% weight)
        2. Rule-based dÃ¹ng Ä‘á»ƒ calibrate vÃ  xá»­ lÃ½ edge cases
        3. Mixed sentiment â†’ kÃ©o vá» neutral dá»±a trÃªn PhoBERT
        4. Neutral soft words â†’ giá»¯ gáº§n neutral (threshold 0.2)
        
        Returns:
            (final_score, method_name)
        """
        total_keywords = num_pos_keywords + num_neg_keywords
        
        # === CASE 1: Mixed sentiment (cÃ³ cáº£ pos vÃ  neg keywords) ===
        # ÄÃ¢y lÃ  case quan trá»ng nháº¥t - cáº§n kÃ©o vá» neutral
        if num_pos_keywords > 0 and num_neg_keywords > 0:
            # PhoBERT quyáº¿t Ä‘á»‹nh hÆ°á»›ng, nhÆ°ng dampen máº¡nh vá» neutral
            balance = min(num_pos_keywords, num_neg_keywords) / max(num_pos_keywords, num_neg_keywords)
            
            # Damping máº¡nh hÆ¡n khi balance cao (keywords cÃ¢n báº±ng)
            damping = 0.40 + (balance * 0.30)
            
            # PhoBERT 60%, rule 40%
            combined = 0.60 * phobert_score + 0.40 * rule_score
            dampened = combined * (1 - damping)
            return max(-1.0, min(1.0, dampened)), "phobert_mixed_neutral_pull"
        
        # === CASE 2: Chá»‰ cÃ³ neutral soft keywords (ok, Ä‘Æ°á»£c, táº¡m, á»•n) ===
        # Rule score tháº¥p (<0.12) thÆ°á»ng lÃ  neutral soft only
        if total_keywords > 0 and abs(rule_score) < 0.12:
            # Neutral soft â†’ kÃ©o máº¡nh vá» neutral
            # PhoBERT 40%, rule 60%, rá»“i dampen máº¡nh
            combined = 0.40 * phobert_score + 0.60 * rule_score
            dampened = combined * 0.35  # Giá»¯ 35% magnitude â†’ gáº§n neutral
            return max(-1.0, min(1.0, dampened)), "phobert_neutral_soft_strong_pull"
        
        # === CASE 3: Weak positive keywords (0.12 <= rule < 0.25) ===
        # CÃ³ keywords nhÆ°ng yáº¿u â†’ dampen vá» neutral hÆ¡n
        if total_keywords > 0 and 0.12 <= abs(rule_score) < 0.25:
            # PhoBERT 50%, rule 50%, dampen nháº¹
            combined = 0.50 * phobert_score + 0.50 * rule_score
            dampened = combined * 0.6  # Giá»¯ 60%
            return max(-1.0, min(1.0, dampened)), "phobert_weak_signal_calibrated"
        
        # === CASE 4: PhoBERT confidence tháº¥p (<0.20) ===
        if confidence < 0.20:
            # PhoBERT khÃ´ng cháº¯c â†’ mix vá»›i rule nhiá»u hÆ¡n
            # PhoBERT 45%, rule 55%
            final = 0.45 * phobert_score + 0.55 * rule_score
            return max(-1.0, min(1.0, final)), "phobert_low_conf_rule_assist"
        
        # === CASE 5: PhoBERT high confidence (>0.45) ===
        if confidence >= 0.45:
            # PhoBERT ráº¥t tá»± tin â†’ 70% PhoBERT, 30% rule
            final = 0.70 * phobert_score + 0.30 * rule_score
            return max(-1.0, min(1.0, final)), "phobert_dominant_high_conf"
        
        # === CASE 6: KhÃ´ng cÃ³ keywords â†’ PhoBERT quyáº¿t Ä‘á»‹nh ===
        if total_keywords == 0:
            # KhÃ´ng cÃ³ domain signal â†’ tin PhoBERT nhÆ°ng dampen
            dampened = phobert_score * 0.70
            return max(-1.0, min(1.0, dampened)), "phobert_only_no_keywords"
        
        # === CASE 7: PhoBERT vÃ  Rule Ä‘á»“ng thuáº­n (cÃ¹ng dáº¥u, cÃ¹ng máº¡nh) ===
        if (phobert_score > 0.2 and rule_score > 0.2) or (phobert_score < -0.2 and rule_score < -0.2):
            # Cáº£ hai Ä‘á»“ng Ã½ máº¡nh â†’ PhoBERT lead, boost
            # PhoBERT 65%, rule 35%
            final = 0.65 * phobert_score + 0.35 * rule_score
            
            # Boost khi Ä‘á»“ng thuáº­n ráº¥t máº¡nh
            if abs(phobert_score) > 0.5 and abs(rule_score) > 0.5:
                final = final * 1.15
            
            return max(-1.0, min(1.0, final)), "phobert_rule_strong_agreement"
        
        # === CASE 8: PhoBERT vÃ  Rule conflict (khÃ¡c dáº¥u) ===
        if (phobert_score > 0.15 and rule_score < -0.15) or (phobert_score < -0.15 and rule_score > 0.15):
            # Conflict â†’ PhoBERT lead nhÆ°ng dampen máº¡nh
            # PhoBERT 55%, rule 45%
            final = 0.55 * phobert_score + 0.45 * rule_score
            final = final * 0.65  # Dampen 35%
            return max(-1.0, min(1.0, final)), "phobert_rule_conflict_dampen"
        
        # === DEFAULT: Balanced mix vá»›i PhoBERT lead ===
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
        # "Ä‘áº¹p nhÆ°ng Ä‘áº¯t" â†’ pháº§n sau (Ä‘áº¯t) quan trá»ng hÆ¡n
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
                
                # Check if tokens match
                if ' '.join(tokens[i:i+keyword_len]) == keyword:
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
                            pos_keywords.append(f"khÃ´ng {keyword}")
                        else:
                            pos_keywords.append(keyword)
                    elif modified_score < 0:
                        if is_negated and base_score > 0:
                            neg_keywords.append(f"khÃ´ng {keyword}")
                        else:
                            neg_keywords.append(keyword)
                    
                    # Track aspect
                    aspect = self._get_aspect(keyword)
                    if aspect:
                        aspect_scores[aspect] += modified_score
        
        # Process neutral_soft words as weak positive (ok, á»•n, Ä‘Æ°á»£c, táº¡m...)
        # Score tháº¥p (0.10) Ä‘á»ƒ khÃ´ng lÃ m cÃ¢u mixed thÃ nh positive
        for i, token in enumerate(tokens):
            if i in matched_positions:
                continue
            if token in self.neutral_soft:
                # Neutral soft words = very weak positive (0.05)
                # Gáº§n nhÆ° neutral, chá»‰ hÆ¡i positive má»™t chÃºt
                soft_score = 0.05
                
                # Check for negation before neutral_soft
                window_start = max(0, i - 3)
                window = tokens[window_start:i]
                is_negated = any(t in NEGATION_WORDS for t in window)
                
                if is_negated:
                    # "khÃ´ng ok" = weak negative
                    sentence_score -= 0.05
                    neg_keywords.append(f"khÃ´ng {token}")
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
            # Special case: "khÃ´ng tá»‡" should be weak positive (but not too strong)
            if base_score < 0:
                # "khÃ´ng tá»‡" -> weak positive, capped at 0.20
                modified_score = min(abs(base_score) * 0.5, 0.20)
            else:
                # "khÃ´ng Ä‘áº¹p" -> negative
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
        """TÃ¡ch vÄƒn báº£n thÃ nh cÃ¡c cÃ¢u"""
        sentences = re.split(r'[.!?;,\n]', text)
        return [s.strip() for s in sentences if s.strip()]


# ==================== RECOMMENDATION ENGINE ====================

class RecommendationEngine:
    """
    Recommendation Engine cho destinations
    Sá»­ dá»¥ng Universal Scoring Engine cho Ä‘iá»ƒm gá»£i Ã½
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        # Import scoring engine
        from .scoring_engine import get_scoring_engine
        self.scoring_engine = get_scoring_engine()
    
    def search_destinations(self, query: str, filters: Dict[str, Any]) -> List:
        """
        TÃ¬m kiáº¿m destinations vá»›i AI scoring
        
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
        TÃ­nh toÃ¡n Ä‘iá»ƒm sá»‘ tá»•ng há»£p cho destination
        Sá»­ dá»¥ng Universal Scoring Engine
        
        Returns:
            Dict vá»›i cÃ¡c scores: overall, review, sentiment, popularity
        """
        return self.scoring_engine.calculate_score(destination)
    
    def _calculate_relevance_score(self, destination, query: str, filters: Dict) -> float:
        """TÃ­nh Ä‘iá»ƒm relevance cho search results"""
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
        """TÃ­nh price competitiveness score dá»±a trÃªn phÃ­ vÃ o cá»•ng"""
        if not destination.entrance_fee:
            return 10.0  # Miá»…n phÃ­ = Ä‘iá»ƒm cao nháº¥t
        
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
        # Short review with weak positive â†’ boost slightly
        if any(kw in ['ok', 'á»•n', 'Ä‘Æ°á»£c', 'táº¡m'] for kw in pos_kw):
            score = min(score * 1.5, 0.25)  # Boost to weak positive
            metadata['post_processing'] = 'short_review_boost'
    
    # 2. Rating-based calibration (optional, if rating is provided)
    if rating is not None:
        original_score = score
        
        if rating == 5 and score < 0.5:
            # Rating 5 should be strong positive
            score = max(score, 0.6)
            metadata['calibrated'] = True
            metadata['calibration_reason'] = f'rating_5_boost (from {original_score:.3f})'
        
        elif rating == 4 and score < 0.15:
            # Rating 4 should be at least weak positive
            score = max(score, 0.20)
            metadata['calibrated'] = True
            metadata['calibration_reason'] = f'rating_4_boost (from {original_score:.3f})'
        
        elif rating == 1 and score > -0.5:
            # Rating 1 should be strong negative
            score = min(score, -0.6)
            metadata['calibrated'] = True
            metadata['calibration_reason'] = f'rating_1_adjust (from {original_score:.3f})'
    
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
    Gá»£i Ã½ Ä‘á»‹a Ä‘iá»ƒm tÆ°Æ¡ng tá»± dá»±a trÃªn:
    - CÃ¹ng loáº¡i hÃ¬nh du lá»‹ch
    - CÃ¹ng khu vá»±c
    - Má»©c giÃ¡ tÆ°Æ¡ng Ä‘Æ°Æ¡ng
    - Äiá»ƒm Ä‘Ã¡nh giÃ¡ cao
    
    Args:
        destination: Destination hiá»‡n táº¡i
        limit: Sá»‘ lÆ°á»£ng gá»£i Ã½ tá»‘i Ä‘a
        
    Returns:
        List cÃ¡c destination tÆ°Æ¡ng tá»±
    """
    from .models import Destination
    from django.db.models import Q, F, Value, FloatField
    from django.db.models.functions import Abs
    
    # TÃ¬m cÃ¡c Ä‘á»‹a Ä‘iá»ƒm khÃ¡c (khÃ´ng pháº£i Ä‘á»‹a Ä‘iá»ƒm hiá»‡n táº¡i)
    queryset = Destination.objects.select_related('recommendation').exclude(id=destination.id)
    
    similar = []
    
    # 1. CÃ¹ng loáº¡i hÃ¬nh du lá»‹ch (Æ°u tiÃªn cao nháº¥t)
    # Lấy danh sách travel_type IDs của destination hiện tại (ManyToMany)
    current_type_ids = list(destination.travel_type.values_list('id', flat=True))
    
    # Tìm các địa điểm có cùng travel_type
    if current_type_ids:
        same_type = queryset.filter(travel_type__id__in=current_type_ids).distinct()
    else:
        same_type = queryset.none()
    
    # 2. CÃ¹ng khu vá»±c
    same_location = queryset.filter(location=destination.location)
    
    # Gá»™p vÃ  tÃ­nh Ä‘iá»ƒm tÆ°Æ¡ng Ä‘á»“ng
    candidates = {}
    
    # Äiá»ƒm cho cÃ¹ng loáº¡i hÃ¬nh
    for dest in same_type[:10]:
        candidates[dest.id] = {'dest': dest, 'score': 50}
    
    # Äiá»ƒm cho cÃ¹ng khu vá»±c
    for dest in same_location[:10]:
        if dest.id in candidates:
            candidates[dest.id]['score'] += 40
        else:
            candidates[dest.id] = {'dest': dest, 'score': 40}
    
    # ThÃªm Ä‘iá»ƒm recommendation
    for dest_id, data in candidates.items():
        dest = data['dest']
        if hasattr(dest, 'recommendation') and dest.recommendation:
            data['score'] += dest.recommendation.overall_score * 0.1
    
    # Sáº¯p xáº¿p theo Ä‘iá»ƒm vÃ  láº¥y top
    sorted_candidates = sorted(candidates.values(), key=lambda x: x['score'], reverse=True)
    
    return [c['dest'] for c in sorted_candidates[:limit]]


def get_personalized_recommendations(user_preferences: Dict, limit: int = 6) -> List:
    """
    Gá»£i Ã½ cÃ¡ nhÃ¢n hÃ³a dá»±a trÃªn sá»Ÿ thÃ­ch ngÆ°á»i dÃ¹ng
    
    Args:
        user_preferences: Dict chá»©a sá»Ÿ thÃ­ch
            - travel_types: List loáº¡i hÃ¬nh yÃªu thÃ­ch
            - locations: List Ä‘á»‹a Ä‘iá»ƒm yÃªu thÃ­ch
            - max_price: NgÃ¢n sÃ¡ch tá»‘i Ä‘a
        limit: Sá»‘ lÆ°á»£ng gá»£i Ã½
        
    Returns:
        List cÃ¡c destination phÃ¹ há»£p
    """
    from .models import Destination
    from django.db.models import Q
    
    queryset = Destination.objects.select_related('recommendation')
    
    # Filter theo sá»Ÿ thÃ­ch
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
    # Bá» filter theo giÃ¡ vÃ¬ Ä‘Ã£ chuyá»ƒn sang entrance_fee
    
    if filters:
        queryset = queryset.filter(filters)
    
    # Sáº¯p xáº¿p theo Ä‘iá»ƒm gá»£i Ã½
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])


def get_seasonal_recommendations(month: int = None, limit: int = 6) -> List:
    """
    Gá»£i Ã½ theo mÃ¹a/thá»i Ä‘iá»ƒm trong nÄƒm
    
    Args:
        month: ThÃ¡ng (1-12), máº·c Ä‘á»‹nh lÃ  thÃ¡ng hiá»‡n táº¡i
        limit: Sá»‘ lÆ°á»£ng gá»£i Ã½
        
    Returns:
        List cÃ¡c destination phÃ¹ há»£p vá»›i mÃ¹a
    """
    from .models import Destination
    from datetime import datetime
    
    if month is None:
        month = datetime.now().month
    
    queryset = Destination.objects.select_related('recommendation')
    
    # Gá»£i Ã½ theo mÃ¹a á»Ÿ Viá»‡t Nam
    if month in [12, 1, 2]:  # MÃ¹a Ä‘Ã´ng - Táº¿t
        # Æ¯u tiÃªn: Miá»n Báº¯c (hoa Ä‘Ã o), ÄÃ  Láº¡t (hoa mai anh Ä‘Ã o)
        queryset = queryset.filter(
            Q(location__icontains='HÃ  Ná»™i') |
            Q(location__icontains='Sa Pa') |
            Q(location__icontains='ÄÃ  Láº¡t') |
            Q(travel_type__icontains='NÃºi')
        )
    elif month in [3, 4, 5]:  # MÃ¹a xuÃ¢n
        # Æ¯u tiÃªn: Miá»n Trung, biá»ƒn
        queryset = queryset.filter(
            Q(location__icontains='ÄÃ  Náºµng') |
            Q(location__icontains='Huáº¿') |
            Q(location__icontains='Há»™i An') |
            Q(travel_type__icontains='Biá»ƒn')
        )
    elif month in [6, 7, 8]:  # MÃ¹a hÃ¨
        # Æ¯u tiÃªn: Biá»ƒn, Ä‘áº£o
        queryset = queryset.filter(
            Q(location__icontains='Nha Trang') |
            Q(location__icontains='PhÃº Quá»‘c') |
            Q(location__icontains='Háº¡ Long') |
            Q(travel_type__icontains='Biá»ƒn')
        )
    else:  # MÃ¹a thu (9, 10, 11)
        # Æ¯u tiÃªn: TÃ¢y NguyÃªn, miá»n Báº¯c
        queryset = queryset.filter(
            Q(location__icontains='ÄÃ  Láº¡t') |
            Q(location__icontains='HÃ  Ná»™i') |
            Q(location__icontains='Ninh BÃ¬nh') |
            Q(travel_type__icontains='NÃºi')
        )
    
    # Sáº¯p xáº¿p theo Ä‘iá»ƒm
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])


def get_personalized_for_user(user, limit: int = 6) -> List:
    """
    Gá»£i Ã½ cÃ¡ nhÃ¢n hÃ³a dá»±a trÃªn sá»Ÿ thÃ­ch Ä‘Ã£ lÆ°u cá»§a user
    
    Args:
        user: User object
        limit: Sá»‘ lÆ°á»£ng gá»£i Ã½
        
    Returns:
        List cÃ¡c destination phÃ¹ há»£p vá»›i sá»Ÿ thÃ­ch user
    """
    from .models import Destination
    from users.models import TravelPreference
    from django.db.models import Q
    
    # Láº¥y sá»Ÿ thÃ­ch cá»§a user
    preferences = TravelPreference.objects.filter(user=user)
    
    if not preferences.exists():
        # Náº¿u chÆ°a cÃ³ sá»Ÿ thÃ­ch, tráº£ vá» top destinations
        return list(
            Destination.objects.select_related('recommendation')
            .order_by('-recommendation__overall_score')[:limit]
        )
    
    # Láº¥y danh sÃ¡ch travel_type vÃ  location yÃªu thÃ­ch
    travel_types = list(preferences.values_list('travel_type', flat=True).distinct())
    locations = list(preferences.values_list('location', flat=True).distinct())
    
    # Build query
    queryset = Destination.objects.select_related('recommendation')
    
    filters = Q()
    
    # Filter theo loáº¡i hÃ¬nh yÃªu thÃ­ch
    if travel_types:
        type_filter = Q()
        for t in travel_types:
            if t:
                type_filter |= Q(travel_type__icontains=t)
        if type_filter:
            filters |= type_filter
    
    # Filter theo Ä‘á»‹a Ä‘iá»ƒm yÃªu thÃ­ch
    if locations:
        loc_filter = Q()
        for loc in locations:
            if loc:
                loc_filter |= Q(location__icontains=loc)
        if loc_filter:
            filters |= loc_filter
    
    if filters:
        queryset = queryset.filter(filters)
    
    # Sáº¯p xáº¿p theo Ä‘iá»ƒm gá»£i Ã½
    queryset = queryset.order_by('-recommendation__overall_score')
    
    return list(queryset[:limit])

