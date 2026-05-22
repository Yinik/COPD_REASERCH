# -*- coding: utf-8 -*-
"""
深入分析孤立实体原因
"""
import config  # 统一路径配置


import os
import re
import csv
from collections import defaultdict

SEED_DICT_PATH = str(config.BASE_DIR / r"种子词典构建结果\29_全部中文文献_最终种子词典_严格清理1.tsv")
TEXT_DIR = str(config.BASE_DIR / r"抽取结果\cleaned_texts")

# 读取种子词典
seed_dict = {}
with open(SEED_DICT_PATH, 'rb') as f:
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

# 读取当前三元组中的实体
entity_in_triples = set()
with open(str(config.BASE_DIR / r"关系抽取结果\A+B_句子清洗+文献筛选_原始三元组_带溯源.csv"), 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        entity_in_triples.add(row['头实体'])
        entity_in_triples.add(row['尾实体'])

# 统计每个实体在所有清洗文本中的出现情况
entity_occurrence = defaultdict(lambda: {'count': 0, 'files': set(), 'contexts': []})
for txt_name in os.listdir(TEXT_DIR):
    if not txt_name.endswith('.txt'):
        continue
    with open(os.path.join(TEXT_DIR, txt_name), 'r', encoding='utf-8') as f:

        text = f.read()
    
    for entity, typ in seed_dict.items():
        if entity in text:
            # 找到出现位置及上下文
            idx = text.find(entity)
            context = text[max(0,idx-30):idx+len(entity)+30]
            entity_occurrence[entity]['count'] += text.count(entity)
            entity_occurrence[entity]['files'].add(txt_name)
            if len(entity_occurrence[entity]['contexts']) < 3:
                entity_occurrence[entity]['contexts'].append((txt_name, context))

# 分析孤立实体
print("=" * 70)
print("孤立实体深度原因分析")
print("=" * 70)

isolated_by_type = defaultdict(list)
for entity, typ in seed_dict.items():
    if entity not in entity_in_triples:
        isolated_by_type[typ].append(entity)

# 原因分类统计
category_reasons = {
    '来自被过滤文献': [],
    '在文本中出现但无共现实体': [],
    '在文本中出现有共现实体但句式不匹配': [],
    '在文本中未出现': [],
}

for entity, typ in seed_dict.items():
    if entity in entity_in_triples:
        continue
    
    occ = entity_occurrence[entity]
    if occ['count'] == 0:
        category_reasons['在文本中未出现'].append((entity, typ))
    else:
        # 检查是否有共现实体
        has_cooccur = False
        for other_entity, other_typ in seed_dict.items():
            if other_entity == entity or other_entity in entity_in_triples:
                continue
            for fname, ctx in occ['contexts']:
                if other_entity in ctx:
                    has_cooccur = True
                    break
            if has_cooccur:
                break
        
        # 判断是否来自被过滤文献
        filtered_keywords = ['咳嗽', 'GERD', '胃食管反流', 'COVID', '新冠', '囊性纤维化', 'cystic-fibrosis', '胸外科', 'thoracic', 'Miller', '肺血栓']
        from_filtered = any(kw in ' '.join(occ['files']) for kw in filtered_keywords)
        
        if from_filtered and occ['count'] > 0:
            category_reasons['来自被过滤文献'].append((entity, typ, occ['count']))
        elif not has_cooccur:
            category_reasons['在文本中出现但无共现实体'].append((entity, typ, occ['count']))
        else:
            category_reasons['在文本中出现有共现实体但句式不匹配'].append((entity, typ, occ['count']))

for reason, items in category_reasons.items():
    print(f"\n【{reason}】: {len(items)} 个")
    for item in items[:15]:
        if len(item) == 2:
            print(f"  - [{item[1]}] {item[0]}")
        else:
            print(f"  - [{item[1]}] {item[0]} (出现{item[2]}次)")
    if len(items) > 15:
        print(f"  ... 等共{len(items)}个")

print("\n" + "=" * 70)
print("改进建议")
print("=" * 70)
print(f"""
1. 来自被过滤文献 ({len(category_reasons['来自被过滤文献'])}个):
   → 原因: A+B模式过滤了咳嗽/GERD/COVID文献
   → 方案: 放宽文献筛选,保留咳嗽指南(COPD与慢性咳嗽症状重叠度高)

2. 在文本中出现但无共现实体 ({len(category_reasons['在文本中出现但无共现实体'])}个):
   → 原因: 该实体在文本中独立出现,周围没有其他词典实体
   → 方案: 放宽句子边界或跨句匹配

3. 在文本中出现有共现实体但句式不匹配 ({len(category_reasons['在文本中出现有共现实体但句式不匹配'])}个):
   → 原因: 实体在句中共现,但不符合任何正则模板
   → 方案: 增加兜底"相关"关系 + 扩展病理/概念关系

4. 在文本中未出现 ({len(category_reasons['在文本中未出现'])}个):
   → 原因: PDF提取失败或该实体不在41篇文献中
   → 方案: 接受现实,这些实体无法从当前语料中抽取
""")
