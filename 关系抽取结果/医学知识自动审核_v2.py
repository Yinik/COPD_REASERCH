#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于COPD医学知识自动审核三元组 V2（更严格版）
输出审核后的Excel文件
"""
import config  # 统一路径配置

import csv
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

OUTPUT_DIR = 'I:\\101实验专题\\关系抽取结果'

# ==================== COPD医学知识库 ====================

COPD_SYMPTOMS = {
    '慢性咳嗽', '咳痰', '呼吸困难', '气短', '喘息', '胸闷',
    '气促', '活动后气促', '咳嗽', '痰量增多', '脓性痰',
    '咳痰量增多', '夜间咳嗽', '晨间咳嗽'
}

COPD_RISK_FACTORS = {
    '吸烟', '被动吸烟', '二手烟', '空气污染', '大气污染',
    '职业粉尘', '粉尘暴露', '化学物质暴露', '呼吸道感染',
    '儿童期感染', '遗传因素', 'α1抗胰蛋白酶缺乏', '年龄',
    '低体重', '营养不良', '室内空气污染', '生物燃料',
    '吸烟史', '长期吸烟', '重度吸烟', '中重度吸烟',
    '反复发生下呼吸道感染', '儿童时期反复发生下呼吸道感染'
}

COPD_MEDICATIONS = {
    '支气管扩张剂', '长效β2受体激动剂', 'LABA', '短效β2受体激动剂', 'SABA',
    '长效抗胆碱能药物', 'LAMA', '短效抗胆碱能药物', 'SAMA',
    '吸入糖皮质激素', 'ICS', '茶碱', '磷酸二酯酶抑制剂',
    '抗生素', '大环内酯类', '糖皮质激素', '全身糖皮质激素',
    '口服糖皮质激素', '雾化吸入药物', '吸入药物',
    '罗氟司特', 'PDE4抑制剂', '黏液溶解剂', '祛痰药',
    '疫苗', '流感疫苗', '肺炎疫苗', '肺炎球菌疫苗',
    'SABA', 'SAMA', 'LABA', 'LAMA', 'ICS',
    '支气管舒张剂', 'β2受体激动剂', '抗胆碱能药物',
    '孟鲁司特', '白三烯受体拮抗剂', '奥达特罗'
}

COPD_TREATMENTS = {
    '戒烟', '肺康复', '长期氧疗', '氧疗', '家庭氧疗',
    '呼吸训练', '运动训练', '营养支持', '疫苗接种',
    '手术治疗', '肺减容手术', '肺移植', '无创通气',
    'NIV', '机械通气', '有创机械通气', '支气管镜介入',
    '戒烟干预', '健康教育', '自我管理',
    '吸入装置', '雾化治疗', '康复治疗', '运动锻炼',
    '体育锻炼', '呼吸肌训练', '氧疗', '家庭氧疗'
}

COPD_EXAMINATIONS = {
    '肺功能', '肺功能检查', '肺通气功能', '支气管舒张试验',
    'FEV1', 'FEV1/FVC', '肺活量', '胸部CT', 'CT',
    '胸部X线', 'X线', 'X线胸片', '血气分析', '动脉血气',
    '血常规', '痰培养', '胸部影像学', '超声心动图',
    '心电图', '6分钟步行试验', '6MWT', 'CAT评分',
    'mMRC评分', 'SGRQ评分', 'FeNO', '呼出气一氧化氮',
    '痰嗜酸粒细胞', '血嗜酸粒细胞计数'
}

COPD_COMPLICATIONS = {
    '心血管疾病', '心绞痛', '心肌梗死', '心力衰竭', '心律失常',
    '肺心病', '慢性肺源性心脏病', '肺动脉高压',
    '骨质疏松', '骨折', '糖尿病', '抑郁症', '焦虑症',
    '睡眠障碍', '肺癌', '呼吸衰竭', '自发性气胸',
    '肺栓塞', '贫血', '营养不良', '体重下降',
    '骨骼肌功能障碍', '青光眼', '白内障',
    '胃食管反流', '反流性食管炎'
}

COPD_COMORBIDITIES = {
    '高血压', '冠心病', '缺血性心脏病', '脑血管病',
    '代谢综合征', '肥胖', '低体重', '肌少症'
}

COPD_RELATED_DISEASES = {
    '慢性阻塞性肺疾病', '慢阻肺', 'COPD', '慢性支气管炎',
    '肺气肿', '哮喘', '支气管哮喘',
    '支气管扩张', '支气管扩张症',
    '急性加重', 'AECOPD', '慢性阻塞性肺疾病急性加重'
}

# 噪声实体（截断词、非标准术语）
NOISE_ENTITIES = {
    '防止过无喘息', '气道反流问卷', '反流症状',
    '风热犯肺证', '湿热郁肺证', '肺脾阳虚证',
    '变应性咳嗽'
}

# ==================== 审核函数 ====================

def audit_explicit(row):
    """审核explicit关系"""
    relation = row['关系类型']
    head = row['头实体']
    head_type = row['头类型']
    tail = row['尾实体']
    tail_type = row['尾类型']
    
    status = '保留'
    suggestion = ''
    note = ''
    
    # 噪声实体直接删除
    if head in NOISE_ENTITIES or tail in NOISE_ENTITIES:
        return '删除', '', '噪声实体/截断词'
    
    # 医学常识错误
    if '治愈' in tail or '根治' in tail:
        return '删除', '', 'COPD不可治愈，医学常识错误'
    
    # 1. 疾病-症状
    if relation == '疾病-症状':
        if head_type == 'Disease' and tail_type == 'Symptom':
            if tail in COPD_SYMPTOMS:
                status = '保留'
                note = 'COPD常见症状'
            elif tail in {'头痛', '咽痛', '鼻塞', '发热', '肌肉酸痛'}:
                status = '删除'
                note = f'{tail}不是COPD特异性症状，多为上呼吸道感染表现'
            else:
                status = '保留'
                note = f'{tail}可能是COPD伴随症状，待确认'
        else:
            status = '删除'
            note = f'类型不匹配: {head_type}→{tail_type}'
    
    # 2. 药物-治疗-疾病
    elif relation == '药物-治疗-疾病':
        if head_type == 'Medication' and tail_type == 'Disease':
            if any(med in head for med in COPD_MEDICATIONS) or head in COPD_MEDICATIONS:
                status = '保留'
                note = 'COPD标准治疗药物'
            elif head in {'中药', '中成药', '汤剂'}:
                status = '保留'
                note = '中医治疗COPD'
            else:
                status = '保留'
                note = f'{head}可能用于COPD治疗，待确认'
        else:
            status = '删除'
            note = f'类型不匹配: {head_type}→{tail_type}'
    
    # 3. 危险因素-疾病
    elif relation == '危险因素-疾病':
        if head_type == 'RiskFactor' and tail_type == 'Disease':
            if any(rf in head for rf in COPD_RISK_FACTORS) or head in COPD_RISK_FACTORS:
                status = '保留'
                note = 'COPD公认危险因素'
            else:
                status = '保留'
                note = f'可能是COPD危险因素，待确认'
        else:
            status = '删除'
            note = f'类型不匹配: {head_type}→{tail_type}'
    
    # 4. 疾病-治疗
    elif relation == '疾病-治疗':
        if head_type == 'Disease' and tail_type == 'Treatment':
            if tail in COPD_TREATMENTS:
                status = '保留'
                note = 'COPD标准治疗措施'
            elif tail == '戒烟':
                status = '保留'
                note = 'COPD最关键干预措施'
            else:
                status = '保留'
                note = f'可能是COPD治疗措施，待确认'
        else:
            status = '删除'
            note = f'类型不匹配: {head_type}→{tail_type}'
    
    # 5. 检查-辅助诊断-疾病
    elif relation == '检查-辅助诊断-疾病':
        if head_type == 'Examination' and tail_type == 'Disease':
            if any(ex in head for ex in COPD_EXAMINATIONS) or head in COPD_EXAMINATIONS:
                status = '保留'
                note = 'COPD诊断相关检查'
            else:
                status = '保留'
                note = f'可能是COPD相关检查，待确认'
        else:
            status = '删除'
            note = f'类型不匹配: {head_type}→{tail_type}'
    
    # 6. 疾病-并发症
    elif relation == '疾病-并发症':
        if head_type == 'Disease' and tail_type == 'Complication':
            if tail in COPD_COMPLICATIONS or tail in COPD_COMORBIDITIES:
                status = '保留'
                note = 'COPD常见并发症/合并症'
            elif tail in {'反流症状', '气道反流问卷'}:
                status = '删除'
                note = 'GERD相关术语，非COPD核心并发症'
            else:
                status = '保留'
                note = f'可能是COPD并发症，待确认'
        else:
            status = '删除'
            note = f'类型不匹配: {head_type}→{tail_type}'
    
    return status, suggestion, note


def audit_cooccur(row):
    """严格审核cooccur（相关）关系"""
    head = row['头实体']
    head_type = row['头类型']
    tail = row['尾实体']
    tail_type = row['尾类型']
    context = row.get('精简上下文', '')
    
    # 噪声实体直接删除
    if head in NOISE_ENTITIES or tail in NOISE_ENTITIES:
        return '删除', '', '噪声实体/截断词'
    
    # 同类型实体 → 删除（无意义关系）
    if head_type == tail_type:
        return '删除', '', f'同类型({head_type})实体之间无明确关系意义'
    
    # Disease + Symptom
    if head_type == 'Disease' and tail_type == 'Symptom':
        if tail in COPD_SYMPTOMS:
            return '保留', '疾病-症状', f'{tail}是COPD常见症状'
        else:
            return '删除', '', f'{tail}不是COPD标准症状，共现无明确关系'
    
    # Disease + Treatment
    elif head_type == 'Disease' and tail_type == 'Treatment':
        if tail in COPD_TREATMENTS:
            return '保留', '疾病-治疗', f'{tail}是COPD标准治疗措施'
        else:
            return '删除', '', f'{tail}不是COPD标准治疗措施'
    
    # Medication + Disease
    elif head_type == 'Medication' and tail_type == 'Disease':
        if any(med in head for med in COPD_MEDICATIONS) or head in COPD_MEDICATIONS:
            return '保留', '药物-治疗-疾病', f'{head}是COPD治疗药物'
        else:
            return '删除', '', f'{head}不是COPD标准治疗药物'
    
    # RiskFactor + Disease
    elif head_type == 'RiskFactor' and tail_type == 'Disease':
        if any(rf in head for rf in COPD_RISK_FACTORS) or head in COPD_RISK_FACTORS:
            return '保留', '危险因素-疾病', f'{head}是COPD危险因素'
        else:
            return '删除', '', f'{head}不是COPD公认危险因素'
    
    # Examination + Disease
    elif head_type == 'Examination' and tail_type == 'Disease':
        if any(ex in head for ex in COPD_EXAMINATIONS) or head in COPD_EXAMINATIONS:
            return '保留', '检查-辅助诊断-疾病', f'{head}是COPD诊断相关检查'
        else:
            return '删除', '', f'{head}不是COPD标准检查'
    
    # Disease + Complication
    elif head_type == 'Disease' and tail_type == 'Complication':
        if tail in COPD_COMPLICATIONS or tail in COPD_COMORBIDITIES:
            return '保留', '疾病-并发症', f'{tail}是COPD常见并发症'
        else:
            return '删除', '', f'{tail}不是COPD常见并发症'
    
    # Disease + RiskFactor（方向反了，应该是RiskFactor→Disease）
    elif head_type == 'Disease' and tail_type == 'RiskFactor':
        if any(rf in tail for rf in COPD_RISK_FACTORS) or tail in COPD_RISK_FACTORS:
            return '删除', '', f'方向错误：应为({tail}, 危险因素-疾病, {head})'
        else:
            return '删除', '', f'{tail}不是COPD公认危险因素，且方向错误'
    
    # Disease + Medication（方向反了，应该是Medication→Disease）
    elif head_type == 'Disease' and tail_type == 'Medication':
        if any(med in tail for med in COPD_MEDICATIONS) or tail in COPD_MEDICATIONS:
            return '删除', '', f'方向错误：应为({tail}, 药物-治疗-疾病, {head})'
        else:
            return '删除', '', f'方向错误：{tail}不是COPD标准药物'
    
    # Disease + Examination（方向反了，应该是Examination→Disease）
    elif head_type == 'Disease' and tail_type == 'Examination':
        if any(ex in tail for ex in COPD_EXAMINATIONS) or tail in COPD_EXAMINATIONS:
            return '删除', '', f'方向错误：应为({tail}, 检查-辅助诊断-疾病, {head})'
        else:
            return '删除', '', f'方向错误：{tail}不是COPD标准检查'
    
    # Disease + Disease
    elif head_type == 'Disease' and tail_type == 'Disease':
        if tail in COPD_COMPLICATIONS or tail in COPD_COMORBIDITIES:
            return '保留', '疾病-并发症', f'{tail}是COPD常见合并症'
        elif tail in COPD_RELATED_DISEASES:
            return '保留', '', f'{tail}与COPD密切相关'
        elif tail in {'哮喘', '支气管哮喘'}:
            return '保留', '', '哮喘与COPD可共存（ACO）'
        elif tail in {'肺结核', '鼻窦炎', 'COVID-19', '过敏性肺炎', '囊性纤维化'}:
            return '删除', '', f'{tail}来自非COPD文献，与COPD无直接核心关联'
        else:
            return '删除', '', f'{tail}与COPD关联性不明确'
    
    # 其他非核心类型组合（Treatment+Symptom, Examination+Symptom, Medication+Symptom等）
    else:
        return '删除', '', f'{head_type}→{tail_type}不是COPD知识图谱核心关系类型'


# ==================== 主程序 ====================

def process_file(input_name, output_name, audit_func):
    input_path = os.path.join(OUTPUT_DIR, input_name)
    output_path = os.path.join(OUTPUT_DIR, output_name)
    
    rows = []
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    print(f"  读取 {len(rows)} 条数据...")
    
    results = []
    stats = {'保留': 0, '删除': 0, '修改': 0}
    
    for row in rows:
        status, suggestion, note = audit_func(row)
        row['审核状态'] = status
        row['修改建议'] = suggestion
        row['备注'] = note
        results.append(row)
        stats[status] = stats.get(status, 0) + 1
    
    # 生成Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "三元组审核"
    
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    col_widths = {
        '关系类型': 16, '头实体': 18, '头类型': 10, '尾实体': 18, '尾类型': 10,
        '头原文': 14, '尾原文': 14, '文献编号': 35, '匹配类型': 10,
        '精简上下文': 50, '审核状态': 10, '修改建议': 16, '备注': 35,
    }
    
    for col_idx, col_name in enumerate(fieldnames, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = col_widths.get(col_name, 15)
    
    for row_idx, row_data in enumerate(results, 2):
        for col_idx, col_name in enumerate(fieldnames, 1):
            value = row_data.get(col_name, '')
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            
            if col_name == '审核状态':
                if value == '保留':
                    cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                    cell.font = Font(color="006100")
                elif value == '删除':
                    cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                    cell.font = Font(color="9C0006")
                elif value == '修改':
                    cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                    cell.font = Font(color="9C5700")
    
    ws.freeze_panes = 'A2'
    ws.row_dimensions[1].height = 25
    for r in range(2, len(results) + 2):
        ws.row_dimensions[r].height = 45
    
    status_col = None
    for i, h in enumerate(fieldnames):
        if h == '审核状态':
            status_col = i + 1
            break
    if status_col:
        dv = DataValidation(type="list", formula1='"保留,删除,修改"', allow_blank=True)
        last_row = len(results) + 1
        col_letter = ws.cell(row=2, column=status_col).column_letter
        dv.add(f'{col_letter}2:{col_letter}{last_row}')
        ws.add_data_validation(dv)
    
    wb.save(output_path)
    
    print(f"  已生成: {output_name}")
    print(f"  统计: 保留={stats['保留']}, 删除={stats['删除']}, 修改={stats.get('修改', 0)}")
    return stats


print("=" * 60)
print("基于COPD医学知识自动审核 V2（严格版）")
print("=" * 60)

print("\n【1/2】审核 Explicit 高质量文件...")
stats_exp = process_file(
    '待审核_精简版_explicit_高质量.tsv',
    '医学审核_explicit_高质量.xlsx',
    audit_explicit
)

print("\n【2/2】审核 Cooccur 兜底文件...")
stats_coo = process_file(
    '待审核_精简版_cooccur_兜底.tsv',
    '医学审核_cooccur_兜底.xlsx',
    audit_cooccur
)

print("\n" + "=" * 60)
print("审核完成！汇总统计")
print("=" * 60)
total_keep = stats_exp['保留'] + stats_coo['保留']
total_del = stats_exp['删除'] + stats_coo['删除']
total_mod = stats_exp.get('修改', 0) + stats_coo.get('修改', 0)
print(f"Explicit: 保留={stats_exp['保留']}, 删除={stats_exp['删除']}")
print(f"Cooccur:  保留={stats_coo['保留']}, 删除={stats_coo['删除']}")
print(f"总计: 保留={total_keep} ({total_keep/981*100:.1f}%), 删除={total_del} ({total_del/981*100:.1f}%)")
print(f"可细化建议: {total_mod} 条")
print("\n生成文件:")
print("  - 医学审核_explicit_高质量.xlsx")
print("  - 医学审核_cooccur_兜底.xlsx")
