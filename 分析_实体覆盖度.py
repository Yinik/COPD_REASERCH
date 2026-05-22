# -*- coding: utf-8 -*-
import config  # 统一路径配置

import csv
from collections import defaultdict

# 读取种子词典
seed_dict = {}
with open(str(config.BASE_DIR / r"种子词典构建结果\29_全部中文文献_最终种子词典_严格清理1.tsv"), 'rb') as f:
    raw = f.read()
if raw.startswith(b'\xff\xfe'):
    text = raw.decode('utf-16-le')
else:
    text = raw.decode('utf-8-sig')
from io import StringIO
reader = csv.DictReader(StringIO(text), delimiter='\t')
for row in reader:
    std = row['标准术语'].strip()
    typ = row['类型'].strip()
    seed_dict[std] = typ

# 读取三元组 (A+B版本)
triples = []
with open(str(config.BASE_DIR / r"关系抽取结果\A+B_句子清洗+文献筛选_原始三元组_带溯源.csv"), 'r', encoding='utf-8-sig') as f:

    reader = csv.DictReader(f)
    for row in reader:
        triples.append(row)

print('=' * 60)
print('实体覆盖度分析报告')
print('=' * 60)
print(f'种子词典实体总数: {len(seed_dict)}')
print(f'三元组总数: {len(triples)}')

# 统计参与三元组的实体
entity_in_triples = set()
entity_as_head = defaultdict(int)
entity_as_tail = defaultdict(int)

for t in triples:
    h, tail = t['头实体'], t['尾实体']
    entity_in_triples.add(h)
    entity_in_triples.add(tail)
    entity_as_head[h] += 1
    entity_as_tail[tail] += 1

participated = len(entity_in_triples)
isolated = len(seed_dict) - participated
print(f'\n至少参与1个三元组的实体: {participated} / {len(seed_dict)} ({participated/len(seed_dict)*100:.1f}%)')
print(f'完全孤立的实体: {isolated} / {len(seed_dict)} ({isolated/len(seed_dict)*100:.1f}%)')

# 按类型统计
print('\n' + '=' * 60)
print('各类型实体参与情况')
print('=' * 60)
type_stats = defaultdict(lambda: {'total': 0, 'in_triple': 0, 'isolated': 0})
for entity, typ in seed_dict.items():
    type_stats[typ]['total'] += 1
    if entity in entity_in_triples:
        type_stats[typ]['in_triple'] += 1
    else:
        type_stats[typ]['isolated'] += 1

TYPE_ORDER = ['Disease','Symptom','Examination','Medication','Treatment','Pathology','Complication','RiskFactor','Guideline','Organization','TCM_Syndrome','Concept','Anatomical']
TYPE_LABELS = {'Disease':'疾病','Symptom':'症状','Examination':'检查','Medication':'药物','Treatment':'治疗','Pathology':'病理','Complication':'并发症','RiskFactor':'危险因素','Guideline':'指南','Organization':'机构','TCM_Syndrome':'中医证候','Concept':'概念','Anatomical':'解剖'}

print(f"{'类型':<12} {'总数':>4} {'参与':>4} {'孤立':>4} {'参与率':>6}")
print('-' * 40)
for typ in TYPE_ORDER:
    if typ in type_stats:
        s = type_stats[typ]
        print(f"{TYPE_LABELS[typ]:<10} {s['total']:>4} {s['in_triple']:>4} {s['isolated']:>4} {s['in_triple']/s['total']*100:>5.1f}%")

# 列出完全孤立的实体
print('\n' + '=' * 60)
print('完全孤立的实体列表（未参与任何三元组）')
print('=' * 60)
for typ in TYPE_ORDER:
    isolated_list = [e for e, t in seed_dict.items() if t == typ and e not in entity_in_triples]
    if isolated_list:
        print(f"\n[{TYPE_LABELS[typ]}] 孤立 {len(isolated_list)} 个:")
        for e in isolated_list:
            print(f"  - {e}")

# 高频实体参与度排名
print('\n' + '=' * 60)
print('参与度最高的实体（出现在最多三元组中）')
print('=' * 60)
entity_freq = {}
for e in entity_in_triples:
    entity_freq[e] = entity_as_head.get(e, 0) + entity_as_tail.get(e, 0)

sorted_entities = sorted(entity_freq.items(), key=lambda x: -x[1])
for i, (e, freq) in enumerate(sorted_entities[:30], 1):
    typ = seed_dict.get(e, '?')
    print(f"{i:2}. [{typ}] {e} : {freq} 次")
