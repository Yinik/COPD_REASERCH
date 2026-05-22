#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚定小簇型孤立关系 V2
找出头尾都不是慢阻肺的真正小簇
"""
import config  # 统一路径配置

import csv
import os
from collections import defaultdict

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

COPD_ALIASES = {'慢性阻塞性肺疾病', '慢阻肺', 'COPD'}

def is_copd(term):
    return term in COPD_ALIASES

# 读取全部数据
all_rows = []
with open(os.path.join(OUTPUT_DIR, '待审核_精简版_explicit_高质量.tsv'), 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        r['_source'] = 'explicit'
        all_rows.append(r)

with open(os.path.join(OUTPUT_DIR, '待审核_精简版_cooccur_兜底.tsv'), 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        r['_source'] = 'cooccur'
        all_rows.append(r)

print(f"总关系数: {len(all_rows)}")

# 统计每个实体的度数
degree = defaultdict(int)
neighbors = defaultdict(set)
for row in all_rows:
    h, t = row['头实体'], row['尾实体']
    degree[h] += 1
    degree[t] += 1
    neighbors[h].add(t)
    neighbors[t].add(h)

# 找出头尾都不是慢阻肺的关系（真正的小簇）
no_copd_relations = [r for r in all_rows if not is_copd(r['头实体']) and not is_copd(r['尾实体'])]
print(f"头尾都不是慢阻肺的关系: {len(no_copd_relations)} 条")

# 分析这些小簇的连通性
print("\n" + "=" * 70)
print("【小簇详细分析】")
print("=" * 70)

# 按类型分组
from collections import Counter
type_pairs = Counter(f"{r['头类型']}→{r['尾类型']}" for r in no_copd_relations)
print(f"\n类型组合分布:")
for pair, count in type_pairs.most_common():
    print(f"  {pair}: {count} 条")

print(f"\n典型小簇案例（前30条）:")
print("-" * 70)
for i, row in enumerate(no_copd_relations[:30], 1):
    h_deg = degree[row['头实体']]
    t_deg = degree[row['尾实体']]
    ctx = row.get('精简上下文', '')[:50]
    print(f"{i:2d}. [{row['头类型']}]{row['头实体']}(度{h_deg}) → [{row['尾类型']}]{row['尾实体']}(度{t_deg})")
    print(f"    来源: {row['_source']} | 上下文: {ctx}...")
    print()

# 分析这些小簇中实体的度数分布
print("=" * 70)
print("【小簇中实体的度数分布】")
print("=" * 70)

entities_in_clusters = set()
for r in no_copd_relations:
    entities_in_clusters.add(r['头实体'])
    entities_in_clusters.add(r['尾实体'])

print(f"小簇涉及实体总数: {len(entities_in_clusters)}")

deg_dist = Counter()
for e in entities_in_clusters:
    d = degree[e]
    if d == 1:
        deg_dist['度=1（纯叶子）'] += 1
    elif d == 2:
        deg_dist['度=2'] += 1
    elif d <= 5:
        deg_dist['度=3-5'] += 1
    else:
        deg_dist['度>5（核心节点）'] += 1

for k, v in deg_dist.items():
    print(f"  {k}: {v} 个")

# 打印度数=1的实体（纯叶子）
print(f"\n纯叶子实体（度=1，只出现在一条关系中）:")
leaf_entities = [e for e in entities_in_clusters if degree[e] == 1]
for e in leaf_entities[:20]:
    # 找到包含该实体的关系
    for r in no_copd_relations:
        if r['头实体'] == e or r['尾实体'] == e:
            print(f"  {e} 在: {r['头实体']} → {r['尾实体']}")
            break
