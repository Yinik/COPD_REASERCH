#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BERT-based Relation Classification for COPD Medical Text
基于 BERT 的关系分类器 —— 轻量版（适合 CPU 运行）
"""
import config  # 统一路径配置


import os
import sys
import json
import warnings
import random
import numpy as np
import pandas as pd
from collections import Counter
from typing import List, Dict, Tuple

import config  # 统一路径配置
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizer,
    BertModel,
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

warnings.filterwarnings("ignore")

# ==================== 配置 ====================
class Config:
    DATA_PATH = str(config.RELATION_DIR / "最终三元组_方案B_医学细化版.tsv")
    OUTPUT_DIR = str(config.BERT_OUTPUT_DIR)
    PRETRAINED_MODEL = "bert-base-chinese"
    MAX_SEQ_LEN = 128  # 减小序列长度加速
    BATCH_SIZE = 8     # 减小 batch 降低内存
    EPOCHS = 10
    LEARNING_RATE = 2e-5
    WEIGHT_DECAY = 0.01
    WARMUP_RATIO = 0.1
    PATIENCE = 3
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    SEED = 42
    TEST_SIZE = 0.15


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


# ==================== 数据 ====================
def load_data(tsv_path):
    df = pd.read_csv(tsv_path, sep="\t", encoding="utf-8")
    print(f"[数据] 总条数: {len(df)}")
    return df


def build_relation_label_map(df):
    relations = sorted(df["关系类型"].unique().tolist())
    relation2id = {rel: idx for idx, rel in enumerate(relations)}
    id2relation = {idx: rel for rel, idx in relation2id.items()}
    print(f"[标签] 共 {len(relations)} 种关系:")
    for rel, idx in relation2id.items():
        print(f"  {idx}: {rel} ({(df['关系类型'] == rel).sum()}条)")
    return relation2id, id2relation


def compute_class_weights(df, relation2id):
    total = len(df)
    n_classes = len(relation2id)
    weights = []
    for rel, idx in sorted(relation2id.items(), key=lambda x: x[1]):
        count = (df["关系类型"] == rel).sum()
        weights.append(total / (n_classes * max(count, 1)))
    return torch.tensor(weights, dtype=torch.float)


# ==================== 实体标记 ====================
def mark_entities_in_sentence(sentence, head, tail):
    sentence = str(sentence) if pd.notna(sentence) else ""
    head = str(head) if pd.notna(head) else ""
    tail = str(tail) if pd.notna(tail) else ""
    
    text = sentence
    # 简单替换，优先替换较长的实体避免子串问题
    # 头实体
    if head and head in text:
        text = text.replace(head, f"[E1]{head}[/E1]", 1)
    # 尾实体
    if tail and tail in text:
        # 如果尾实体和头实体相同，避免重复替换
        if tail != head:
            text = text.replace(tail, f"[E2]{tail}[/E2]", 1)
    
    # 如果都没找到，拼接提示
    if "[E1]" not in text and "[E2]" not in text:
        text = f"[E1]{head}[/E1]与[E2]{tail}[/E2]的关系：{text}"
    
    return text


# ==================== Dataset ====================
class RelationDataset(Dataset):
    def __init__(self, df, tokenizer, relation2id, max_len=128):
        self.df = df.reset_index(drop=True)
        self.tokenizer = tokenizer
        self.relation2id = relation2id
        self.max_len = max_len
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        relation = row["关系类型"]
        head = row["头实体"]
        tail = row["尾实体"]
        
        sentence = row.get("上下文句子", "")
        if not sentence or (isinstance(sentence, float) and pd.isna(sentence)):
            sentence = row.iloc[9] if len(row) > 9 else ""
        sentence = str(sentence) if pd.notna(sentence) else ""
        
        text = mark_entities_in_sentence(sentence, head, tail)
        
        encoding = self.tokenizer(
            text,
            max_length=self.max_len,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        
        label = self.relation2id.get(relation, 0)
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(label, dtype=torch.long),
        }


# ==================== 模型 ====================
class BertRelationClassifier(nn.Module):
    def __init__(self, num_classes, pretrained_model="bert-base-chinese"):
        super().__init__()
        self.bert = BertModel.from_pretrained(pretrained_model, local_files_only=True)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)
        nn.init.xavier_uniform_(self.classifier.weight)
        nn.init.zeros_(self.classifier.bias)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.last_hidden_state[:, 0, :]  # [CLS]
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


def evaluate(model, dataloader, device):
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
    
    return {
        "loss": avg_loss, "accuracy": acc,
        "f1_macro": f1_macro, "f1_weighted": f1_w,
        "y_true": all_labels, "y_pred": all_preds,
    }


# ==================== 主流程 ====================
def run_training(config):
    print("=" * 60)
    print("BERT 关系分类器 - COPD 医学文本 (轻量版)")
    print(f"设备: {config.DEVICE}")
    print("=" * 60)
    sys.stdout.flush()
    
    set_seed(config.SEED)
    ensure_dir(config.OUTPUT_DIR)
    
    # 1. 数据
    df = load_data(config.DATA_PATH)
    relation2id, id2relation = build_relation_label_map(df)
    num_classes = len(relation2id)
    class_weights = compute_class_weights(df, relation2id)
    
    # 2. Tokenizer（先加载，再调整词表）
    print("\n[加载] Tokenizer...")
    sys.stdout.flush()
    tokenizer = BertTokenizer.from_pretrained(config.PRETRAINED_MODEL, local_files_only=True)
    
    # 添加特殊 token，然后手动初始化（避免 mean_resizing 在 CPU 上过慢）
    special_tokens = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
    num_added = tokenizer.add_special_tokens(special_tokens)
    print(f"[词表] 新增 {num_added} 个特殊 token，词表大小: {len(tokenizer)}")
    sys.stdout.flush()
    
    # 3. 划分训练/验证集
    labels = df["关系类型"].map(relation2id).values
    try:
        train_df, val_df = train_test_split(
            df, test_size=config.TEST_SIZE, random_state=config.SEED, stratify=labels
        )
    except ValueError:
        # 某些类别样本太少，无法 stratify，改用普通 split
        print("[警告] 部分类别样本过少，关闭分层抽样")
        train_df, val_df = train_test_split(
            df, test_size=config.TEST_SIZE, random_state=config.SEED
        )
    print(f"\n[划分] 训练集: {len(train_df)} | 验证集: {len(val_df)}")
    sys.stdout.flush()
    
    train_dataset = RelationDataset(train_df, tokenizer, relation2id, config.MAX_SEQ_LEN)
    val_dataset = RelationDataset(val_df, tokenizer, relation2id, config.MAX_SEQ_LEN)
    
    train_loader = DataLoader(train_dataset, batch_size=config.BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config.BATCH_SIZE, shuffle=False)
    
    # 4. 模型
    print("\n[加载] BERT 模型...")
    sys.stdout.flush()
    model = BertRelationClassifier(num_classes, config.PRETRAINED_MODEL)
    
    # 关键修复：禁用 mean_resizing，使用快速初始化
    model.bert.resize_token_embeddings(len(tokenizer), mean_resizing=False)
    print("[模型] Token 嵌入已调整")
    sys.stdout.flush()
    
    model.to(config.DEVICE)
    
    # 5. 优化器
    optimizer = AdamW(model.parameters(), lr=config.LEARNING_RATE, weight_decay=config.WEIGHT_DECAY)
    total_steps = len(train_loader) * config.EPOCHS
    warmup_steps = int(total_steps * config.WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )
    
    # 6. 训练循环
    print(f"\n[训练] 开始，共 {config.EPOCHS} epochs")
    sys.stdout.flush()
    
    best_f1 = 0
    patience_counter = 0
    best_model_path = os.path.join(config.OUTPUT_DIR, "best_model.pt")
    
    for epoch in range(1, config.EPOCHS + 1):
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, scheduler, config.DEVICE, class_weights
        )
        val_metrics = evaluate(model, val_loader, config.DEVICE)
        
        print(
            f"Epoch {epoch:02d} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
            f"Val Loss: {val_metrics['loss']:.4f} Acc: {val_metrics['accuracy']:.4f} "
            f"F1(macro): {val_metrics['f1_macro']:.4f} F1(weighted): {val_metrics['f1_weighted']:.4f}"
        )
        sys.stdout.flush()
        
        if val_metrics["f1_macro"] > best_f1:
            best_f1 = val_metrics["f1_macro"]
            patience_counter = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "relation2id": relation2id,
                "id2relation": id2relation,
                "tokenizer_name": config.PRETRAINED_MODEL,
            }, best_model_path)
            print(f"  -> 保存最佳模型 (Val F1={best_f1:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= config.PATIENCE:
                print(f"  -> 早停 (patience={config.PATIENCE})")
                break
    
    print(f"\n{'='*60}")
    print(f"训练完成 | 最佳 Val F1(macro): {best_f1:.4f}")
    print(f"模型保存: {best_model_path}")
    print(f"{'='*60}")
    
    # 保存元数据
    meta = {
        "relation2id": relation2id,
        "id2relation": id2relation,
        "num_classes": num_classes,
        "pretrained_model": config.PRETRAINED_MODEL,
        "max_seq_len": config.MAX_SEQ_LEN,
        "best_model_path": best_model_path,
    }
    with open(os.path.join(config.OUTPUT_DIR, "model_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    return best_model_path, relation2id, id2relation


# ==================== 预测 ====================
class RelationPredictor:
    def __init__(self, model_path, device=None):
        self.device = device or torch.device("cpu")
        checkpoint = torch.load(model_path, map_location=self.device)
        
        self.relation2id = checkpoint["relation2id"]
        self.id2relation = checkpoint["id2relation"]
        self.tokenizer = BertTokenizer.from_pretrained(
            checkpoint.get("tokenizer_name", "bert-base-chinese"), local_files_only=True
        )
        special_tokens = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
        self.tokenizer.add_special_tokens(special_tokens)
        
        self.model = BertRelationClassifier(
            num_classes=len(self.relation2id),
            pretrained_model=checkpoint.get("tokenizer_name", "bert-base-chinese"),
        )
        self.model.bert.resize_token_embeddings(len(self.tokenizer), mean_resizing=False)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()
        print(f"[预测器] 加载完成，{len(self.relation2id)} 种关系")
    
    def predict(self, sentence, head, tail):
        text = mark_entities_in_sentence(sentence, head, tail)
        encoding = self.tokenizer(
            text, max_length=256, padding="max_length",
            truncation=True, return_tensors="pt",
        )
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        
        with torch.no_grad():
            logits = self.model(input_ids, attention_mask)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
            pred_id = int(np.argmax(probs))
        
        top3_idx = np.argsort(probs)[::-1][:3]
        return {
            "sentence": sentence, "head": head, "tail": tail,
            "predicted_relation": self.id2relation[pred_id],
            "confidence": float(probs[pred_id]),
            "top3": [{"relation": self.id2relation[int(idx)], "probability": float(probs[idx])} for idx in top3_idx],
        }


# ==================== 入口 ====================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["train", "predict"], default="train")
    parser.add_argument("--model_path", type=str, default=None)
    parser.add_argument("--sentence", type=str, default="")
    parser.add_argument("--head", type=str, default="")
    parser.add_argument("--tail", type=str, default="")
    args = parser.parse_args()
    
    config = Config()
    
    if args.mode == "train":
        run_training(config)
    elif args.mode == "predict":
        if not args.model_path:
            meta_path = os.path.join(config.OUTPUT_DIR, "model_meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    args.model_path = json.load(f)["best_model_path"]
            else:
                raise FileNotFoundError("未找到模型")
        predictor = RelationPredictor(args.model_path, config.DEVICE)
        if args.sentence and args.head and args.tail:
            result = predictor.predict(args.sentence, args.head, args.tail)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("请提供 --sentence, --head, --tail")
