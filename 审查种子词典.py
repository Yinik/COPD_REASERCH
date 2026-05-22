#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取并审查种子词典
"""
import config  # 统一路径配置

import csv

TSV_PATH = 'I:\\101实验专题\\种子词典构建结果\\29_全部中文文献_最终种子词典_严格清理1.tsv'

# 读取UTF-16 LE文件
with open(TSV_PATH, 'r', encoding='utf-16-le') as f:
    reader = csv.DictReader(f, delimiter='\t')
    fieldnames = reader.fieldnames
    rows = list(reader)

print("字段名:", fieldnames)
print(f"总行数: {len(rows)}")
print()

# 按类型分组
from collections import defaultdict
by_type = defaultdict(list)
for r in rows:
    by_type[r.get('类型', r.get('type', 'UNKNOWN'))].append(r)

# 输出各类型统计
print("=" * 60)
print("种子词典各类型统计")
print("=" * 60)
for t in sorted(by_type.keys()):
    items = by_type[t]
    print(f"\n【{t}】共 {len(items)} 条")
    for r in items:
        std = r.get('标准术语', r.get('standard_term', ''))
        alias = r.get('别名', r.get('alias', ''))
        if alias:
            print(f"  {std} (别名: {alias})")
        else:
            print(f"  {std}")
