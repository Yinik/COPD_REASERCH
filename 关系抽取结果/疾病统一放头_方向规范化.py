#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向规范化：尾实体是Disease时，反转方向使疾病在头
保留全部关系，只调整方向，不删除任何关系
"""
import config  # 统一路径配置

import csv
import os
from collections import Counter

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'
INPUT_FILE = '最终三元组_方案B_医学细化版.tsv'

# 读取数据
rows = []
with open(os.path.join(OUTPUT_DIR, INPUT_FILE), 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        rows.append(r)

print(f"读取: {len(rows)} 条关系")

# 处理每条关系
kept = []      # 保持不变
reversed_rows = []  # 方向反转

for row in rows:
    h_type = row['头类型']
    t_type = row['尾类型']
    
    # 规则：尾实体是Disease，且头实体不是Disease → 反转方向
    if t_type == 'Disease' and h_type != 'Disease':
        new_row = dict(row)
        # 交换头尾
        new_row['头实体'] = row['尾实体']
        new_row['尾实体'] = row['头实体']
        new_row['头类型'] = row['尾类型']
        new_row['尾类型'] = row['头类型']
        new_row['头原文'] = row['尾原文']
        new_row['尾原文'] = row['头原文']
        
        # 标记为已反转
        new_row['备注'] = f'方向规范化：尾实体是Disease，反转方向（原{row["头实体"]}→{row["尾实体"]}）'
        reversed_rows.append(new_row)
    else:
        # 保持不变（头已是Disease，或头尾都不是Disease）
        kept.append(row)

print(f"保持不变: {len(kept)} 条")
print(f"方向反转: {len(reversed_rows)} 条")

# 合并
all_rows = kept + reversed_rows

# 去重
seen = set()
unique = []
for r in all_rows:
    key = (r['关系类型'], r['头实体'], r['尾实体'])
    if key not in seen:
        seen.add(key)
        unique.append(r)

print(f"去重前: {len(all_rows)} 条")
print(f"去重后: {len(unique)} 条")

# 统计方向改善情况
head_is_disease = sum(1 for r in unique if r['头类型'] == 'Disease')
tail_is_disease = sum(1 for r in unique if r['尾类型'] == 'Disease')
print(f"\n方向改善统计:")
print(f"  疾病在头: {head_is_disease} 条 ({head_is_disease/len(unique)*100:.1f}%)")
print(f"  疾病在尾: {tail_is_disease} 条 ({tail_is_disease/len(unique)*100:.1f}%)")

# 保存
output = os.path.join(OUTPUT_DIR, '方向规范化_疾病统一在头.tsv')
with open(output, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(unique[0].keys()), delimiter='\t')
    writer.writeheader()
    writer.writerows(unique)

print(f"\n文件已保存: {output}")
