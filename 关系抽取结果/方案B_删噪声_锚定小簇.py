#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案B：删除噪声小簇 + 保留医学相关簇 + 补充锚定边
"""
import config  # 统一路径配置

import csv
import os

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

COPD_ALIASES = {'慢性阻塞性肺疾病', '慢阻肺', 'COPD'}

def is_copd(term):
    return term in COPD_ALIASES

# ==================== 医学知识定义 ====================

# 噪声实体：应删除所有包含这些实体的关系
NOISE_ENTITIES = {
    # 慢性咳嗽指南噪声
    'EB', 'CVA', 'PNDS', '鼻后滴流综合征', '鼻后滴流',
    '嗜酸粒细胞性支气管炎', '咳嗽变异性哮喘', '躯体性咳敏综合征',
    '气道神经源性炎症', '引感性咳嗽', '抽动性咳嗽',
    
    # GERD/反流噪声
    '胃食管反流病', '胃食管反流', '反流性咽喉炎', '胃酸反流', '反流症状',
    '胆汁反流', '弱酸反流', '非酸反流', '食管反流', '气道反流问卷',
    '弱酸反流患者漏诊', '异常非酸反流',
    
    # 罕见病/非COPD
    '复发性多软骨炎', '细支气管炎', '迁延性支气管炎',
    'COVID-19',
    
    # 截断词/噪声
    '防止过无喘息', '镇咳药体激动剂', '反流症酸药物', '糖皮质激素及抗',
    '子类药物加', '雾化吸入利多卡', '镇咳药物分', '肺通气功',
    
    # 病原体（不应作为疾病节点）
    '肺炎链球菌', '肺炎支原体', '肺炎衣原体', '流感病毒', '不动杆菌感染',
    
    # 方向错误的评估指标
    '运动能力',  # 是评估指标，不是治疗措施
    'BMI',  # 体格指标
}

# 噪声关系：特定方向错误的关系对
NOISE_RELATION_PAIRS = {
    # (头实体, 尾实体) 精确匹配则删除
    ('运动能力', '呼吸困难'),
    ('肺通气功', '咳痰'),
    ('BMI', '呼吸困难'),
}

# COPD合并症/并发症/鉴别诊断：保留小簇并锚定
COPD_MERGED_DISEASES = {
    # 合并症
    '心血管疾病': '合并症',
    '冠心病': '合并症',
    '缺血性心脏病': '合并症',
    '心绞痛': '合并症',
    '心肌梗死': '合并症',
    '心力衰竭': '合并症',
    '心衰': '合并症',
    '心律失常': '合并症',
    '肺心病': '并发症',
    '慢性肺源性心脏病': '并发症',
    '肺动脉高压': '并发症',
    '骨质疏松': '合并症',
    '骨质疏松症': '合并症',
    '骨折': '合并症',
    '糖尿病': '合并症',
    '抑郁症': '合并症',
    '抑郁': '合并症',
    '焦虑症': '合并症',
    '焦虑': '合并症',
    '睡眠障碍': '合并症',
    '失眠': '合并症',
    '肺癌': '合并症',
    '贫血': '合并症',
    '营养不良': '合并症',
    '肌少症': '合并症',
    '高血压': '合并症',
    '代谢综合征': '合并症',
    '胃食管反流病': '合并症',
    '胃食管反流': '合并症',
    '阻塞性睡眠呼吸暂停': '合并症',
    'OSA': '合并症',
    
    # 严重并发症
    '呼吸衰竭': '严重并发症',
    '右心衰竭': '严重并发症',
    '肺栓塞': '并发症',
    '自发性气胸': '并发症',
    '胸腔积液': '并发症',
    
    # 鉴别诊断
    '支气管哮喘': '鉴别诊断',
    '哮喘': '鉴别诊断',
    '支气管扩张': '鉴别诊断',
    '支气管扩张症': '鉴别诊断',
    '肺结核': '鉴别诊断',
    '肺炎': '鉴别诊断',
    '肺结节': '鉴别诊断',
    '肺癌': '合并症',
    
    # 相关疾病
    '慢性支气管炎': '相关疾病',
    '支气管炎': '相关疾病',
    '肺气肿': '相关疾病',
}

# ==================== 读取全部数据 ====================

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

# ==================== 处理逻辑 ====================

kept_rows = []        # 保留的关系
deleted_rows = []     # 删除的关系
anchored_rows = []    # 新增的锚定关系

# 记录已生成的锚定关系，避免重复
anchored_keys = set()

def add_anchor(disease, anchor_type):
    """补充慢阻肺到疾病的锚定关系"""
    key = ('疾病-' + anchor_type, '慢性阻塞性肺疾病', disease)
    if key in anchored_keys:
        return
    anchored_keys.add(key)
    
    relation_type = {
        '合并症': '疾病-并发症',
        '严重并发症': '疾病-并发症',
        '并发症': '疾病-并发症',
        '鉴别诊断': '疾病-并发症',  # 用并发症类型，备注说明
        '相关疾病': '疾病-并发症',
    }.get(anchor_type, '相关')
    
    anchored_rows.append({
        '关系类型': relation_type,
        '头实体': '慢性阻塞性肺疾病',
        '头类型': 'Disease',
        '尾实体': disease,
        '尾类型': 'Disease',
        '头原文': '慢阻肺',
        '尾原文': disease,
        '精简上下文': f'方案B锚定：{disease}是慢阻肺的{anchor_type}',
        '文献编号': '医学知识锚定',
        '匹配类型': 'anchored',
        '审核状态': '保留',
        '修改建议': '',
        '备注': f'由方案B补充锚定边：{disease}为慢阻肺{anchor_type}'
    })

for row in all_rows:
    h = row['头实体']
    t = row['尾实体']
    h_type = row['头类型']
    t_type = row['尾类型']
    rel_type = row['关系类型']
    
    # 判断1: 包含噪声实体 → 删除
    if h in NOISE_ENTITIES or t in NOISE_ENTITIES:
        deleted_rows.append((row, f'含噪声实体: {h if h in NOISE_ENTITIES else t}'))
        continue
    
    # 判断2: 特定噪声关系对 → 删除
    if (h, t) in NOISE_RELATION_PAIRS or (t, h) in NOISE_RELATION_PAIRS:
        deleted_rows.append((row, '方向错误的噪声关系对'))
        continue
    
    # 判断3: cooccur中的同类型关系 → 删除
    if row['_source'] == 'cooccur' and h_type == t_type:
        deleted_rows.append((row, f'cooccur同类型关系({h_type}→{t_type})'))
        continue
    
    # 判断4: 描述性短语 → 删除
    if h in {'反复发生肺炎', '病毒感染', '肺部并发症', '气道炎症'} or \
       t in {'反复发生肺炎', '病毒感染', '肺部并发症', '气道炎症'}:
        deleted_rows.append((row, '描述性短语非标准实体'))
        continue
    
    # 保留该关系
    kept_rows.append(row)
    
    # 判断是否需要补充锚定边
    # 如果头实体是非慢阻肺疾病，且是COPD合并症/并发症/鉴别诊断
    if h_type == 'Disease' and not is_copd(h) and h in COPD_MERGED_DISEASES:
        add_anchor(h, COPD_MERGED_DISEASES[h])
    
    # 如果尾实体是非慢阻肺疾病，且是COPD合并症/并发症/鉴别诊断
    if t_type == 'Disease' and not is_copd(t) and t in COPD_MERGED_DISEASES:
        add_anchor(t, COPD_MERGED_DISEASES[t])

# ==================== 统计与输出 ====================

print("\n" + "=" * 60)
print("方案B执行结果")
print("=" * 60)
print(f"原始关系: {len(all_rows)} 条")
print(f"删除噪声: {len(deleted_rows)} 条")
print(f"保留关系: {len(kept_rows)} 条")
print(f"新增锚定: {len(anchored_rows)} 条")
print(f"最终关系: {len(kept_rows) + len(anchored_rows)} 条")

print("\n" + "=" * 60)
print("【删除的噪声小簇 Top 20】")
print("=" * 60)
for i, (row, reason) in enumerate(deleted_rows[:20], 1):
    print(f"{i:2d}. ({row['头类型']}→{row['尾类型']}) {row['头实体']} → {row['尾实体']}")
    print(f"    原因: {reason}")

print("\n" + "=" * 60)
print("【新增的锚定关系】")
print("=" * 60)
for r in anchored_rows:
    print(f"  慢阻肺 → [{r['关系类型']}] → {r['尾实体']} ({r['备注']})")

# 保存最终文件
final_rows = kept_rows + anchored_rows

# 去重
seen = set()
unique_final = []
for row in final_rows:
    key = (row['关系类型'], row['头实体'], row['尾实体'])
    if key not in seen:
        seen.add(key)
        unique_final.append(row)

output_tsv = os.path.join(OUTPUT_DIR, '最终三元组_方案B_锚定版.tsv')
if unique_final:
    fieldnames = list(unique_final[0].keys())
    with open(output_tsv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(unique_final)
    print(f"\n最终文件已保存: {output_tsv}")
    print(f"去重后最终关系: {len(unique_final)} 条")

# 统计最终各类型关系数量
from collections import Counter
rel_counts = Counter(r['关系类型'] for r in unique_final)
print("\n最终关系类型分布:")
for rel, count in rel_counts.most_common():
    print(f"  {rel}: {count} 条")
