"""
AI-powered Sentiment Analysis using PhoBERT
Phân tích cảm xúc bằng AI thật cho tiếng Việt
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Sentiment Analyzer sử dụng PhoBERT
    
    Model: vinai/phobert-base-v2 (fine-tuned for sentiment analysis)
    Output: 
        - score: -1 (tiêu cực) đến 1 (tích cực)
        - confidence: độ tin cậy 0-1
        - label: 'positive', 'negative', 'neutral'
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_loaded = False
        
    def load_model(self):
        """Load PhoBERT model (lazy loading)"""
        if self.model_loaded:
            return
        
        try:
            logger.info("Loading PhoBERT sentiment model...")
            
            # Sử dụng model đã fine-tune cho sentiment (nếu có)
            # Hoặc dùng base model với custom classification head
            model_name = "wonrax/phobert-base-vietnamese-sentiment"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            
            self.model_loaded = True
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load PhoBERT model: {e}")
            logger.warning("Falling back to rule-based sentiment analysis")
            self.model_loaded = False
    
    def analyze(self, text):
        """
        Phân tích sentiment của text (with caching)
        
        Args:
            text (str): Text cần phân tích
            
        Returns:
            tuple: (sentiment_score, confidence, label, keywords)
                - sentiment_score: float từ -1 đến 1
                - confidence: float từ 0 đến 1
                - label: str ('positive', 'negative', 'neutral')
                - keywords: list các từ khóa quan trọng
        """
        if not text or not text.strip():
            return 0.0, 0.0, 'neutral', []
        
        # Check cache first
        import hashlib
        from django.core.cache import cache
        from django.conf import settings
        
        text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        cache_key = f'sentiment:{text_hash}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Sentiment cache HIT for: {text[:50]}...")
            return cached_result
        
        logger.debug(f"Sentiment cache MISS for: {text[:50]}...")
        
        # Load model nếu chưa load
        if not self.model_loaded:
            self.load_model()
        
        # Nếu model không load được, fallback về rule-based
        if not self.model_loaded:
            result = self._fallback_analysis(text)
            cache.set(cache_key, result, settings.CACHE_TTL.get('sentiment', 86400))
            return result
        
        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
            
            # Parse results
            probs = probabilities[0].cpu().numpy()
            
            # Model output: [negative, neutral, positive] hoặc [negative, positive]
            if len(probs) == 3:
                neg_prob, neu_prob, pos_prob = probs
                
                # Tính sentiment score (-1 đến 1)
                sentiment_score = pos_prob - neg_prob
                
                # Xác định label
                max_prob = max(probs)
                if max_prob == pos_prob:
                    label = 'positive'
                elif max_prob == neg_prob:
                    label = 'negative'
                else:
                    label = 'neutral'
                
                confidence = float(max_prob)
                
            else:  # Binary classification
                neg_prob, pos_prob = probs
                sentiment_score = pos_prob - neg_prob
                label = 'positive' if sentiment_score > 0 else 'negative'
                confidence = float(max(probs))
            
            # Extract keywords (đơn giản hóa)
            keywords = self._extract_keywords(text, label)
            
            result = (float(sentiment_score), confidence, label, keywords)
            
            # Cache the result
            cache.set(cache_key, result, settings.CACHE_TTL.get('sentiment', 86400))
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            result = self._fallback_analysis(text)
            cache.set(cache_key, result, settings.CACHE_TTL.get('sentiment', 86400))
            return result
    
    def _extract_keywords(self, text, sentiment_label):
        """
        Trích xuất từ khóa quan trọng từ text
        Sử dụng underthesea để word segmentation
        """
        try:
            from underthesea import word_tokenize
            
            # Word segmentation
            words = word_tokenize(text, format="text").split()
            
            # Từ điển từ khóa cơ bản
            positive_words = [
                'đẹp', 'tốt', 'tuyệt', 'ngon', 'sạch', 'thân_thiện', 
                'chuyên_nghiệp', 'rẻ', 'thoải_mái', 'yên_tĩnh', 'tiện_nghi',
                'sang_trọng', 'ấn_tượng', 'hài_lòng', 'recommend', 'nên'
            ]
            
            negative_words = [
                'tệ', 'xấu', 'bẩn', 'đắt', 'kém', 'thất_vọng', 'tránh',
                'lãng_phí', 'ồn_ào', 'chật_chội', 'cũ_kỹ', 'hư_hỏng',
                'chán', 'nguy_hiểm', 'mệt', 'đông_đúc'
            ]
            
            # Lọc keywords theo sentiment
            keywords = []
            if sentiment_label == 'positive':
                keywords = [w for w in words if w.lower() in positive_words]
            elif sentiment_label == 'negative':
                keywords = [w for w in words if w.lower() in negative_words]
            
            return keywords[:5]  # Top 5 keywords
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []
    
    def _fallback_analysis(self, text):
        """
        Fallback về rule-based analysis nếu AI model không hoạt động
        """
        from .ai_module import analyze_sentiment as rule_based_analysis
        
        score, pos_kw, neg_kw = rule_based_analysis(text)
        
        # Xác định label
        if score > 0.3:
            label = 'positive'
        elif score < -0.3:
            label = 'negative'
        else:
            label = 'neutral'
        
        # Confidence thấp hơn vì dùng rule-based
        confidence = min(abs(score), 0.7)
        
        keywords = pos_kw if score > 0 else neg_kw
        
        return score, confidence, label, keywords


# Singleton instance
_analyzer = None

def get_sentiment_analyzer():
    """Get or create sentiment analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


def analyze_sentiment_ai(text):
    """
    Wrapper function để phân tích sentiment bằng AI
    
    Args:
        text (str): Text cần phân tích
        
    Returns:
        tuple: (sentiment_score, positive_keywords, negative_keywords)
            - Tương thích với interface cũ
    """
    analyzer = get_sentiment_analyzer()
    score, confidence, label, keywords = analyzer.analyze(text)
    
    # Phân chia keywords theo sentiment
    if label == 'positive':
        positive_keywords = keywords
        negative_keywords = []
    elif label == 'negative':
        positive_keywords = []
        negative_keywords = keywords
    else:
        positive_keywords = []
        negative_keywords = []
    
    return score, positive_keywords, negative_keywords


def batch_analyze_sentiments(texts):
    """
    Phân tích sentiment cho nhiều texts cùng lúc (hiệu quả hơn)
    
    Args:
        texts (list): Danh sách texts
        
    Returns:
        list: Danh sách (score, pos_kw, neg_kw) cho mỗi text
    """
    analyzer = get_sentiment_analyzer()
    results = []
    
    for text in texts:
        score, pos_kw, neg_kw = analyze_sentiment_ai(text)
        results.append((score, pos_kw, neg_kw))
    
    return results
