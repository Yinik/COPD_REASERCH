#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查自动审核质量，抽样展示保留和删除的案例
"""
import config  # 统一路径配置

import csv
import os

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

# 读取explicit审核结果
print("=" * 70)
print("Explicit 审核结果抽样检查")
print("=" * 70)

rows_exp = []
with open(os.path.join(OUTPUT_DIR, '待审核_精简版_explicit_高质量.tsv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for r in reader:
        rows_exp.append(r)

# 读取cooccur审核结果
rows_coo = []
with open(os.path.join(OUTPUT_DIR, '待审核_精简版_cooccur_兜底.tsv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for r in reader:
        rows_coo.append(r)

# 重新运行审核逻辑（简化版）获取审核结果
from 医学知识自动审核 import audit_explicit, audit_cooccur

print("\n【Explicit - 被删除的案例】")
deleted_exp = []
for row in rows_exp:
    status, suggestion, note = audit_explicit(row)
    if status == '删除':
        deleted_exp.append((row, note))

for i, (row, note) in enumerate(deleted_exp[:10]):
    print(f"  {i+1}. ({row['关系类型']}) {row['头实体']} → {row['尾实体']}")
    print(f"     原因: {note}")
    print()

print(f"  Explicit 删除总数: {len(deleted_exp)} 条")

print("\n【Cooccur - 被删除的案例】")
deleted_coo = []
for row in rows_coo:
    status, suggestion, note = audit_cooccur(row)
    if status == '删除':
        deleted_coo.append((row, note))

for i, (row, note) in enumerate(deleted_coo[:15]):
    print(f"  {i+1}. ({row['头类型']}→{row['尾类型']}) {row['头实体']} → {row['尾实体']}")
    print(f"     原因: {note}")
    print()

print(f"  Cooccur 删除总数: {len(deleted_coo)} 条")

print("\n【Cooccur - 被保留但可能存疑的案例（抽样）】")
kept_coo_samples = []
for row in rows_coo:
    status, suggestion, note = audit_cooccur(row)
    if status == '保留' and not suggestion:
        kept_coo_samples.append((row, note))

import random
random.seed(42)
if len(kept_coo_samples) > 20:
    samples = random.sample(kept_coo_samples, 20)
else:
    samples = kept_coo_samples

for i, (row, note) in enumerate(samples):
    print(f"  {i+1}. ({row['头类型']}→{row['尾类型']}) {row['头实体']} → {row['尾实体']}")
    print(f"     上下文: {row['精简上下文'][:80]}")
    print(f"     审核备注: {note}")
    print()

print(f"\nCooccur 保留但无细化建议的: {len(kept_coo_samples)} 条")
