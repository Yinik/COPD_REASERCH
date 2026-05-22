#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚定小簇型孤立关系
核心策略：
1. 找出所有与"慢阻肺"主图断开的小簇
2. 对每条小簇关系溯源原始证据句
3. 如果证据句中慢阻肺也出现 → 列举误抽，删除小簇，补充慢阻肺关系
4. 如果证据句中慢阻肺没出现但实体是慢阻肺合并症 → 补充锚定边
5. 否则 → 删除小簇
"""
import config  # 统一路径配置

import csv
import os
from collections import defaultdict

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

# ==================== 读取全部审核后的数据 ====================

# 读取Explicit
exp_rows = []
with open(os.path.join(OUTPUT_DIR, '待审核_精简版_explicit_高质量.tsv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for r in reader:
        r['_source'] = 'explicit'
        exp_rows.append(r)

# 读取Cooccur
coo_rows = []
with open(os.path.join(OUTPUT_DIR, '待审核_精简版_cooccur_兜底.tsv'), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter='\t')
    for r in reader:
        r['_source'] = 'cooccur'
        coo_rows.append(r)

all_rows = exp_rows + coo_rows
print(f"总关系数: {len(all_rows)} (explicit {len(exp_rows)} + cooccur {len(coo_rows)})")

# ==================== 构建图结构 ====================

# 找到"慢阻肺"的所有别名
COPD_ALIASES = {'慢性阻塞性肺疾病', '慢阻肺', 'COPD'}

def is_copd(term):
    return term in COPD_ALIASES

# 构建邻接表
graph = defaultdict(set)  # entity -> set of neighbors
relation_map = {}  # (head, tail) -> row

for row in all_rows:
    h = row['头实体']
    t = row['尾实体']
    graph[h].add(t)
    graph[t].add(h)
    relation_map[(h, t)] = row

# 从慢阻肺出发BFS，找到所有可达实体
reachable_from_copd = set()
queue = list(COPD_ALIASES)
for alias in COPD_ALIASES:
    reachable_from_copd.add(alias)

while queue:
    node = queue.pop(0)
    for neighbor in graph.get(node, set()):
        if neighbor not in reachable_from_copd:
            reachable_from_copd.add(neighbor)
            queue.append(neighbor)

print(f"从慢阻肺可达的实体: {len(reachable_from_copd)} 个")

# 找出所有与慢阻肺断开的关系（小簇）
disconnected_relations = []
for row in all_rows:
    h = row['头实体']
    t = row['尾实体']
    if h not in reachable_from_copd and t not in reachable_from_copd:
        disconnected_relations.append(row)

print(f"\n与慢阻肺完全断开的关系: {len(disconnected_relations)} 条")

# ==================== 慢阻肺合并症集合（医学知识） ====================

COPD_COMORBIDITIES = {
    '糖尿病', '心血管疾病', '心绞痛', '心肌梗死', '心力衰竭', '心律失常',
    '肺心病', '慢性肺源性心脏病', '肺动脉高压',
    '骨质疏松', '骨质疏松症', '骨折',
    '抑郁症', '抑郁', '焦虑症', '焦虑',
    '睡眠障碍', '失眠',
    '肺癌', '贫血', '营养不良',
    '胃食管反流病', '胃食管反流',
    '阻塞性睡眠呼吸暂停', 'OSA',
    '高血压', '冠心病', '缺血性心脏病', '脑血管病',
    '代谢综合征', '肥胖', '低体重', '肌少症',
    '肺结核', '肺炎', '肺栓塞',
    '支气管哮喘', '哮喘',
    '右心衰竭', '呼吸衰竭',
}

# ==================== 锚定算法 ====================

anchored_relations = []    # 新增的锚定关系
kept_clusters = []         # 保留的小簇（医学上有独立价值）
deleted_clusters = []      # 删除的小簇（列举误抽）
modified_relations = []    # 修改的关系

def extract_copd_from_context(context):
    """从上下文中判断是否提及慢阻肺"""
    if not context:
        return False
    for alias in COPD_ALIASES:
        if alias in context:
            return True
    return False

for row in disconnected_relations:
    h = row['头实体']
    t = row['尾实体']
    context = row.get('精简上下文', '')
    rel_type = row['关系类型']
    h_type = row['头类型']
    t_type = row['尾类型']
    
    # 情况1：证据句中出现了慢阻肺 → 这是列举误抽
    if extract_copd_from_context(context):
        # 删除小簇关系 (h, 相关, t)
        # 但补充慢阻肺到h和慢阻肺到t的关系（如果还没有的话）
        deleted_clusters.append((row, '列举误抽：证据句中慢阻肺也出现，应是慢阻肺的并发症'))
        
        # 补充锚定关系
        if h in COPD_COMORBIDITIES:
            anchored_relations.append({
                '关系类型': '疾病-并发症',
                '头实体': '慢性阻塞性肺疾病',
                '头类型': 'Disease',
                '尾实体': h,
                '尾类型': h_type,
                '头原文': '慢阻肺',
                '尾原文': h,
                '精简上下文': context[:80],
                '文献编号': row.get('文献编号', ''),
                '匹配类型': 'anchored',
                '审核状态': '保留',
                '修改建议': '',
                '备注': '由小簇锚定算法补充：列举句中慢阻肺与' + h + '共现'
            })
        
        if t in COPD_COMORBIDITIES:
            anchored_relations.append({
                '关系类型': '疾病-并发症',
                '头实体': '慢性阻塞性肺疾病',
                '头类型': 'Disease',
                '尾实体': t,
                '尾类型': t_type,
                '头原文': '慢阻肺',
                '尾原文': t,
                '精简上下文': context[:80],
                '文献编号': row.get('文献编号', ''),
                '匹配类型': 'anchored',
                '审核状态': '保留',
                '修改建议': '',
                '备注': '由小簇锚定算法补充：列举句中慢阻肺与' + t + '共现'
            })
    
    # 情况2：证据句中没有慢阻肺，但h或t是慢阻肺合并症
    elif h in COPD_COMORBIDITIES or t in COPD_COMORBIDITIES:
        # 保留小簇关系（可能有独立医学价值，如糖尿病→心血管疾病）
        # 同时补充锚定边
        kept_clusters.append((row, '实体是慢阻肺合并症，保留小簇并补充锚定边'))
        
        if h in COPD_COMORBIDITIES:
            anchored_relations.append({
                '关系类型': '疾病-并发症',
                '头实体': '慢性阻塞性肺疾病',
                '头类型': 'Disease',
                '尾实体': h,
                '尾类型': h_type,
                '头原文': '慢阻肺',
                '尾原文': h,
                '精简上下文': context[:80] if context else '',
                '文献编号': row.get('文献编号', ''),
                '匹配类型': 'anchored',
                '审核状态': '保留',
                '修改建议': '',
                '备注': '由小簇锚定算法补充：' + h + '是慢阻肺已知合并症'
            })
        
        if t in COPD_COMORBIDITIES:
            anchored_relations.append({
                '关系类型': '疾病-并发症',
                '头实体': '慢性阻塞性肺疾病',
                '头类型': 'Disease',
                '尾实体': t,
                '尾类型': t_type,
                '头原文': '慢阻肺',
                '尾原文': t,
                '精简上下文': context[:80] if context else '',
                '文献编号': row.get('文献编号', ''),
                '匹配类型': 'anchored',
                '审核状态': '保留',
                '修改建议': '',
                '备注': '由小簇锚定算法补充：' + t + '是慢阻肺已知合并症'
            })
    
    # 情况3：都不是慢阻肺合并症 → 删除
    else:
        deleted_clusters.append((row, '与慢阻肺无关且非已知合并症，删除'))

# ==================== 生成最终文件 ====================

# 最终保留的关系 = 原有可达关系 + 保留的小簇 + 新增锚定关系
final_rows = []

# 1. 原有与慢阻肺连通的关系
for row in all_rows:
    h = row['头实体']
    t = row['尾实体']
    if h in reachable_from_copd or t in reachable_from_copd:
        final_rows.append(row)

# 2. 保留的小簇
for row, reason in kept_clusters:
    row['审核状态'] = '保留'
    row['备注'] = '小簇保留：' + reason
    final_rows.append(row)

# 3. 新增的锚定关系
final_rows.extend(anchored_relations)

# 去重
seen = set()
unique_final = []
for row in final_rows:
    key = (row['关系类型'], row['头实体'], row['尾实体'])
    if key not in seen:
        seen.add(key)
        unique_final.append(row)

# 输出统计
print("\n" + "=" * 60)
print("锚定算法结果统计")
print("=" * 60)
print(f"原始总关系: {len(all_rows)}")
print(f"与慢阻肺断开的小簇: {len(disconnected_relations)}")
print(f"  - 列举误抽（删除）: {len(deleted_clusters)} 条")
print(f"  - 合并症小簇（保留+锚定）: {len(kept_clusters)} 条")
print(f"  - 无关小簇（删除）: {len([d for d in deleted_clusters if '列举' not in d[1]])} 条")
print(f"新增锚定关系: {len(anchored_relations)} 条")
print(f"去重后最终关系: {len(unique_final)} 条")

# 打印典型案例
print("\n" + "=" * 60)
print("【列举误抽 → 删除 + 补充锚定】典型案例")
print("=" * 60)
for row, reason in deleted_clusters[:10]:
    print(f"\n删除: ({row['头实体']}) → [{row['关系类型']}] → ({row['尾实体']})")
    print(f"  原因: {reason}")
    print(f"  上下文: {row.get('精简上下文', '')[:60]}...")

print("\n" + "=" * 60)
print("【新增锚定关系】")
print("=" * 60)
for r in anchored_relations[:15]:
    print(f"  慢阻肺 → [{r['关系类型']}] → {r['尾实体']} ({r['尾类型']})")

# 保存到TSV
output_tsv = os.path.join(OUTPUT_DIR, '最终三元组_小簇锚定后.tsv')
if unique_final:
    fieldnames = list(unique_final[0].keys())
    with open(output_tsv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(unique_final)
    print(f"\n最终文件已保存: {output_tsv}")
