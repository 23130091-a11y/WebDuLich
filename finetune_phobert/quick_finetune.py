"""
Quick Fine-tune Script - Chạy nhanh để test

Sử dụng:
- Ít epochs hơn (2-3)
- Batch size nhỏ hơn cho CPU
- Có thể chạy trên CPU trong ~30-60 phút
"""

import os
import sys
import torch
import pandas as pd
import numpy as np
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)
from datasets import Dataset, DatasetDict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

# Check device
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Config
MODEL_NAME = "wonrax/phobert-base-vietnamese-sentiment"
OUTPUT_DIR = "./phobert-travel-sentiment-quick"
DATA_DIR = "./finetune_data"
MAX_LENGTH = 128  # Shorter for faster training
BATCH_SIZE = 8 if device == "cpu" else 16
NUM_EPOCHS = 2 if device == "cpu" else 3
LEARNING_RATE = 3e-5

# Label mapping
LABEL2ID = {"NEG": 0, "NEU": 1, "POS": 2}
ID2LABEL = {0: "NEG", 1: "NEU", 2: "POS"}


def load_data():
    """Load data từ CSV"""
    train_df = pd.read_csv(f"{DATA_DIR}/train.csv")
    val_df = pd.read_csv(f"{DATA_DIR}/val.csv")
    test_df = pd.read_csv(f"{DATA_DIR}/test.csv")
    
    # Limit data for quick training
    if device == "cpu":
        train_df = train_df.sample(min(1000, len(train_df)), random_state=42)
        val_df = val_df.sample(min(200, len(val_df)), random_state=42)
        test_df = test_df.sample(min(200, len(test_df)), random_state=42)
    
    print(f"Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    return train_df, val_df, test_df


def compute_metrics(eval_pred):
    """Compute metrics"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    
    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='macro', zero_division=0
    )
    
    _, _, f1_per_class, _ = precision_recall_fscore_support(
        labels, predictions, average=None, zero_division=0
    )
    
    return {
        "accuracy": accuracy,
        "f1_macro": f1,
        "f1_neg": f1_per_class[0],
        "f1_neu": f1_per_class[1],
        "f1_pos": f1_per_class[2],
    }


def main():
    print("=" * 60)
    print("QUICK FINE-TUNE PhoBERT FOR TRAVEL SENTIMENT")
    print("=" * 60)
    
    # Load tokenizer and model
    print("\n1. Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )
    
    # Load data
    print("\n2. Loading data...")
    train_df, val_df, test_df = load_data()
    
    # Create datasets
    def create_dataset(df):
        dataset = Dataset.from_pandas(df[['text', 'label_id']])
        dataset = dataset.rename_column("label_id", "labels")
        
        def tokenize(examples):
            return tokenizer(
                examples["text"],
                padding="max_length",
                truncation=True,
                max_length=MAX_LENGTH,
            )
        
        return dataset.map(tokenize, batched=True, remove_columns=["text"])
    
    train_dataset = create_dataset(train_df)
    val_dataset = create_dataset(val_df)
    test_dataset = create_dataset(test_df)
    
    # Training arguments
    print("\n3. Setting up training...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE * 2,
        learning_rate=LEARNING_RATE,
        weight_decay=0.01,
        warmup_ratio=0.1,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_f1_macro",
        greater_is_better=True,
        logging_steps=50,
        report_to="none",
        fp16=device == "cuda",
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )
    
    # Train
    print("\n4. Training...")
    print(f"   Epochs: {NUM_EPOCHS}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Learning rate: {LEARNING_RATE}")
    
    trainer.train()
    
    # Evaluate
    print("\n5. Evaluating on test set...")
    results = trainer.evaluate(test_dataset)
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Accuracy: {results['eval_accuracy']:.4f}")
    print(f"F1 Macro: {results['eval_f1_macro']:.4f}")
    print(f"F1 NEG:   {results['eval_f1_neg']:.4f}")
    print(f"F1 NEU:   {results['eval_f1_neu']:.4f}")
    print(f"F1 POS:   {results['eval_f1_pos']:.4f}")
    
    # Save model
    print(f"\n6. Saving model to {OUTPUT_DIR}...")
    trainer.save_model()
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    # Test predictions
    print("\n7. Sample predictions...")
    test_texts = [
        "Địa điểm rất đẹp, view tuyệt vời!",
        "Dịch vụ tệ, không bao giờ quay lại!",
        "Cũng được, không có gì đặc biệt.",
        "Cảnh đẹp nhưng đông quá.",
        "Không tệ lắm, tạm ổn.",
        "Hơi đắt nhưng đáng tiền.",
        "Ok thôi, bình thường.",
        "Tạm ổn, giá hơi cao.",
    ]
    
    model.eval()
    model.to(device)
    
    print("\n" + "-" * 60)
    for text in test_texts:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]
        
        pred_label = ID2LABEL[np.argmax(probs)]
        print(f"'{text}'")
        print(f"  → {pred_label} (NEG:{probs[0]:.2f}, NEU:{probs[1]:.2f}, POS:{probs[2]:.2f})")
        print()
    
    print("=" * 60)
    print("✅ DONE!")
    print(f"Model saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
