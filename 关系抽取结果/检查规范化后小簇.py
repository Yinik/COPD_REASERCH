#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查方向规范化后的图谱连通性
"""
import config  # 统一路径配置

import csv
import os
from collections import defaultdict, Counter

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'
INPUT_FILE = '方向规范化_疾病统一在头.tsv'

COPD_ALIASES = {'慢性阻塞性肺疾病', '慢阻肺', 'COPD'}

def is_copd(term):
    return term in COPD_ALIASES

# 读取数据
rows = []
with open(os.path.join(OUTPUT_DIR, INPUT_FILE), 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        rows.append(r)

print(f"总关系: {len(rows)} 条")

# 构建图
graph = defaultdict(set)
entity_types = {}

for row in rows:
    h, t = row['头实体'], row['尾实体']
    h_type, t_type = row['头类型'], row['尾类型']
    graph[h].add(t)
    graph[t].add(h)  # 无向图用于连通性分析
    entity_types[h] = h_type
    entity_types[t] = t_type

# 从COPD出发BFS
reachable = set()
queue = list(COPD_ALIASES)
for alias in COPD_ALIASES:
    reachable.add(alias)

while queue:
    node = queue.pop(0)
    for neighbor in graph.get(node, set()):
        if neighbor not in reachable:
            reachable.add(neighbor)
            queue.append(neighbor)

print(f"从COPD可达的实体: {len(reachable)} 个")

# 找出所有不可达的实体
all_entities = set(entity_types.keys())
unreachable = all_entities - reachable

print(f"不可达的实体: {len(unreachable)} 个")

# 不可达实体按类型分类
unreachable_by_type = Counter(entity_types[e] for e in unreachable)
print(f"\n不可达实体类型分布:")
for etype, count in unreachable_by_type.most_common():
    print(f"  {etype}: {count} 个")

# 找出所有与COPD断开的关系
connected = []    # 与COPD连通
disconnected = []  # 与COPD断开

for row in rows:
    h, t = row['头实体'], row['尾实体']
    if h in reachable or t in reachable:
        connected.append(row)
    else:
        disconnected.append(row)

print(f"\n与COPD连通的关系: {len(connected)} 条")
print(f"与COPD断开的关系（小簇）: {len(disconnected)} 条 ({len(disconnected)/len(rows)*100:.1f}%)")

# 分析断开的小簇
print(f"\n断开的小簇分析:")

# 统计每个Disease子簇
disease_clusters = defaultdict(list)
for row in disconnected:
    h, t = row['头实体'], row['尾实体']
    h_type = row['头类型']
    if h_type == 'Disease':
        disease_clusters[h].append(row)

# 按大小排序
sorted_clusters = sorted(disease_clusters.items(), key=lambda x: -len(x[1]))

print(f"\n前10大孤立小簇（以Disease为头）:")
for i, (disease, rels) in enumerate(sorted_clusters[:10], 1):
    print(f"\n{i}. 【{disease}】簇 - {len(rels)} 条关系")
    for r in rels[:5]:
        print(f"   {r['头实体']} → [{r['关系类型']}] → {r['尾实体']}")
    if len(rels) > 5:
        print(f"   ... 等共 {len(rels)} 条")

# 分析连通后的效果
print(f"\n连通性改善建议:")
print(f"  若删除所有断开关系: 剩 {len(connected)} 条（纯COPD辐射图）")
print(f"  若保留全部: 共 {len(rows)} 条（含 {len(disconnected)} 条孤立小簇）")

# 检查断开的Disease列表
print(f"\n主要孤立中心疾病:")
for disease, rels in sorted_clusters[:15]:
    print(f"  {disease}: {len(rels)} 条")
