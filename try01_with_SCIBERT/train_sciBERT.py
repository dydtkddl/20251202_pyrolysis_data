# -*- coding: utf-8 -*-
"""
SciBERT EXP/NONEXP 분류기 전체 엔진
------------------------------------
✓ SciBERT-uncased 사용
✓ JSONL 데이터 자동 로딩
✓ logging + tqdm
✓ GPU 자동 사용
✓ 학습/검증 정확도 출력
"""

import os
import json
import logging
from tqdm import tqdm
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.metrics import accuracy_score


# -------------------------------------------------------
# 0) Logging
# -------------------------------------------------------
logging.basicConfig(
    filename="train.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# -------------------------------------------------------
# 1) Dataset Loader
# -------------------------------------------------------
class PyroDataset(Dataset):
    def __init__(self, jsonl_file, tokenizer, max_len=256):
        self.samples = []
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                self.samples.append(item)

        self.tokenizer = tokenizer
        self.max_len = max_len
        self.label_map = {"exp": 1, "noexp": 0}

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text = self.samples[idx]["text"]
        label = self.label_map[self.samples[idx]["label"]]

        enc = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_len,
            return_tensors="pt",
        )

        return {
            "input_ids": enc["input_ids"].squeeze(),
            "attention_mask": enc["attention_mask"].squeeze(),
            "labels": torch.tensor(label, dtype=torch.long),
        }


# -------------------------------------------------------
# 2) Training Function
# -------------------------------------------------------
def train_one_epoch(model, loader, optimizer, scheduler, device):
    model.train()
    total_loss = 0

    pbar = tqdm(loader, desc="Training", ncols=120)
    for batch in pbar:
        batch = {k: v.to(device) for k, v in batch.items()}

        outputs = model(**batch)
        loss = outputs.loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        pbar.set_postfix({"loss": f"{loss.item():.4f}"})

    return total_loss / len(loader)


# -------------------------------------------------------
# 3) Evaluation
# -------------------------------------------------------
@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    preds, labels = [], []

    for batch in tqdm(loader, desc="Evaluating", ncols=120):
        labels.extend(batch["labels"].tolist())
        batch = {k: v.to(device) for k, v in batch.items()}

        outputs = model(**batch)
        logits = outputs.logits
        preds.extend(torch.argmax(logits, dim=1).cpu().tolist())

    acc = accuracy_score(labels, preds)
    return acc


# -------------------------------------------------------
# 4) Main
# -------------------------------------------------------
def main():
    train_path = "train.jsonl"
    valid_path = "valid.jsonl"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    # SciBERT-uncased (추천)
    model_name = "allenai/scibert_scivocab_uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Dataset
    train_ds = PyroDataset(train_path, tokenizer)
    valid_ds = PyroDataset(valid_path, tokenizer)

    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True)
    valid_loader = DataLoader(valid_ds, batch_size=8)

    # Model
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
    ).to(device)

    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)

    # Scheduler
    epochs = 4
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
    )

    # Training Loop
    for epoch in range(1, epochs + 1):
        logger.info(f"Epoch {epoch}/{epochs}")

        train_loss = train_one_epoch(model, train_loader, optimizer, scheduler, device)
        val_acc = evaluate(model, valid_loader, device)

        logger.info(f"[Epoch {epoch}] Train Loss: {train_loss:.4f}, Valid Acc: {val_acc:.4f}")
        print(f"📢 Epoch {epoch}: Train Loss={train_loss:.4f}, Valid Acc={val_acc:.4f}")

    # Save Model
    os.makedirs("saved_model", exist_ok=True)
    model.save_pretrained("saved_model")
    tokenizer.save_pretrained("saved_model")

    print("🎉 Training complete! Model saved in ./saved_model")


if __name__ == "__main__":
    main()

