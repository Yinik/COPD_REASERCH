#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于COPD医学知识审查种子词典
输出审查报告和修正后的词典
"""

import csv
import os
from collections import defaultdict

TSV_PATH = 'I:\\101实验专题\\种子词典构建结果\\29_全部中文文献_最终种子词典_严格清理1.tsv'
REPORT_PATH = 'I:\\101实验专题\\种子词典审查报告.txt'
FIXED_TSV_PATH = 'I:\\101实验专题\\种子词典构建结果\\29_种子词典_医学审核修正版.tsv'

# 读取原始数据
with open(TSV_PATH, 'r', encoding='utf-16-le') as f:
    reader = csv.DictReader(f, delimiter='\t')
    rows = list(reader)

# ==================== 医学知识审核规则 ====================

# 1. 应删除的实体（非COPD核心/噪声/截断）
SHOULD_DELETE = {
    # 截断词/噪声
    '防止过无喘息', '镇咳药体激动剂', '反流症酸药物', '糖皮质激素及抗',
    '子类药物加', '雾化吸入利多卡', '镇咳药物分',
    '弱酸反流患者漏诊', '异常非酸反流',
    '引感性咳嗽', '抽动性咳嗽',
    '肺通气功',  # 截断，应为肺通气功能
    
    # GERD相关（来自被过滤的GERD文献）
    '胃酸反流', '反流症状', '胆汁反流', '弱酸反流', '非酸反流',
    '食管反流', '气道反流问卷', '反流性咽喉炎', '促胃动力药',
    '抑酸药物', '胃食管反流', '胃食管反流病',
    
    # COVID相关
    'COVID-19',
    
    # 过于宽泛的描述性短语
    '反复发生肺炎', '病毒感染', '肺部并发症',
    '气道炎症', '鼻窦炎症状', '结核中毒症状',
    '咳嗽加剧', '咳少许白色黏液痰', '咳少量白色黏痰',
    
    # 慢性咳嗽特异性疾病（非COPD核心）
    '躯体性咳敏综合征', '气道神经源性炎症', '鼻后滴流综合征',
    'PNDS', 'EB', 'CVA',  # 这些是慢性咳嗽病因，在COPD文献中只是鉴别诊断
    
    # 过于具体的病原体
    '肺炎链球菌', '肺炎支原体', '肺炎衣原体', '流感病毒', '不动杆菌感染',
    
    # 其他非核心
    '复发性多软骨炎', '细支气管炎', '迁延性支气管炎',
}

# 2. 类型错误的实体及其正确类型
TYPE_ERRORS = {
    # 检查/体征被标为其他类型
    '线胸片': ('Examination', 'X线胸片'),  # 当前在Medication，应为检查
    '呼吸频率': ('Examination', '呼吸频率'),  # 当前在Examination，但更像体征，可保留
    'BMI': ('Examination', 'BMI'),  # 体格指标，保留在Examination可接受
    '吸气流速': ('Examination', '吸气流速'),  # 肺功能参数，保留
    '吸气峰流速': ('Examination', '吸气峰流速'),  # 同上
    'FEV1较基线变化': ('Examination', 'FEV1较基线变化'),  # 疗效指标，保留
    
    # 治疗措施被标为危险因素
    '抗感染': ('Treatment', '抗感染治疗'),  # 当前在RiskFactor
    
    # 药物被标为症状
    '中成药': ('Medication', '中成药'),  # 当前在Symptom
    
    # 中医证候被标为症状（应删除或单独分类）
    '肺脾阳虚证': ('DELETE', ''),
    '湿热郁肺证': ('DELETE', ''),
    '风寒袭肺': ('DELETE', ''),
    '肺脾气虚': ('DELETE', ''),
    '气虚': ('DELETE', ''),
    '祛邪': ('DELETE', ''),
    '脉浮': ('DELETE', ''),
    
    # 中医治疗原则被标为Treatment
    '宣肺止咳': ('DELETE', ''),  # 中医治法，非标准治疗措施
    '益肾': ('DELETE', ''),
    '活血': ('DELETE', ''),
    '补肺': ('DELETE', ''),
    '健脾': ('DELETE', ''),
    '舒肺贴': ('DELETE', ''),  # 具体中成药外治，过于具体
    '益肺灸': ('DELETE', ''),
    
    # 体征/评估指标被标为Treatment
    '运动能力': ('DELETE', ''),  # 这是评估指标，不是治疗
    
    # 过于宽泛的药物类别
    '抗菌药物': ('Medication', '抗菌药物'),  # 保留但备注：过于宽泛
    '镇咳药物': ('Medication', '镇咳药物'),
    '抗胆碱能药物': ('Medication', '抗胆碱能药物'),
    '生物制剂': ('Medication', '生物制剂'),
    '糖皮质激素': ('Medication', '糖皮质激素'),
    '激动剂': ('Medication', '激动剂'),
    '联合制剂': ('Medication', '联合制剂'),
    '免疫调节剂': ('Medication', '免疫调节剂'),
    '受体阻断剂': ('Medication', '受体阻断剂'),
    '精神类药物': ('Medication', '精神类药物'),
    '吸入药物': ('Medication', '吸入药物'),
    '口服抗菌药物': ('Medication', '口服抗菌药物'),
    '茶碱类药物': ('Medication', '茶碱类药物'),
    '第一代抗组胺药物': ('Medication', '第一代抗组胺药物'),
    '抗组胺药物': ('Medication', '抗组胺药物'),
    '非依赖性镇咳药': ('Medication', '非依赖性镇咳药'),
    '非麻醉性镇咳药': ('Medication', '非麻醉性镇咳药'),
    '中枢性镇咳药': ('Medication', '中枢性镇咳药'),
    '依赖性镇咳药': ('Medication', '依赖性镇咳药'),
    '减充血剂': ('Medication', '减充血剂'),
    
    # 药物组合方案（不是具体药物）
    'LABA联合LAMA': ('DELETE', ''),  # 是方案不是药物
    'ICS联合LABA': ('DELETE', ''),
    
    # 症状被标为疾病
    '支气管炎': ('Disease', '支气管炎'),  # 可保留，但注意与慢性支气管炎区分
}

# 3. 需要合并的重复实体
DUPLICATES = {
    '胃食管反流': '胃食管反流病',  # 合并为胃食管反流病
    '鼻后滴流综合征': 'PNDS',  # 两者重复
}

# ==================== 执行审核 ====================

fixed_rows = []
deleted_rows = []
modified_rows = []
issues = defaultdict(list)

for row in rows:
    std_term = row.get('标准术语', '')
    alias = row.get('同义词', '')
    etype = row.get('类型', '')
    
    # 判断1: 是否应删除
    if std_term in SHOULD_DELETE:
        reason = ''
        if std_term in {'防止过无喘息', '镇咳药体激动剂', '反流症酸药物', '糖皮质激素及抗', '子类药物加', '雾化吸入利多卡', '镇咳药物分', '肺通气功'}:
            reason = '截断词/噪声实体'
        elif std_term in {'胃酸反流', '反流症状', '胆汁反流', '弱酸反流', '非酸反流', '食管反流', '气道反流问卷', '反流性咽喉炎', '促胃动力药', '抑酸药物', '胃食管反流', '胃食管反流病'}:
            reason = 'GERD相关噪声（来自非COPD文献）'
        elif std_term == 'COVID-19':
            reason = 'COVID-19，非COPD核心实体'
        elif std_term in {'反复发生肺炎', '病毒感染', '肺部并发症', '气道炎症', '鼻窦炎症状', '结核中毒症状', '咳嗽加剧', '咳少许白色黏液痰', '咳少量白色黏痰'}:
            reason = '描述性短语，非标准医学实体'
        elif std_term in {'躯体性咳敏综合征', '气道神经源性炎症'}:
            reason = '慢性咳嗽特异性实体，非COPD核心'
        elif std_term in {'鼻后滴流综合征', 'PNDS', 'EB', 'CVA'}:
            reason = '慢性咳嗽病因，在COPD中仅作鉴别诊断'
        elif std_term in {'肺炎链球菌', '肺炎支原体', '肺炎衣原体', '流感病毒', '不动杆菌感染'}:
            reason = '病原体，非疾病实体'
        elif std_term in {'复发性多软骨炎', '细支气管炎', '迁延性支气管炎'}:
            reason = '罕见病或非COPD相关疾病'
        else:
            reason = '非COPD核心实体'
        
        deleted_rows.append((row, reason))
        issues['删除'].append((std_term, etype, reason))
        continue
    
    # 判断2: 类型错误
    if std_term in TYPE_ERRORS:
        correct_type, correct_name = TYPE_ERRORS[std_term]
        if correct_type == 'DELETE':
            reason = '中医证候/治法，不适合COPD西医知识图谱'
            if std_term in {'运动能力'}:
                reason = '评估指标，不是治疗措施'
            elif std_term in {'LABA联合LAMA', 'ICS联合LABA'}:
                reason = '药物治疗方案，不是具体药物'
            deleted_rows.append((row, reason))
            issues['删除'].append((std_term, etype, reason))
            continue
        else:
            old_type = etype
            row['类型'] = correct_type
            if correct_name:
                row['标准术语'] = correct_name
            modified_rows.append((row, old_type, correct_type, f'类型修正: {old_type}→{correct_type}'))
            issues['类型错误'].append((std_term, old_type, correct_type, f'应为{correct_type}'))
            fixed_rows.append(row)
            continue
    
    # 判断3: 其他问题
    # 中医症状
    if std_term in {'自汗', '脉浮'} and etype == 'Symptom':
        deleted_rows.append((row, '中医特有症状，不适合COPD西医知识图谱'))
        issues['删除'].append((std_term, etype, '中医特有症状'))
        continue
    
    # 过于宽泛的药物（保留但标记）
    if etype == 'Medication' and std_term in {'抗菌药物', '镇咳药物', '抗胆碱能药物', '糖皮质激素', '激动剂'}:
        issues['警告'].append((std_term, etype, '药物类别过于宽泛，建议细化为具体药物'))
    
    # 默认保留
    fixed_rows.append(row)

# ==================== 生成报告 ====================

with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("COPD种子词典 — 医学知识审查报告\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"原始词典: 185 条实体\n")
    f.write(f"审核后保留: {len(fixed_rows)} 条\n")
    f.write(f"删除: {len(deleted_rows)} 条\n")
    f.write(f"修改类型: {len([m for m in modified_rows if m[1] != m[2]])} 条\n\n")
    
    # 问题分类统计
    f.write("=" * 80 + "\n")
    f.write("【问题分类统计】\n")
    f.write("=" * 80 + "\n\n")
    
    for category, items in issues.items():
        f.write(f"◆ {category}（{len(items)} 条）\n")
        f.write("-" * 60 + "\n")
        for item in items[:20]:
            if category == '删除':
                f.write(f"  {item[0]} [{item[1]}] → {item[2]}\n")
            elif category == '类型错误':
                f.write(f"  {item[0]}: {item[1]} → {item[2]} ({item[3]})\n")
            else:
                f.write(f"  {item[0]} [{item[1]}]: {item[2]}\n")
        if len(items) > 20:
            f.write(f"  ... 等共 {len(items)} 条\n")
        f.write("\n")
    
    # 详细删除列表
    f.write("=" * 80 + "\n")
    f.write("【删除实体详细列表】\n")
    f.write("=" * 80 + "\n\n")
    
    # 按原因分组
    del_by_reason = defaultdict(list)
    for row, reason in deleted_rows:
        del_by_reason[reason].append(row['标准术语'])
    
    for reason, terms in sorted(del_by_reason.items(), key=lambda x: -len(x[1])):
        f.write(f"\n{reason}（{len(terms)} 条）:\n")
        for t in terms:
            f.write(f"  - {t}\n")
    
    # 修正后各类型统计
    f.write("\n" + "=" * 80 + "\n")
    f.write("【修正后各类型统计】\n")
    f.write("=" * 80 + "\n\n")
    
    by_type_fixed = defaultdict(list)
    for r in fixed_rows:
        by_type_fixed[r['类型']].append(r)
    
    for t in sorted(by_type_fixed.keys()):
        items = by_type_fixed[t]
        f.write(f"【{t}】共 {len(items)} 条\n")
        for r in items:
            std = r['标准术语']
            alias = r.get('同义词', '')
            if alias and alias != '-':
                f.write(f"  {std} (别名: {alias})\n")
            else:
                f.write(f"  {std}\n")
        f.write("\n")
    
    # 保留但需关注的实体
    f.write("=" * 80 + "\n")
    f.write("【保留但需关注的实体】\n")
    f.write("=" * 80 + "\n\n")
    f.write("以下实体医学上正确但存在局限性，建议后续优化:\n\n")
    f.write("1. 过于宽泛的药物类别（建议细化为具体药物）:\n")
    for t in ['抗菌药物', '镇咳药物', '抗胆碱能药物', '糖皮质激素', '茶碱类药物', '免疫调节剂']:
        f.write(f"   - {t}\n")
    f.write("\n2. 中医相关实体（如保留需单独分类）:\n")
    f.write("   - 肺康复中包含中医元素，但'补肺''健脾'等是治法原则\n")
    f.write("\n3. 合并症/鉴别诊断实体（非COPD特有但医学上相关）:\n")
    for t in ['肺结核', '肺栓塞', '支气管哮喘', '肺癌']:
        f.write(f"   - {t}\n")

# 保存修正后的TSV
with open(FIXED_TSV_PATH, 'w', encoding='utf-16-le', newline='') as f:
    if fixed_rows:
        fieldnames = fixed_rows[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(fixed_rows)

print(f"审查报告已生成: {REPORT_PATH}")
print(f"修正后词典已生成: {FIXED_TSV_PATH}")
print(f"\n统计:")
print(f"  原始: {len(rows)} 条")
print(f"  保留: {len(fixed_rows)} 条")
print(f"  删除: {len(deleted_rows)} 条")
print(f"  修改类型: {len(modified_rows)} 条")
