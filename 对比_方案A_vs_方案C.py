# -*- coding: utf-8 -*-
import config  # 统一路径配置

import csv
import os

A_TSV = str(config.BASE_DIR / r"种子词典构建结果\29_全部中文文献_最终种子词典_严格清理.tsv")
C_TSV = str(config.BASE_DIR / r"种子词典构建结果\30_COPD聚焦种子词典.tsv")
OUT_PATH = str(config.BASE_DIR / r"种子词典构建结果\方案A_vs_方案C_差异对比.txt")

def load_tsv(path):
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            entries.append({
                'standard': row['标准术语'],
                'aliases': row['同义词'] if row['同义词'] != '-' else '',
                'type': row['类型'],
                'freq': row['总频次'],
                'score': row['得分'],
            })
    return entries

a_entries = load_tsv(A_TSV)
c_entries = load_tsv(C_TSV)

a_dict = {e['standard']: e for e in a_entries}
c_dict = {e['standard']: e for e in c_entries}

# 共有术语
common = [s for s in a_dict if s in c_dict]
# A独有（被C过滤）
only_a = [s for s in a_dict if s not in c_dict]
# C独有（理论上没有，因为C是A的子集）
only_c = [s for s in c_dict if s not in a_dict]

TYPE_ORDER = ['Disease', 'Symptom', 'Examination', 'Medication', 'Treatment',
              'Pathology', 'Complication', 'RiskFactor', 'Guideline',
              'Organization', 'TCM_Syndrome', 'Concept', 'Anatomical']

TYPE_LABELS = {
    'Disease': '疾病', 'Symptom': '症状体征', 'Examination': '检查检验',
    'Medication': '药物', 'Treatment': '治疗方法', 'Pathology': '病理机制',
    'Complication': '并发症', 'RiskFactor': '危险因素', 'Guideline': '指南标准',
    'Organization': '组织机构', 'TCM_Syndrome': '中医证候', 'Concept': '抽象概念',
    'Anatomical': '解剖部位',
}

with open(OUT_PATH, 'w', encoding='utf-8') as f:

    f.write("=" * 70 + "\n")
    f.write("方案A (282条) vs 方案C (128条) — 实体差异对比\n")
    f.write("=" * 70 + "\n\n")

    f.write(f"【统计】\n")
    f.write(f"  方案A独有（被方案C过滤）: {len(only_a)} 条\n")
    f.write(f"  两方案共有: {len(common)} 条\n")
    f.write(f"  方案C独有: {len(only_c)} 条\n\n")

    if only_c:
        f.write("警告: 方案C中存在方案A没有的术语（理论上不应发生）\n\n")

    # 共有术语
    f.write("=" * 70 + "\n")
    f.write(f"【第一部分】两方案共有的术语 ({len(common)}条)\n")
    f.write("=" * 70 + "\n\n")
    for t in TYPE_ORDER:
        items = sorted([s for s in common if a_dict[s]['type'] == t])
        if not items:
            continue
        f.write(f"\n[{TYPE_LABELS[t]} / {t}] ({len(items)}条)\n")
        f.write("-" * 50 + "\n")
        for s in items:
            e = a_dict[s]
            alias = f" (别名: {e['aliases']})" if e['aliases'] else ""
            f.write(f"  + {s}{alias}\n")

    # A独有
    f.write("\n\n" + "=" * 70 + "\n")
    f.write(f"【第二部分】仅在方案A中存在、被方案C过滤的术语 ({len(only_a)}条)\n")
    f.write("=" * 70 + "\n")
    f.write("\n说明: 这些术语因以下原因之一被方案C过滤——\n")
    f.write("  1. 非COPD疾病（慢性咳嗽、GERD、COVID-19等）\n")
    f.write("  2. PDF提取截断/噪声\n")
    f.write("  3. 过于宽泛的非术语短语\n\n")

    for t in TYPE_ORDER:
        items = sorted([s for s in only_a if a_dict[s]['type'] == t])
        if not items:
            continue
        f.write(f"\n[{TYPE_LABELS[t]} / {t}] 被过滤 {len(items)} 条\n")
        f.write("-" * 50 + "\n")
        for s in items:
            e = a_dict[s]
            alias = f" (别名: {e['aliases']})" if e['aliases'] else ""
            f.write(f"  - {s}{alias} [频次{e['freq']}, 得分{e['score']}]\n")

print(f"[已保存] {OUT_PATH}")
print(f"  共有: {len(common)} 条")
print(f"  A独有(被C过滤): {len(only_a)} 条")
