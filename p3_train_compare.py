#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P3 多配置消融实验训练脚本
在相同的训练/验证/测试集上，对比不同配置下的BERT关系分类性能
"""
import config
import os
import sys
import json
import time
import warnings
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizer, BertModel,
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
)

warnings.filterwarnings("ignore")

# ==================== 路径 ====================
DATA_DIR = config.BASE_DIR / "p3_comparison"
OUTPUT_DIR = config.BASE_DIR / "p3_comparison" / "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEVICE = torch.device("cpu")
SEED = 42


def set_seed(seed=42):
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# ==================== 配置定义 ====================
CONFIGS = {
    "baseline": {
        "desc": "基线配置（实体标记+类别权重+dropout=0.1）",
        "use_entity_markers": True,
        "use_class_weights": True,
        "dropout": 0.1,
        "lr": 2e-5,
    },
    "no_entity_markers": {
        "desc": "无实体标记（仅原始句子+[CLS]）",
        "use_entity_markers": False,
        "use_class_weights": True,
        "dropout": 0.1,
        "lr": 2e-5,
    },
    "no_class_weights": {
        "desc": "无类别权重（平衡采样）",
        "use_entity_markers": True,
        "use_class_weights": False,
        "dropout": 0.1,
        "lr": 2e-5,
    },
    "high_dropout": {
        "desc": "高dropout=0.3（更强正则化）",
        "use_entity_markers": True,
        "use_class_weights": True,
        "dropout": 0.3,
        "lr": 2e-5,
    },
}

# ==================== 超参数 ====================
MAX_SEQ_LEN = 128
BATCH_SIZE = 8
EPOCHS = 3
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
PATIENCE = 1
PRETRAINED_MODEL = "bert-base-chinese"


# ==================== 数据加载 ====================
def load_splits():
    with open(DATA_DIR / "train.json", "r", encoding="utf-8") as f:
        train = pd.DataFrame(json.load(f))
    with open(DATA_DIR / "val.json", "r", encoding="utf-8") as f:
        val = pd.DataFrame(json.load(f))
    with open(DATA_DIR / "test.json", "r", encoding="utf-8") as f:
        test = pd.DataFrame(json.load(f))
    return train, val, test


def build_label_map(train_df):
    relations = sorted(train_df["relation"].unique().tolist())
    relation2id = {rel: idx for idx, rel in enumerate(relations)}
    id2relation = {idx: rel for rel, idx in relation2id.items()}
    return relation2id, id2relation


def compute_class_weights(train_df, relation2id):
    total = len(train_df)
    n_classes = len(relation2id)
    weights = []
    for rel, idx in sorted(relation2id.items(), key=lambda x: x[1]):
        count = (train_df["relation"] == rel).sum()
        weights.append(total / (n_classes * max(count, 1)))
    return torch.tensor(weights, dtype=torch.float)


# ==================== 实体标记 ====================
def mark_entities(sentence, head, tail, use_markers=True):
    sentence = str(sentence) if pd.notna(sentence) else ""
    head = str(head) if pd.notna(head) else ""
    tail = str(tail) if pd.notna(tail) else ""

    if not use_markers:
        return sentence

    text = sentence
    if head and head in text:
        text = text.replace(head, f"[E1]{head}[/E1]", 1)
    if tail and tail in text and tail != head:
        text = text.replace(tail, f"[E2]{tail}[/E2]", 1)
    if "[E1]" not in text and "[E2]" not in text:
        text = f"[E1]{head}[/E1]与[E2]{tail}[/E2]的关系：{text}"
    return text


# ==================== Dataset ====================
class RelationDataset(Dataset):
    def __init__(self, df, tokenizer, relation2id, max_len=128, use_markers=True):
        self.df = df.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.relation2id = relation2id
        self.max_len = max_len
        self.use_markers = use_markers

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        text = mark_entities(row["sentence"], row["head"], row["tail"], self.use_markers)
        encoding = self.tokenizer(
            text, max_length=self.max_len, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        label = self.relation2id.get(row["relation"], 0)
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(label, dtype=torch.long),
        }


# ==================== 模型 ====================
class BertRelationClassifier(nn.Module):
    def __init__(self, num_classes, dropout=0.1):
        super().__init__()
        self.bert = BertModel.from_pretrained(PRETRAINED_MODEL, local_files_only=True)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.zeros_(self.classifier.bias)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.last_hidden_state[:, 0, :]
        pooled = self.dropout(pooled)
        return self.classifier(pooled)


# ==================== 训练 ====================
def train_epoch(model, dataloader, optimizer, scheduler, device, class_weights=None):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []
    criterion = nn.CrossEntropyLoss(
        weight=class_weights.to(device) if class_weights is not None else None
    )
    for batch in dataloader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["label"].to(device)
        optimizer.zero_grad()
        logits = model(input_ids, attention_mask)
        loss = criterion(logits, labels)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        total_loss += loss.item()
        preds = torch.argmax(logits, dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_labels.extend(labels.cpu().numpy())
    return total_loss / len(dataloader), accuracy_score(all_labels, all_preds)


def evaluate(model, dataloader, device, id2relation):
    model.eval()
    total_loss = 0
    all_preds, all_labels = [], []
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)
            logits = model(input_ids, attention_mask)
            loss = criterion(logits, labels)
            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(dataloader)
    acc = accuracy_score(all_labels, all_preds)
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="macro", zero_division=0
    )
    p_w, r_w, f1_w, _ = precision_recall_fscore_support(
        all_labels, all_preds, average="weighted", zero_division=0
    )
    p_c, r_c, f1_c, s_c = precision_recall_fscore_support(
        all_labels, all_preds, average=None, zero_division=0,
        labels=list(range(len(id2relation)))
    )
    per_class = {id2relation[i]: {"precision": p_c[i], "recall": r_c[i], "f1": f1_c[i], "support": int(s_c[i])}
                 for i in range(len(id2relation))}

    return {
        "loss": avg_loss, "accuracy": acc,
        "f1_macro": f1_macro, "f1_weighted": f1_w,
        "precision_macro": p_macro, "recall_macro": r_macro,
        "per_class": per_class,
    }


# ==================== 主流程 ====================
def run_experiment(cfg_name, cfg):
    print(f"\n{'='*60}")
    print(f"Config: {cfg_name} | {cfg['desc']}")
    print(f"{'='*60}")
    sys.stdout.flush()

    set_seed(SEED)
    start_time = time.time()

    train_df, val_df, test_df = load_splits()
    relation2id, id2relation = build_label_map(train_df)
    num_classes = len(relation2id)
    class_weights = compute_class_weights(train_df, relation2id) if cfg["use_class_weights"] else None

    tokenizer = BertTokenizer.from_pretrained(PRETRAINED_MODEL, local_files_only=True)
    if cfg["use_entity_markers"]:
        special_tokens = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
        num_added = tokenizer.add_special_tokens(special_tokens)
    else:
        num_added = 0

    train_ds = RelationDataset(train_df, tokenizer, relation2id, MAX_SEQ_LEN, cfg["use_entity_markers"])
    val_ds = RelationDataset(val_df, tokenizer, relation2id, MAX_SEQ_LEN, cfg["use_entity_markers"])
    test_ds = RelationDataset(test_df, tokenizer, relation2id, MAX_SEQ_LEN, cfg["use_entity_markers"])

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    model = BertRelationClassifier(num_classes, dropout=cfg["dropout"])
    if num_added > 0:
        model.bert.resize_token_embeddings(len(tokenizer), mean_resizing=False)
    model.to(DEVICE)

    optimizer = AdamW(model.parameters(), lr=cfg["lr"], weight_decay=WEIGHT_DECAY)
    total_steps = len(train_loader) * EPOCHS
    warmup_steps = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    best_f1 = 0
    patience_counter = 0
    history = []
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, scheduler, DEVICE, class_weights
        )
        val_metrics = evaluate(model, val_loader, DEVICE, id2relation)
        epoch_time = time.time() - t0

        history.append({
            "epoch": epoch,
            "train_loss": train_loss, "train_acc": train_acc,
            "val_loss": val_metrics["loss"], "val_acc": val_metrics["accuracy"],
            "val_f1_macro": val_metrics["f1_macro"],
            "val_f1_weighted": val_metrics["f1_weighted"],
        })

        print(f"  Epoch {epoch}/{EPOCHS} ({epoch_time:.0f}s) | "
              f"Train Loss: {train_loss:.4f} | "
              f"Val F1(macro): {val_metrics['f1_macro']:.4f} F1(w): {val_metrics['f1_weighted']:.4f}")
        sys.stdout.flush()

        if val_metrics["f1_macro"] > best_f1:
            best_f1 = val_metrics["f1_macro"]
            patience_counter = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"  -> Early stop (patience={PATIENCE})")
                break

    # 测试集评估
    model.load_state_dict(best_state)
    test_metrics = evaluate(model, test_loader, DEVICE, id2relation)

    elapsed = time.time() - start_time
    print(f"  Test | Acc: {test_metrics['accuracy']:.4f} | Macro-F1: {test_metrics['f1_macro']:.4f} | Weighted-F1: {test_metrics['f1_weighted']:.4f} | Time: {elapsed/60:.1f}min")
    sys.stdout.flush()

    result = {
        "config_name": cfg_name, "config": cfg,
        "num_classes": num_classes,
        "relations": list(relation2id.keys()),
        "relation2id": relation2id,
        "train_size": len(train_df), "val_size": len(val_df), "test_size": len(test_df),
        "best_val_f1_macro": best_f1,
        "test_metrics": {
            "accuracy": test_metrics["accuracy"],
            "f1_macro": test_metrics["f1_macro"],
            "f1_weighted": test_metrics["f1_weighted"],
            "precision_macro": test_metrics["precision_macro"],
            "recall_macro": test_metrics["recall_macro"],
            "per_class": test_metrics["per_class"],
        },
        "history": history,
        "elapsed_seconds": elapsed,
    }

    result_path = OUTPUT_DIR / f"{cfg_name}_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    model_path = OUTPUT_DIR / f"{cfg_name}_best_model.pt"
    torch.save({
        "model_state_dict": best_state,
        "relation2id": relation2id,
        "id2relation": id2relation,
        "config": cfg,
    }, model_path)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="all")
    args = parser.parse_args()

    configs_to_run = list(CONFIGS.keys()) if args.config == "all" else [args.config]
    all_results = {}
    for cfg_name in configs_to_run:
        if cfg_name not in CONFIGS:
            print(f"[Error] Unknown config: {cfg_name}")
            continue
        result = run_experiment(cfg_name, CONFIGS[cfg_name])
        all_results[cfg_name] = result

    summary_path = OUTPUT_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("P3 Ablation Results Summary")
    print(f"{'='*60}")
    print(f"{'Config':<22} {'Acc':>8} {'Macro-F1':>10} {'Weighted-F1':>12} {'Time(min)':>10}")
    print("-" * 60)
    for cfg_name, res in all_results.items():
        tm = res["elapsed_seconds"] / 60
        print(f"{cfg_name:<22} {res['test_metrics']['accuracy']:>8.4f} {res['test_metrics']['f1_macro']:>10.4f} {res['test_metrics']['f1_weighted']:>12.4f} {tm:>10.1f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
