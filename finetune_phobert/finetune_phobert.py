"""
Fine-tune PhoBERT cho Travel Sentiment Analysis

Model: vinai/phobert-base hoặc wonrax/phobert-base-vietnamese-sentiment
Task: 3-class classification (NEG, NEU, POS)

Requirements:
- transformers>=4.30.0
- torch>=2.0.0
- datasets
- scikit-learn
- pandas
"""

import os
import torch
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    DataCollatorWithPadding,
)
from datasets import Dataset, DatasetDict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class FinetuneConfig:
    """Configuration cho fine-tuning"""
    # Model
    model_name: str = "wonrax/phobert-base-vietnamese-sentiment"
    num_labels: int = 3
    
    # Training
    output_dir: str = "./phobert-travel-sentiment"
    num_train_epochs: int = 5
    per_device_train_batch_size: int = 16
    per_device_eval_batch_size: int = 32
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    
    # Evaluation
    evaluation_strategy: str = "epoch"
    save_strategy: str = "epoch"
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_f1_macro"
    greater_is_better: bool = True
    
    # Early stopping
    early_stopping_patience: int = 3
    
    # Data
    max_length: int = 256
    data_dir: str = "./finetune_data"
    
    # Label mapping
    label2id: Dict = field(default_factory=lambda: {"NEG": 0, "NEU": 1, "POS": 2})
    id2label: Dict = field(default_factory=lambda: {0: "NEG", 1: "NEU", 2: "POS"})


# ============================================================
# DATA LOADING
# ============================================================

def load_data(config: FinetuneConfig) -> DatasetDict:
    """Load và preprocess data từ CSV files"""
    
    # Load CSV files
    train_df = pd.read_csv(f"{config.data_dir}/train.csv")
    val_df = pd.read_csv(f"{config.data_dir}/val.csv")
    test_df = pd.read_csv(f"{config.data_dir}/test.csv")
    
    # Convert to HuggingFace Dataset
    train_dataset = Dataset.from_pandas(train_df[['text', 'label_id']])
    val_dataset = Dataset.from_pandas(val_df[['text', 'label_id']])
    test_dataset = Dataset.from_pandas(test_df[['text', 'label_id']])
    
    # Rename label column
    train_dataset = train_dataset.rename_column("label_id", "labels")
    val_dataset = val_dataset.rename_column("label_id", "labels")
    test_dataset = test_dataset.rename_column("label_id", "labels")
    
    return DatasetDict({
        "train": train_dataset,
        "validation": val_dataset,
        "test": test_dataset
    })


def tokenize_data(dataset: DatasetDict, tokenizer, config: FinetuneConfig) -> DatasetDict:
    """Tokenize dataset"""
    
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=config.max_length,
        )
    
    tokenized = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
    )
    
    return tokenized


# ============================================================
# METRICS
# ============================================================

def compute_metrics(eval_pred):
    """Compute metrics cho evaluation"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    
    # Accuracy
    accuracy = accuracy_score(labels, predictions)
    
    # Precision, Recall, F1 (macro)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='macro', zero_division=0
    )
    
    # Per-class metrics
    precision_per_class, recall_per_class, f1_per_class, _ = precision_recall_fscore_support(
        labels, predictions, average=None, zero_division=0
    )
    
    return {
        "accuracy": accuracy,
        "f1_macro": f1,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_neg": f1_per_class[0],
        "f1_neu": f1_per_class[1],
        "f1_pos": f1_per_class[2],
    }


# ============================================================
# TRAINING
# ============================================================

class TravelSentimentTrainer:
    """Trainer class cho Travel Sentiment Fine-tuning"""
    
    def __init__(self, config: FinetuneConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        self.trainer = None
        
    def setup(self):
        """Setup model và tokenizer"""
        logger.info(f"Loading model: {self.config.model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        
        # Load model
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.config.model_name,
            num_labels=self.config.num_labels,
            id2label=self.config.id2label,
            label2id=self.config.label2id,
            ignore_mismatched_sizes=True,  # Cho phép thay đổi classifier head
        )
        
        logger.info(f"Model loaded successfully")
        
    def prepare_data(self) -> DatasetDict:
        """Load và tokenize data"""
        logger.info("Loading data...")
        dataset = load_data(self.config)
        
        logger.info("Tokenizing data...")
        tokenized_dataset = tokenize_data(dataset, self.tokenizer, self.config)
        
        logger.info(f"Train samples: {len(tokenized_dataset['train'])}")
        logger.info(f"Val samples: {len(tokenized_dataset['validation'])}")
        logger.info(f"Test samples: {len(tokenized_dataset['test'])}")
        
        return tokenized_dataset
    
    def train(self, tokenized_dataset: DatasetDict):
        """Train model"""
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            per_device_eval_batch_size=self.config.per_device_eval_batch_size,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_ratio=self.config.warmup_ratio,
            evaluation_strategy=self.config.evaluation_strategy,
            save_strategy=self.config.save_strategy,
            load_best_model_at_end=self.config.load_best_model_at_end,
            metric_for_best_model=self.config.metric_for_best_model,
            greater_is_better=self.config.greater_is_better,
            logging_dir=f"{self.config.output_dir}/logs",
            logging_steps=100,
            report_to="none",  # Disable wandb
            fp16=torch.cuda.is_available(),  # Use FP16 if GPU available
        )
        
        # Data collator
        data_collator = DataCollatorWithPadding(tokenizer=self.tokenizer)
        
        # Trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset["train"],
            eval_dataset=tokenized_dataset["validation"],
            tokenizer=self.tokenizer,
            data_collator=data_collator,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=self.config.early_stopping_patience)],
        )
        
        # Train
        logger.info("Starting training...")
        train_result = self.trainer.train()
        
        # Save model
        logger.info(f"Saving model to {self.config.output_dir}")
        self.trainer.save_model()
        self.tokenizer.save_pretrained(self.config.output_dir)
        
        return train_result
    
    def evaluate(self, tokenized_dataset: DatasetDict) -> Dict:
        """Evaluate on test set"""
        logger.info("Evaluating on test set...")
        
        results = self.trainer.evaluate(tokenized_dataset["test"])
        
        # Get predictions for confusion matrix
        predictions = self.trainer.predict(tokenized_dataset["test"])
        preds = np.argmax(predictions.predictions, axis=1)
        labels = predictions.label_ids
        
        # Confusion matrix
        cm = confusion_matrix(labels, preds)
        
        logger.info("\n=== Test Results ===")
        logger.info(f"Accuracy: {results['eval_accuracy']:.4f}")
        logger.info(f"F1 Macro: {results['eval_f1_macro']:.4f}")
        logger.info(f"F1 NEG: {results['eval_f1_neg']:.4f}")
        logger.info(f"F1 NEU: {results['eval_f1_neu']:.4f}")
        logger.info(f"F1 POS: {results['eval_f1_pos']:.4f}")
        logger.info(f"\nConfusion Matrix:\n{cm}")
        
        return results
    
    def predict(self, texts: List[str]) -> List[Dict]:
        """Predict sentiment cho list of texts"""
        results = []
        
        for text in texts:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_length,
                padding=True,
            )
            
            # Move to same device as model
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
            
            probs = probs.cpu().numpy()[0]
            pred_label = np.argmax(probs)
            
            results.append({
                "text": text,
                "label": self.config.id2label[pred_label],
                "confidence": float(probs[pred_label]),
                "probs": {
                    "NEG": float(probs[0]),
                    "NEU": float(probs[1]),
                    "POS": float(probs[2]),
                }
            })
        
        return results


# ============================================================
# MAIN
# ============================================================

def main():
    """Main function để fine-tune PhoBERT"""
    
    # Config
    config = FinetuneConfig(
        model_name="wonrax/phobert-base-vietnamese-sentiment",
        output_dir="./phobert-travel-sentiment",
        data_dir="./finetune_data",
        num_train_epochs=5,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
    )
    
    # Initialize trainer
    trainer = TravelSentimentTrainer(config)
    
    # Setup
    trainer.setup()
    
    # Prepare data
    tokenized_dataset = trainer.prepare_data()
    
    # Train
    train_result = trainer.train(tokenized_dataset)
    
    # Evaluate
    test_results = trainer.evaluate(tokenized_dataset)
    
    # Test predictions
    test_texts = [
        "Địa điểm rất đẹp, view tuyệt vời!",
        "Dịch vụ tệ, không bao giờ quay lại!",
        "Cũng được, không có gì đặc biệt.",
        "Cảnh đẹp nhưng đông quá.",
        "Không tệ lắm, tạm ổn.",
        "Hơi đắt nhưng đáng tiền.",
    ]
    
    print("\n=== Sample Predictions ===")
    predictions = trainer.predict(test_texts)
    for pred in predictions:
        print(f"Text: {pred['text']}")
        print(f"  → Label: {pred['label']} (conf: {pred['confidence']:.3f})")
        print(f"  → Probs: NEG={pred['probs']['NEG']:.3f}, NEU={pred['probs']['NEU']:.3f}, POS={pred['probs']['POS']:.3f}")
        print()
    
    print(f"\n✅ Model saved to: {config.output_dir}")
    print("To use in production, update ai_engine.py to load from this path.")


if __name__ == "__main__":
    main()
