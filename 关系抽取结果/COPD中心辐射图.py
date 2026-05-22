#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建以COPD为中心的辐射型知识图谱
- 只保留涉及COPD的关系
- 反转所有COPD在尾的关系
- 重命名关系类型为COPD视角
"""
import config  # 统一路径配置

import csv
import os
from collections import Counter

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'
INPUT_FILE = '最终三元组_方案B_医学细化版.tsv'

COPD_CORE = {'慢性阻塞性肺疾病', '慢阻肺', 'COPD'}
COPD_EXTENDED = COPD_CORE | {'急性加重', 'AECOPD', '慢性阻塞性肺疾病急性加重'}

def is_copd(term):
    return term in COPD_EXTENDED

# 读取数据
rows = []
with open(os.path.join(OUTPUT_DIR, INPUT_FILE), 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        rows.append(r)

print(f"原始关系: {len(rows)} 条")

# 关系类型重命名映射（从COPD视角）
RELATION_RENAME = {
    # 本来就是COPD在头的关系
    '疾病-症状': '核心症状',
    '疾病-治疗': '核心治疗',
    '疾病-并发症': '常见合并症',
    
    # 需要反转的：药物→COPD → COPD→药物
    '药物-治疗-疾病': '治疗药物',
    '药物-缓解-症状': '对症治疗药物',
    '药物-影响-检查指标': '药物影响检查',
    '药物-导致-并发症': '药物不良反应',
    '药物-减少-急性加重': '预防急性加重药物',
    '药物-联合-药物': '药物联合方案',
    
    # 需要反转的：检查→COPD → COPD→检查
    '检查-辅助诊断-疾病': '诊断检查',
    '检查-评估-症状': '症状评估',
    '检查-评估-疾病': '疾病评估',
    '检查-筛查-疾病': '筛查检查',
    '检查-指导-治疗': '检查指导治疗',
    
    # 需要反转的：危险因素→COPD → COPD→危险因素
    '危险因素-疾病': '危险因素',
    '危险因素-加重-症状': '症状加重因素',
    '危险因素-协同-危险因素': '协同危险因素',
    
    # 病理生理
    '病理生理-导致': '病理生理改变',
    '病理生理-导致-症状': '病理生理改变',
    
    # 诱发
    '诱发-急性加重': '急性加重诱因',
    '治疗-减少-急性加重': '预防急性加重',
    
    # 治疗改善
    '治疗-改善-症状': '康复治疗',
    '治疗-改善-评估指标': '康复改善指标',
    
    # 其他
    '症状-伴随-症状': '伴随症状',
    '并发症-关联-并发症': '合并症关联',
}

# 处理每条关系
kept = []      # 保留的关系
deleted = []   # 删除的关系

for row in rows:
    h = row['头实体']
    t = row['尾实体']
    rel_type = row['关系类型']
    
    # 情况1: COPD在头 → 保持不变
    if is_copd(h):
        new_row = dict(row)
        new_rel = RELATION_RENAME.get(rel_type, rel_type)
        new_row['关系类型'] = new_rel
        if new_rel != rel_type:
            new_row['备注'] = f'COPD辐射图：{rel_type}→{new_rel}'
        kept.append(new_row)
        continue
    
    # 情况2: COPD在尾 → 反转方向
    if is_copd(t):
        new_row = dict(row)
        # 交换头尾
        new_row['头实体'] = t
        new_row['尾实体'] = h
        new_row['头类型'] = row['尾类型']
        new_row['尾类型'] = row['头类型']
        new_row['头原文'] = row['尾原文']
        new_row['尾原文'] = row['头原文']
        
        # 重命名关系
        new_rel = RELATION_RENAME.get(rel_type, rel_type)
        new_row['关系类型'] = new_rel
        new_row['备注'] = f'COPD辐射图：反转+重命名({rel_type}→{new_rel})'
        kept.append(new_row)
        continue
    
    # 情况3: 不涉及COPD → 删除
    deleted.append(row)

print(f"涉及COPD（保留+反转）: {len(kept)} 条")
print(f"不涉及COPD（删除）: {len(deleted)} 条")

# 统计
rel_counts = Counter(r['关系类型'] for r in kept)
print("\n辐射图关系类型分布:")
for rel, count in rel_counts.most_common():
    print(f"  {rel}: {count} 条")

# 去重
seen = set()
unique = []
for r in kept:
    key = (r['关系类型'], r['头实体'], r['尾实体'])
    if key not in seen:
        seen.add(key)
        unique.append(r)

print(f"\n去重前: {len(kept)} 条")
print(f"去重后: {len(unique)} 条")

# 保存
output = os.path.join(OUTPUT_DIR, 'COPD辐射图_中心版.tsv')
with open(output, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(unique[0].keys()), delimiter='\t')
    writer.writeheader()
    writer.writerows(unique)

print(f"\n文件已保存: {output}")
