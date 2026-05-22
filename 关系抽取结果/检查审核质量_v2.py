#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查V2审核质量，抽样展示保留和删除的案例
"""
import config  # 统一路径配置

import csv
import os

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

# 重新导入审核函数
import importlib.util
spec = importlib.util.spec_from_file_location("audit_module", os.path.join(OUTPUT_DIR, "医学知识自动审核_v2.py"))
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

# 读取数据
rows_coo = []
with open(os.path.join(OUTPUT_DIR, '待审核_精简版_cooccur_兜底.tsv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for r in reader:
        rows_coo.append(r)

kept = []
deleted = []
for row in rows_coo:
    status, suggestion, note = audit_module.audit_cooccur(row)
    if status == '保留':
        kept.append((row, suggestion, note))
    else:
        deleted.append((row, note))

print("=" * 70)
print(f"Cooccur 审核结果: 保留 {len(kept)} 条, 删除 {len(deleted)} 条")
print("=" * 70)

print("\n【保留案例 Top 20 — 医学上合理的共现关系】")
print("-" * 70)
for i, (row, suggestion, note) in enumerate(kept[:20]):
    rel_str = f"→ [{suggestion}]" if suggestion else "→ [相关]"
    print(f"{i+1:2d}. ({row['头类型']}→{row['尾类型']}) {row['头实体']} {rel_str} {row['尾实体']}")
    print(f"    备注: {note}")
    print()

print("\n【删除案例 Top 20 — 伪关系/无意义共现】")
print("-" * 70)
for i, (row, note) in enumerate(deleted[:20]):
    print(f"{i+1:2d}. ({row['头类型']}→{row['尾类型']}) {row['头实体']} → {row['尾实体']}")
    print(f"    上下文: {row['精简上下文'][:60]}...")
    print(f"    删除原因: {note}")
    print()

# 统计按类型的删除分布
from collections import Counter
delete_types = Counter(f"{r['头类型']}→{r['尾类型']}" for r, n in deleted)
print("\n【删除案例的类型分布】")
for type_pair, count in delete_types.most_common():
    print(f"  {type_pair}: {count} 条")
