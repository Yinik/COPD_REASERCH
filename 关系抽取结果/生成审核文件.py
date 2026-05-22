#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成人工审核专用文件
将981条三元组拆分为 explicit（高质量）和 cooccur（兜底）两个文件
增加审核状态、修改建议、备注字段
"""
import config  # 统一路径配置

import csv
import os

INPUT_FILE = 'v4_最大覆盖版_原始三元组_带溯源.csv'
OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

# 读取原始数据
rows = []
with open(os.path.join(OUTPUT_DIR, INPUT_FILE), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

print(f"读取完成: {len(rows)} 条三元组")

# 拆分
explicit_rows = [r for r in rows if r['匹配类型'] == 'explicit']
cooccur_rows = [r for r in rows if r['匹配类型'] == 'cooccur']

print(f"Explicit（明确模板）: {len(explicit_rows)} 条")
print(f"Cooccur（兜底共现）: {len(cooccur_rows)} 条")

# 新增字段
NEW_FIELDS = ['审核状态', '修改建议', '备注']

# 生成 explicit 审核文件
explicit_path = os.path.join(OUTPUT_DIR, '待审核_三元组_explicit_高质量.tsv')
with open(explicit_path, 'w', encoding='utf-8-sig', newline='') as f:
    fieldnames = list(rows[0].keys()) + NEW_FIELDS
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    for r in explicit_rows:
        row = dict(r)
        row['审核状态'] = '待审核'
        row['修改建议'] = ''
        row['备注'] = ''
        writer.writerow(row)

print(f"已生成: {explicit_path} ({len(explicit_rows)} 条)")

# 生成 cooccur 审核文件
cooccur_path = os.path.join(OUTPUT_DIR, '待审核_三元组_cooccur_兜底.tsv')
with open(cooccur_path, 'w', encoding='utf-8-sig', newline='') as f:
    fieldnames = list(rows[0].keys()) + NEW_FIELDS
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    for r in cooccur_rows:
        row = dict(r)
        row['审核状态'] = '待审核'
        row['修改建议'] = ''
        row['备注'] = ''
        writer.writerow(row)

print(f"已生成: {cooccur_path} ({len(cooccur_rows)} 条)")

# 同时生成一个合并的完整审核文件
all_path = os.path.join(OUTPUT_DIR, '待审核_三元组_全部_981条.tsv')
with open(all_path, 'w', encoding='utf-8-sig', newline='') as f:
    fieldnames = list(rows[0].keys()) + NEW_FIELDS
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    for r in rows:
        row = dict(r)
        row['审核状态'] = '待审核'
        row['修改建议'] = ''
        row['备注'] = ''
        writer.writerow(row)

print(f"已生成: {all_path} ({len(rows)} 条)")

print("\n全部生成完毕！")
