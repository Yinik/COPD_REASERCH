# -*- coding: utf-8 -*-
"""
基于BERT的COPD医学关系抽取模型

训练数据：675条三元组（头实体、尾实体、关系类型、精简上下文）
模型：bert-base-chinese + 全连接分类层
任务：13类关系分类

用法:
    python bert_relation_extraction.py
"""
import config  # 统一路径配置


import os
import re
import random
import numpy as np
import pandas as pd
from collections import Counter

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertModel, AdamW, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

# ========== 配置 ==========
SEED = 42
MAX_LEN = 256
BATCH_SIZE = 16
EPOCHS = 30
LR = 2e-5
BERT_MODEL = 'bert-base-chinese'
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f'使用设备: {DEVICE}')

# 固定随机种子
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

set_seed(SEED)

# ========== 13种关系类型 ==========
RELATION_TYPES = [
    '药物-治疗-疾病',
    '药物-缓解-症状',
    '药物-导致-并发症',
    '疾病-症状',
    '疾病-并发症',
    '疾病-治疗',
    '检查-辅助诊断-疾病',
    '检查-评估-症状',
    '检查-评估-疾病',
    '检查-筛查-疾病',
    '治疗-改善-症状',
    '危险因素-疾病',
    '诱发-急性加重',
]
REL2ID = {rel: i for i, rel in enumerate(RELATION_TYPES)}
ID2REL = {i: rel for rel, i in REL2ID.items()}
NUM_CLASSES = len(RELATION_TYPES)

# ========== 数据加载 ==========
def load_data(tsv_path='关系抽取结果/方向规范化_疾病统一在头.tsv'):
    """从三元组文件加载数据，构造训练样本"""
    df = pd.read_csv(tsv_path, sep='\t', encoding='utf-8')
    
    samples = []
    for _, row in df.iterrows():
        rel = str(row.iloc[0]).strip()
        head = str(row.iloc[1]).strip()
        tail = str(row.iloc[2]).strip()
        head_raw = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else head
        tail_raw = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else tail
        context = str(row.iloc[9]).strip() if pd.notna(row.iloc[9]) else ''
        
        if rel not in REL2ID:
            continue
        
        # 构造输入文本：头实体 + SEP + 尾实体 + SEP + 上下文
        # 这样BERT能明确知道要判断哪两个实体之间的关系
        if context:
            text = f'{head_raw}[SEP]{tail_raw}[SEP]{context}'
        else:
            text = f'{head_raw}[SEP]{tail_raw}'
        
        samples.append({
            'text': text,
            'head': head,
            'tail': tail,
            'relation': rel,
            'label': REL2ID[rel],
        })
    
    return samples

# ========== Dataset ==========
class RelationDataset(Dataset):
    def __init__(self, samples, tokenizer, max_len=MAX_LEN):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_len = max_len
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        s = self.samples[idx]
        encoding = self.tokenizer.encode_plus(
            s['text'],
            add_special_tokens=True,
            max_length=self.max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'label': torch.tensor(s['label'], dtype=torch.long),
        }

# ========== 模型定义 ==========
class BertRelationClassifier(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES, dropout=0.3):
        super().__init__()
        self.bert = BertModel.from_pretrained(BERT_MODEL)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_classes)
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # 取[CLS] token的输出作为句子表示
        cls_output = outputs.last_hidden_state[:, 0, :]  # [batch, hidden_size]
        cls_output = self.dropout(cls_output)
        logits = self.classifier(cls_output)
        return logits

# ========== 训练 ==========
def train_epoch(model, dataloader, optimizer, scheduler, criterion):
    model.train()
    total_loss = 0
    for batch in dataloader:
        input_ids = batch['input_ids'].to(DEVICE)
        attention_mask = batch['attention_mask'].to(DEVICE)
        labels = batch['label'].to(DEVICE)
        
        optimizer.zero_grad()
        logits = model(input_ids, attention_mask)
        loss = criterion(logits, labels)
        loss.backward()
        
        # 梯度裁剪，防止BERT微调时梯度爆炸
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        scheduler.step()
        total_loss += loss.item()
    
    return total_loss / len(dataloader)

# ========== 评估 ==========
def eval_epoch(model, dataloader):
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch['input_ids'].to(DEVICE)
            attention_mask = batch['attention_mask'].to(DEVICE)
            labels = batch['label'].to(DEVICE)
            
            logits = model(input_ids, attention_mask)
            preds = torch.argmax(logits, dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    acc = accuracy_score(all_labels, all_preds)
    f1 = f1_score(all_labels, all_preds, average='weighted')
    return acc, f1, all_labels, all_preds

# ========== 主流程 ==========
def main():
    print('=' * 60)
    print('COPD医学关系抽取 - BERT微调')
    print('=' * 60)
    
    # 加载数据
    print('\n[1/6] 加载数据...')
    samples = load_data()
    print(f'  总样本数: {len(samples)}')
    print(f'  关系分布: {Counter(s["relation"] for s in samples)}')
    
    # 划分训练/验证/测试
    train_samples, temp_samples = train_test_split(
        samples, test_size=0.3, random_state=SEED, stratify=[s['label'] for s in samples]
    )
    val_samples, test_samples = train_test_split(
        temp_samples, test_size=0.5, random_state=SEED,
        stratify=[s['label'] for s in temp_samples]
    )
    print(f'  训练集: {len(train_samples)} | 验证集: {len(val_samples)} | 测试集: {len(test_samples)}')
    
    # Tokenizer
    print('\n[2/6] 加载BERT tokenizer...')
    tokenizer = BertTokenizer.from_pretrained(BERT_MODEL)
    
    # Dataset & DataLoader
    print('\n[3/6] 构造DataLoader...')
    train_ds = RelationDataset(train_samples, tokenizer)
    val_ds = RelationDataset(val_samples, tokenizer)
    test_ds = RelationDataset(test_samples, tokenizer)
    
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE)
    
    # 模型
    print('\n[4/6] 初始化模型...')
    model = BertRelationClassifier(num_classes=NUM_CLASSES).to(DEVICE)
    
    # 优化器和学习率调度
    optimizer = AdamW(model.parameters(), lr=LR, weight_decay=0.01)
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
    )
    criterion = nn.CrossEntropyLoss()
    
    # 训练
    print('\n[5/6] 开始训练...')
    best_f1 = 0
    best_state = None
    patience = 5
    no_improve = 0
    
    for epoch in range(1, EPOCHS + 1):
        train_loss = train_epoch(model, train_loader, optimizer, scheduler, criterion)
        val_acc, val_f1, _, _ = eval_epoch(model, val_loader)
        
        print(f'  Epoch {epoch:02d} | Loss: {train_loss:.4f} | Val Acc: {val_acc:.4f} | Val F1: {val_f1:.4f}')
        
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_state = model.state_dict()
            no_improve = 0
        else:
            no_improve += 1
        
        if no_improve >= patience:
            print(f'  早停: 验证F1连续{patience}轮未提升')
            break
    
    # 加载最佳模型
    model.load_state_dict(best_state)
    
    # 测试集评估
    print('\n[6/6] 测试集评估...')
    test_acc, test_f1, true_labels, pred_labels = eval_epoch(model, test_loader)
    print(f'  测试集准确率: {test_acc:.4f}')
    print(f'  测试集F1: {test_f1:.4f}')
    
    print('\n' + '=' * 60)
    print('分类报告:')
    print(classification_report(
        true_labels, pred_labels,
        target_names=RELATION_TYPES,
        digits=3, zero_division=0
    ))
    
    # 保存模型
    os.makedirs('bert_model', exist_ok=True)
    torch.save(best_state, 'bert_model/best_model.pt')
    tokenizer.save_pretrained('bert_model')
    print('模型已保存到 bert_model/')
    
    # 保存对比结果
    with open('BERT_TRAINING_RESULT.txt', 'w', encoding='utf-8') as f:
        f.write('BERT关系抽取训练结果\n')
        f.write('=' * 60 + '\n')
        f.write(f'训练样本: {len(train_samples)}\n')
        f.write(f'验证样本: {len(val_samples)}\n')
        f.write(f'测试样本: {len(test_samples)}\n')
        f.write(f'模型: {BERT_MODEL}\n')
        f.write(f'最佳验证F1: {best_f1:.4f}\n')
        f.write(f'测试集准确率: {test_acc:.4f}\n')
        f.write(f'测试集F1: {test_f1:.4f}\n')
    
    print('\n结果已保存到 BERT_TRAINING_RESULT.txt')

if __name__ == '__main__':
    main()
