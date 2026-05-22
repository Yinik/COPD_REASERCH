#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案B-选择2-医学知识细化：不删除"相关"关系，而是基于医学知识逐条细化
"""
import config  # 统一路径配置

import csv
import os
from collections import Counter

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'
INPUT_FILE = '最终三元组_方案B_锚定版.tsv'

# 读取数据
rows = []
with open(os.path.join(OUTPUT_DIR, INPUT_FILE), 'r', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        rows.append(r)

# 分离"相关"关系和非"相关"关系
related_rows = [r for r in rows if r['关系类型'] == '相关']
non_related_rows = [r for r in rows if r['关系类型'] != '相关']

print(f"总关系: {len(rows)}")
print(f"'相关'关系待细化: {len(related_rows)}")
print(f"非'相关'关系: {len(non_related_rows)}")

# ==================== 医学知识细化规则库 ====================

# 1. 上下文关键词 → 关系类型映射（按优先级排序）
CONTEXT_RULES = [
    # 药物-缓解/改善-症状
    ({'缓解', '改善', '减轻', '控制', '降低', '减少', '止咳', '平喘', '祛痰', '化痰', '退热'},
     None, 'Symptom', '药物-缓解-症状'),
    
    # 治疗-改善-症状
    ({'改善', '缓解', '减轻', '康复', '训练', '锻炼'},
     None, 'Symptom', '治疗-改善-症状'),
    
    # 检查-评估/监测-症状/疾病
    ({'评估', '监测', '检查', '评价', '测定', '测量', '显示', '提示', '反映'},
     None, None, '检查-评估-疾病'),
    
    # 危险因素-加重/导致-症状
    ({'加重', '加剧', '恶化', '诱发', '引起', '导致'},
     None, 'Symptom', '危险因素-加重-症状'),
    
    # 药物-导致-并发症（不良反应）
    ({'不良反应', '副作用', '导致', '引起', '增加风险', '易患'},
     'Medication', None, '药物-导致-并发症'),
    
    # 感染-诱发-急性加重
    ({'诱发', '引起', '导致', '加重', '感染'},
     None, None, '诱发-急性加重'),
    
    # 病理-导致-症状
    ({'导致', '引起', '造成', '产生'},
     None, 'Symptom', '病理生理-导致-症状'),
]

# 2. 类型组合 → 关系类型映射（医学常识）
TYPE_RULES = {
    # Medication + Symptom → 药物缓解症状（医学正确）
    ('Medication', 'Symptom'): ('HEAD', '药物-缓解-症状', 'TAIL', False),
    
    # Treatment + Symptom → 治疗改善症状
    ('Treatment', 'Symptom'): ('HEAD', '治疗-改善-症状', 'TAIL', False),
    
    # Examination + Symptom → 检查评估症状
    ('Examination', 'Symptom'): ('HEAD', '检查-评估-症状', 'TAIL', False),
    
    # RiskFactor + Symptom → 危险因素加重症状
    ('RiskFactor', 'Symptom'): ('HEAD', '危险因素-加重-症状', 'TAIL', False),
    
    # Disease + Symptom → 疾病-症状
    ('Disease', 'Symptom'): ('HEAD', '疾病-症状', 'TAIL', False),
    
    # Disease + Treatment → 疾病-治疗
    ('Disease', 'Treatment'): ('HEAD', '疾病-治疗', 'TAIL', False),
    
    # Disease + Medication → 药物-治疗-疾病（反转）
    ('Disease', 'Medication'): ('TAIL', '药物-治疗-疾病', 'HEAD', True),
    
    # Disease + Examination → 检查-辅助诊断-疾病（反转）
    ('Disease', 'Examination'): ('TAIL', '检查-辅助诊断-疾病', 'HEAD', True),
    
    # Disease + RiskFactor → 危险因素-疾病（反转）
    ('Disease', 'RiskFactor'): ('TAIL', '危险因素-疾病', 'HEAD', True),
    
    # Disease + Complication → 疾病-并发症
    ('Disease', 'Complication'): ('HEAD', '疾病-并发症', 'TAIL', False),
    
    # Disease + Disease → 疾病-并发症（合并症）
    ('Disease', 'Disease'): ('HEAD', '疾病-并发症', 'TAIL', False),
    
    # Medication + Disease → 药物-治疗-疾病
    ('Medication', 'Disease'): ('HEAD', '药物-治疗-疾病', 'TAIL', False),
    
    # RiskFactor + Disease → 危险因素-疾病
    ('RiskFactor', 'Disease'): ('HEAD', '危险因素-疾病', 'TAIL', False),
    
    # Examination + Disease → 检查-辅助诊断-疾病
    ('Examination', 'Disease'): ('HEAD', '检查-辅助诊断-疾病', 'TAIL', False),
    
    # Treatment + Disease → 疾病-治疗（反转）
    ('Treatment', 'Disease'): ('TAIL', '疾病-治疗', 'HEAD', True),
    
    # Complication + Disease → 疾病-并发症（反转）
    ('Complication', 'Disease'): ('TAIL', '疾病-并发症', 'HEAD', True),
    
    # Medication + Examination → 药物-影响-检查指标
    ('Medication', 'Examination'): ('HEAD', '药物-影响-检查指标', 'TAIL', False),
    
    # Examination + Treatment → 检查-指导-治疗
    ('Examination', 'Treatment'): ('HEAD', '检查-指导-治疗', 'TAIL', False),
    
    # Medication + Medication → 药物-联合-药物
    ('Medication', 'Medication'): ('HEAD', '药物-联合-药物', 'TAIL', False),
    
    # RiskFactor + RiskFactor → 危险因素-协同-危险因素
    ('RiskFactor', 'RiskFactor'): ('HEAD', '危险因素-协同-危险因素', 'TAIL', False),
    
    # Symptom + Symptom → 症状-伴随-症状
    ('Symptom', 'Symptom'): ('HEAD', '症状-伴随-症状', 'TAIL', False),
    
    # Complication + Complication → 并发症-关联-并发症
    ('Complication', 'Complication'): ('HEAD', '并发症-关联-并发症', 'TAIL', False),
}

# 3. 特殊实体对 → 关系类型
SPECIAL_PAIRS = {
    ('吸烟', '肺癌'): ('吸烟', '危险因素-疾病', '肺癌', False),
    ('吸烟', '心血管疾病'): ('吸烟', '危险因素-疾病', '心血管疾病', False),
    ('吸烟', '慢性阻塞性肺疾病'): ('吸烟', '危险因素-疾病', '慢性阻塞性肺疾病', False),
    ('吸烟', '慢阻肺'): ('吸烟', '危险因素-疾病', '慢阻肺', False),
    ('吸烟', 'COPD'): ('吸烟', '危险因素-疾病', 'COPD', False),
    ('吸烟', '呼吸困难'): ('吸烟', '危险因素-加重-症状', '呼吸困难', False),
    ('吸烟', '咳嗽'): ('吸烟', '危险因素-加重-症状', '咳嗽', False),
    
    ('糖皮质激素', '骨质疏松'): ('糖皮质激素', '药物-导致-并发症', '骨质疏松', False),
    ('糖皮质激素', '糖尿病'): ('糖皮质激素', '药物-导致-并发症', '糖尿病', False),
    ('糖皮质激素', '骨折'): ('糖皮质激素', '药物-导致-并发症', '骨折', False),
    
    ('缺氧', '肺动脉高压'): ('缺氧', '病理生理-导致', '肺动脉高压', False),
    ('肺动脉高压', '右心衰竭'): ('肺动脉高压', '病理生理-导致', '右心衰竭', False),
    ('肺动脉高压', '肺心病'): ('肺动脉高压', '病理生理-导致', '肺心病', False),
    
    ('气流受限', '呼吸困难'): ('气流受限', '病理生理-导致', '呼吸困难', False),
    ('肺过度充气', '呼吸困难'): ('肺过度充气', '病理生理-导致', '呼吸困难', False),
    
    ('呼吸道感染', '急性加重'): ('呼吸道感染', '诱发-急性加重', '急性加重', False),
    ('呼吸道感染', 'AECOPD'): ('呼吸道感染', '诱发-急性加重', 'AECOPD', False),
    ('感染', '急性加重'): ('感染', '诱发-急性加重', '急性加重', False),
    
    ('支气管扩张剂', '呼吸困难'): ('支气管扩张剂', '药物-缓解-症状', '呼吸困难', False),
    ('支气管扩张剂', '喘息'): ('支气管扩张剂', '药物-缓解-症状', '喘息', False),
    ('支气管扩张剂', 'FEV1'): ('支气管扩张剂', '药物-影响-检查指标', 'FEV1', False),
    ('支气管扩张剂', '肺功能'): ('支气管扩张剂', '药物-影响-检查指标', '肺功能', False),
    
    ('LABA', '呼吸困难'): ('LABA', '药物-缓解-症状', '呼吸困难', False),
    ('LAMA', '呼吸困难'): ('LAMA', '药物-缓解-症状', '呼吸困难', False),
    ('ICS', '急性加重'): ('ICS', '药物-减少-急性加重', '急性加重', False),
    
    ('肺康复', '呼吸困难'): ('肺康复', '治疗-改善-症状', '呼吸困难', False),
    ('肺康复', '运动能力'): ('肺康复', '治疗-改善-评估指标', '运动能力', False),
    ('戒烟', '肺功能'): ('戒烟', '治疗-改善-检查指标', '肺功能', False),
    ('戒烟', '急性加重'): ('戒烟', '治疗-减少-急性加重', '急性加重', False),
    
    ('肺功能', '呼吸困难'): ('肺功能', '检查-评估-症状', '呼吸困难', False),
    ('肺功能', '慢阻肺'): ('肺功能', '检查-辅助诊断-疾病', '慢阻肺', False),
    ('肺功能', 'COPD'): ('肺功能', '检查-辅助诊断-疾病', 'COPD', False),
    ('CT', '肺癌'): ('CT', '检查-筛查-疾病', '肺癌', False),
    ('CT', '肺结节'): ('CT', '检查-筛查-疾病', '肺结节', False),
    
    ('糖尿病', '心血管疾病'): ('糖尿病', '疾病-并发症', '心血管疾病', False),
    ('糖尿病', '心绞痛'): ('糖尿病', '疾病-并发症', '心绞痛', False),
    ('糖尿病', '心肌梗死'): ('糖尿病', '疾病-并发症', '心肌梗死', False),
    ('高血压', '心血管疾病'): ('高血压', '疾病-并发症', '心血管疾病', False),
    ('高血压', '心绞痛'): ('高血压', '疾病-并发症', '心绞痛', False),
    
    ('慢性阻塞性肺疾病', '肺癌'): ('慢性阻塞性肺疾病', '疾病-并发症', '肺癌', False),
    ('慢阻肺', '肺癌'): ('慢阻肺', '疾病-并发症', '肺癌', False),
    ('COPD', '肺癌'): ('COPD', '疾病-并发症', '肺癌', False),
    
    ('慢性阻塞性肺疾病', '心血管疾病'): ('慢性阻塞性肺疾病', '疾病-并发症', '心血管疾病', False),
    ('慢阻肺', '心血管疾病'): ('慢阻肺', '疾病-并发症', '心血管疾病', False),
    ('COPD', '心血管疾病'): ('COPD', '疾病-并发症', '心血管疾病', False),
    
    ('空气污染', '慢阻肺'): ('空气污染', '危险因素-疾病', '慢阻肺', False),
    ('空气污染', 'COPD'): ('空气污染', '危险因素-疾病', 'COPD', False),
    ('空气污染', '慢性阻塞性肺疾病'): ('空气污染', '危险因素-疾病', '慢性阻塞性肺疾病', False),
    
    ('职业粉尘', '慢阻肺'): ('职业粉尘', '危险因素-疾病', '慢阻肺', False),
    ('生物燃料', '慢阻肺'): ('生物燃料', '危险因素-疾病', '慢阻肺', False),
    
    ('流感疫苗', '肺炎'): ('流感疫苗', '治疗-预防-疾病', '肺炎', False),
    ('肺炎疫苗', '肺炎'): ('肺炎疫苗', '治疗-预防-疾病', '肺炎', False),
    ('疫苗', '急性加重'): ('疫苗', '治疗-预防-急性加重', '急性加重', False),
}

def refine_relation(row):
    """基于医学知识细化单条'相关'关系"""
    h = row['头实体']
    t = row['尾实体']
    h_type = row['头类型']
    t_type = row['尾类型']
    context = row.get('精简上下文', '')
    
    # 步骤1: 检查特殊实体对
    key = (h, t)
    key_rev = (t, h)
    
    if key in SPECIAL_PAIRS:
        nh, nr, nt, rev = SPECIAL_PAIRS[key]
        return nh, nr, nt, rev, '特殊实体对（医学常识）'
    if key_rev in SPECIAL_PAIRS:
        nh, nr, nt, rev = SPECIAL_PAIRS[key_rev]
        return nh, nr, nt, rev, '特殊实体对（医学常识，反转）'
    
    # 步骤2: 上下文关键词分析
    if context:
        context_str = str(context)
        for keywords, req_h_type, req_t_type, rel_type in CONTEXT_RULES:
            # 检查是否匹配关键词
            matched = sum(1 for kw in keywords if kw in context_str)
            if matched >= 1:
                # 检查类型要求
                type_match = True
                if req_h_type and h_type != req_h_type:
                    type_match = False
                if req_t_type and t_type != req_t_type:
                    type_match = False
                
                if type_match:
                    # 判断是否需要反转
                    reverse = False
                    if h_type == 'Disease' and t_type in {'Medication', 'Examination', 'RiskFactor', 'Treatment'}:
                        reverse = True
                    return h, rel_type, t, reverse, f'上下文关键词（{list(keywords)[0]}...）'
    
    # 步骤3: 类型组合规则
    type_key = (h_type, t_type)
    if type_key in TYPE_RULES:
        rule = TYPE_RULES[type_key]
        if rule is not None:
            new_head_marker, new_rel, new_tail_marker, reverse = rule
            if reverse:
                return t, new_rel, h, True, f'类型组合({h_type}→{t_type})+方向修正'
            else:
                return h, new_rel, t, False, f'类型组合({h_type}→{t_type})'
    
    # 步骤4: 无法细化，保留为相关
    return None, None, None, False, None

# ==================== 执行细化 ====================

refined_rows = []
kept_related = []
refine_log = []

for row in related_rows:
    new_h, new_rel, new_t, reverse, reason = refine_relation(row)
    
    if new_rel is None:
        # 无法细化，保留
        kept_related.append(row)
        refine_log.append((row, '保留为相关', '无法通过医学知识细化'))
    else:
        # 成功细化
        new_row = dict(row)
        new_row['关系类型'] = new_rel
        new_row['备注'] = f'由相关细化为{new_rel}（{reason}）'
        
        if reverse:
            new_row['头实体'] = new_t
            new_row['尾实体'] = new_h
            new_row['头类型'] = row['尾类型']
            new_row['尾类型'] = row['头类型']
            new_row['头原文'] = row['尾原文']
            new_row['尾原文'] = row['头原文']
        else:
            new_row['头实体'] = new_h
            new_row['尾实体'] = new_t
        
        refined_rows.append(new_row)
        refine_log.append((row, f'→ {new_rel}', reason))

# ==================== 统计 ====================

print("\n" + "=" * 60)
print("医学知识细化结果")
print("=" * 60)
print(f"'相关'关系总数: {len(related_rows)}")
print(f"  → 成功细化: {len(refined_rows)} 条")
print(f"  → 保留为相关: {len(kept_related)} 条")
print(f"\n细化后新增关系类型:")

new_type_counts = Counter(r['关系类型'] for r in refined_rows)
for rel, count in new_type_counts.most_common():
    print(f"  {rel}: {count} 条")

print("\n" + "=" * 60)
print("【细化典型案例】（前30条）")
print("=" * 60)

for i, (old_row, action, reason) in enumerate(refine_log[:30], 1):
    print(f"\n{i:2d}. {old_row['头实体']} → [相关] → {old_row['尾实体']}")
    print(f"    类型: {old_row['头类型']}→{old_row['尾类型']}")
    ctx = old_row.get('精简上下文', '')
    if ctx:
        ctx = ctx.encode('utf-8', errors='ignore').decode('utf-8')
    print(f"    上下文: {ctx[:50]}...")
    print(f"    -> {action}")
    print(f"    依据: {reason}")

# ==================== 保存最终文件 ====================

final_rows = non_related_rows + refined_rows + kept_related

# 去重
seen = set()
unique_final = []
for row in final_rows:
    key = (row['关系类型'], row['头实体'], row['尾实体'])
    if key not in seen:
        seen.add(key)
        unique_final.append(row)

# 最终统计
print("\n" + "=" * 60)
print("最终汇总")
print("=" * 60)
print(f"非'相关'关系: {len(non_related_rows)} 条")
print(f"细化后的'相关': {len(refined_rows)} 条")
print(f"保留的'相关': {len(kept_related)} 条")
print(f"去重前总计: {len(non_related_rows) + len(refined_rows) + len(kept_related)} 条")
print(f"去重后总计: {len(unique_final)} 条")

final_type_counts = Counter(r['关系类型'] for r in unique_final)
print("\n最终关系类型分布:")
for rel, count in final_type_counts.most_common():
    pct = count / len(unique_final) * 100
    print(f"  {rel}: {count} 条 ({pct:.1f}%)")

# 保存
output_tsv = os.path.join(OUTPUT_DIR, '最终三元组_方案B_医学细化版.tsv')
if unique_final:
    fieldnames = list(unique_final[0].keys())
    with open(output_tsv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(unique_final)
    print(f"\n最终文件已保存: {output_tsv}")
