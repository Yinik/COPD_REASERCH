#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成精简版人工审核文件
- 删除冗长的"原始句子"字段
- 新增"精简上下文"：只保留头实体前后30字
- 保留源文件名（不长，且有用）
"""
import config  # 统一路径配置

import csv
import os
import re

INPUT_FILE = 'v4_最大覆盖版_原始三元组_带溯源.csv'
OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

def extract_context(sentence, head, tail, window=30):
    """提取头实体和尾实体周围的关键上下文"""
    if not sentence:
        return ""
    
    # 找到头实体和尾实体在句子中的位置
    head_pos = sentence.find(head)
    if head_pos == -1:
        # 尝试找头原文
        head_pos = sentence.find(head[:3]) if len(head) >= 3 else -1
    
    tail_pos = sentence.find(tail)
    if tail_pos == -1:
        tail_pos = sentence.find(tail[:3]) if len(tail) >= 3 else -1
    
    # 确定截取范围
    if head_pos != -1 and tail_pos != -1:
        start = min(head_pos, tail_pos)
        end = max(head_pos + len(head), tail_pos + len(tail))
    elif head_pos != -1:
        start = head_pos
        end = head_pos + len(head)
    elif tail_pos != -1:
        start = tail_pos
        end = tail_pos + len(tail)
    else:
        # 都找不到，取句子前60字
        return sentence[:60] + "..." if len(sentence) > 60 else sentence
    
    # 向前后扩展window个字符
    context_start = max(0, start - window)
    context_end = min(len(sentence), end + window)
    
    context = sentence[context_start:context_end]
    if context_start > 0:
        context = "..." + context
    if context_end < len(sentence):
        context = context + "..."
    
    return context

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

# 定义精简后的字段（删除原始句子，新增精简上下文）
ORIGINAL_FIELDS = ['关系类型', '头实体', '头类型', '尾实体', '尾类型', '头原文', '尾原文', '文献编号', '匹配类型']
NEW_FIELDS = ['精简上下文', '审核状态', '修改建议', '备注']

def write_trimmed_file(filepath, data_rows):
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=ORIGINAL_FIELDS + NEW_FIELDS, delimiter='\t')
        writer.writeheader()
        for r in data_rows:
            row = {k: r.get(k, '') for k in ORIGINAL_FIELDS}
            row['精简上下文'] = extract_context(r.get('原始句子', ''), r['头实体'], r['尾实体'])
            row['审核状态'] = '待审核'
            row['修改建议'] = ''
            row['备注'] = ''
            writer.writerow(row)

# 生成 explicit 精简版
explicit_path = os.path.join(OUTPUT_DIR, '待审核_精简版_explicit_高质量.tsv')
write_trimmed_file(explicit_path, explicit_rows)
print(f"已生成: {explicit_path} ({len(explicit_rows)} 条)")

# 生成 cooccur 精简版
cooccur_path = os.path.join(OUTPUT_DIR, '待审核_精简版_cooccur_兜底.tsv')
write_trimmed_file(cooccur_path, cooccur_rows)
print(f"已生成: {cooccur_path} ({len(cooccur_rows)} 条)")

# 生成合并精简版
all_path = os.path.join(OUTPUT_DIR, '待审核_精简版_全部_981条.tsv')
write_trimmed_file(all_path, rows)
print(f"已生成: {all_path} ({len(rows)} 条)")

print("\n全部精简版生成完毕！")
