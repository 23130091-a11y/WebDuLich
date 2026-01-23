"""
Script để tích hợp fine-tuned PhoBERT model vào ai_engine.py

Sau khi fine-tune xong, chạy script này để:
1. Copy model vào thư mục travel/models/
2. Update ai_engine.py để load model mới
"""

import os
import shutil

# Paths
FINETUNED_MODEL_PATH = "./phobert-travel-sentiment"
TARGET_MODEL_PATH = "../travel/models/phobert-travel-sentiment"

# Code snippet để update ai_engine.py
AI_ENGINE_UPDATE = '''
# ============================================================
# UPDATED: Load fine-tuned PhoBERT model for Travel domain
# ============================================================

# Thay đổi trong class SentimentAnalyzer:

def load_model(self):
    """Load fine-tuned PhoBERT model"""
    if self.model_loaded:
        return
    
    try:
        logger.info("Loading fine-tuned PhoBERT model...")
        
        # Ưu tiên load fine-tuned model
        finetuned_path = os.path.join(settings.BASE_DIR, 'travel', 'models', 'phobert-travel-sentiment')
        
        if os.path.exists(finetuned_path):
            model_name = finetuned_path
            logger.info(f"Using fine-tuned model from: {finetuned_path}")
        else:
            # Fallback to original model
            model_name = "wonrax/phobert-base-vietnamese-sentiment"
            logger.info(f"Fine-tuned model not found, using: {model_name}")
        
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
'''


def copy_model():
    """Copy fine-tuned model to travel/models/"""
    if not os.path.exists(FINETUNED_MODEL_PATH):
        print(f"❌ Fine-tuned model not found at: {FINETUNED_MODEL_PATH}")
        print("Please run finetune_phobert.py first!")
        return False
    
    # Create target directory
    os.makedirs(os.path.dirname(TARGET_MODEL_PATH), exist_ok=True)
    
    # Copy model
    if os.path.exists(TARGET_MODEL_PATH):
        shutil.rmtree(TARGET_MODEL_PATH)
    
    shutil.copytree(FINETUNED_MODEL_PATH, TARGET_MODEL_PATH)
    print(f"✅ Model copied to: {TARGET_MODEL_PATH}")
    return True


def print_integration_guide():
    """Print hướng dẫn tích hợp"""
    print("\n" + "=" * 60)
    print("HƯỚNG DẪN TÍCH HỢP FINE-TUNED MODEL")
    print("=" * 60)
    
    print("""
1. Chạy fine-tuning:
   cd finetune_phobert
   python prepare_dataset.py
   python finetune_phobert.py

2. Copy model:
   python integrate_finetuned_model.py --copy

3. Update ai_engine.py:
   Thay đổi hàm load_model() trong class SentimentAnalyzer:
""")
    print(AI_ENGINE_UPDATE)
    
    print("""
4. Test model mới:
   cd ..
   python test_comprehensive.py

5. Kiểm tra kết quả:
   - Accuracy nên tăng từ 82% lên 90%+
   - F1 NEU nên cải thiện đáng kể
   - Mixed sentiment cases nên được xử lý tốt hơn
""")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--copy":
        copy_model()
    else:
        print_integration_guide()
