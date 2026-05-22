#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于COPD医学知识自动审核三元组
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

# 慢阻肺的常见症状（正确的疾病-症状关系）
COPD_SYMPTOMS = {
    '慢性咳嗽', '咳痰', '呼吸困难', '气短', '喘息', '胸闷',
    '气促', '活动后气促', '咳嗽', '痰量增多', '脓性痰'
}

# 慢阻肺的常见危险因素（正确的危险因素-疾病关系）
COPD_RISK_FACTORS = {
    '吸烟', '被动吸烟', '二手烟', '空气污染', '大气污染',
    '职业粉尘', '粉尘暴露', '化学物质暴露', '呼吸道感染',
    '儿童期感染', '遗传因素', 'α1抗胰蛋白酶缺乏', '年龄',
    '低体重', '营养不良', '室内空气污染', '生物燃料',
    '吸烟史', '长期吸烟', '重度吸烟', '中重度吸烟'
}

# 治疗慢阻肺的药物（正确的药物-治疗-疾病关系）
COPD_MEDICATIONS = {
    '支气管扩张剂', '长效β2受体激动剂', 'LABA', '短效β2受体激动剂', 'SABA',
    '长效抗胆碱能药物', 'LAMA', '短效抗胆碱能药物', 'SAMA',
    '吸入糖皮质激素', 'ICS', '茶碱', '磷酸二酯酶抑制剂',
    '抗生素', '大环内酯类', '糖皮质激素', '全身糖皮质激素',
    '口服糖皮质激素', '雾化吸入药物', '吸入药物',
    '罗氟司特', 'PDE4抑制剂', '黏液溶解剂', '祛痰药',
    '疫苗', '流感疫苗', '肺炎疫苗', '肺炎球菌疫苗'
}

# 慢阻肺的治疗措施（正确的疾病-治疗关系）
COPD_TREATMENTS = {
    '戒烟', '肺康复', '长期氧疗', '氧疗', '家庭氧疗',
    '呼吸训练', '运动训练', '营养支持', '疫苗接种',
    '手术治疗', '肺减容手术', '肺移植', '无创通气',
    'NIV', '机械通气', '有创机械通气', '支气管镜介入',
    '戒烟干预', '健康教育', '自我管理'
}

# 诊断慢阻肺的检查（正确的检查-辅助诊断-疾病关系）
COPD_EXAMINATIONS = {
    '肺功能', '肺功能检查', '肺通气功能', '支气管舒张试验',
    'FEV1', 'FEV1/FVC', '肺活量', '胸部CT', 'CT',
    '胸部X线', 'X线', 'X线胸片', '血气分析', '动脉血气',
    '血常规', '痰培养', '胸部影像学', '超声心动图',
    '心电图', '6分钟步行试验', '6MWT', 'CAT评分',
    'mMRC评分', 'SGRQ评分'
}

# 慢阻肺的常见并发症（正确的疾病-并发症关系）
COPD_COMPLICATIONS = {
    '心血管疾病', '心绞痛', '心肌梗死', '心力衰竭', '心律失常',
    '肺心病', '慢性肺源性心脏病', '肺动脉高压',
    '骨质疏松', '骨折', '糖尿病', '抑郁症', '焦虑症',
    '睡眠障碍', '肺癌', '呼吸衰竭', '自发性气胸',
    '肺栓塞', '胃食管反流', '反流症状', '贫血',
    '营养不良', '体重下降', '骨骼肌功能障碍',
    '青光眼', '白内障'
}

# 慢阻肺的常见合并症/共病
COPD_COMORBIDITIES = {
    '高血压', '冠心病', '缺血性心脏病', '脑血管病',
    '代谢综合征', '肥胖', '低体重', '肌少症'
}

# 其他与慢阻肺相关的疾病（可能出现在共现中）
COPD_RELATED_DISEASES = {
    '慢性阻塞性肺疾病', '慢阻肺', 'COPD', '慢性支气管炎',
    '肺气肿', '哮喘', '支气管哮喘', '咳嗽变异性哮喘',
    '支气管扩张', '支气管扩张症', '间质性肺病',
    '肺结核', '肺炎', '肺癌', '肺纤维化',
    '急性加重', 'AECOPD', '慢性阻塞性肺疾病急性加重',
    '稳定期', '急性期'
}

# 需要删除的明显错误关系
DELETION_PATTERNS = {
    # 医学常识错误
    ('慢性阻塞性肺疾病', '疾病-治疗', '治愈'),
    ('慢阻肺', '疾病-治疗', '治愈'),
    ('COPD', '疾病-治疗', '治愈'),
    ('慢性阻塞性肺疾病', '疾病-症状', '治愈'),
    # 方向明显错误的（症状不能导致疾病）
    # 这些会在审核逻辑中处理
}

# 关系方向规则：某些尾实体类型暗示方向错误
DIRECTION_ERRORS = {
    # 症状不能作为头实体指向疾病
    # 但这里需要结合具体实体判断
}

# ==================== 审核函数 ====================

def audit_explicit(row):
    """审核explicit关系"""
    relation = row['关系类型']
    head = row['头实体']
    head_type = row['头类型']
    tail = row['尾实体']
    tail_type = row['尾类型']
    context = row.get('精简上下文', '')
    
    status = '保留'
    suggestion = ''
    note = ''
    
    # 1. 疾病-症状关系审核
    if relation == '疾病-症状':
        if head_type == 'Disease' and tail_type == 'Symptom':
            # 检查尾实体是否是COPD的症状
            if tail in COPD_SYMPTOMS:
                status = '保留'
                note = 'COPD常见症状，医学正确'
            elif tail in {'发热', '头痛', '咽痛', '鼻塞'}:
                status = '删除'
                note = f'{tail}不是COPD的特异性症状，可能是呼吸道感染症状'
            elif tail in {'防止过无喘息', '风热犯肺证', '湿热郁肺证', '肺脾阳虚证'}:
                status = '删除'
                note = '截断词或中医证候术语，非标准症状实体'
            else:
                status = '保留'
                note = f'COPD可能伴随{tail}，待确认'
        else:
            status = '删除'
            note = f'方向错误：{head_type}→{tail_type}不符合疾病-症状定义'
    
    # 2. 药物-治疗-疾病关系审核
    elif relation == '药物-治疗-疾病':
        if head_type == 'Medication' and tail_type == 'Disease':
            # 检查头实体是否是COPD治疗药物
            if any(med in head for med in COPD_MEDICATIONS) or head in COPD_MEDICATIONS:
                status = '保留'
                note = 'COPD标准治疗药物'
            elif head in {'抗菌药物', '镇咳药物', '抗胆碱能药物', '糖皮质激素'}:
                # 这些是药物类别，过于宽泛但医学上正确
                status = '保留'
                note = '药物类别，医学正确但建议细化为具体药物'
            elif head in {'中药', '中成药', '汤剂'}:
                status = '保留'
                note = '中医治疗COPD，医学正确'
            else:
                status = '保留'
                note = f'{head}可能用于COPD治疗，待确认'
        else:
            status = '删除'
            note = f'方向错误：{head_type}→{tail_type}不符合药物-疾病定义'
    
    # 3. 危险因素-疾病关系审核
    elif relation == '危险因素-疾病':
        if head_type == 'RiskFactor' and tail_type == 'Disease':
            if any(rf in head for rf in COPD_RISK_FACTORS) or head in COPD_RISK_FACTORS:
                status = '保留'
                note = 'COPD公认危险因素'
            elif head in {'吸烟史', '吸烟指数'}:
                status = '保留'
                note = '吸烟相关危险因素'
            elif head in {'早产', '出生低体重', '儿童期反复下呼吸道感染'}:
                status = '保留'
                note = 'COPD早期生活危险因素'
            else:
                status = '保留'
                note = f'可能是COPD危险因素，待确认'
        else:
            status = '删除'
            note = f'方向错误：{head_type}→{tail_type}不符合危险因素-疾病定义'
    
    # 4. 疾病-治疗关系审核
    elif relation == '疾病-治疗':
        if head_type == 'Disease' and tail_type == 'Treatment':
            if tail in COPD_TREATMENTS:
                status = '保留'
                note = 'COPD标准治疗措施'
            elif tail == '戒烟':
                status = '保留'
                note = 'COPD最重要干预措施'
            elif tail in {'手术', '药物治疗', '吸入治疗'}:
                status = '保留'
                note = 'COPD治疗措施，医学正确'
            else:
                status = '保留'
                note = f'可能是COPD治疗措施，待确认'
        else:
            status = '删除'
            note = f'方向错误：{head_type}→{tail_type}不符合疾病-治疗定义'
    
    # 5. 检查-辅助诊断-疾病关系审核
    elif relation == '检查-辅助诊断-疾病':
        if head_type == 'Examination' and tail_type == 'Disease':
            if any(ex in head for ex in COPD_EXAMINATIONS) or head in COPD_EXAMINATIONS:
                status = '保留'
                note = 'COPD诊断相关检查'
            elif head in {'血常规', 'FEV1较基线变化'}:
                status = '保留'
                note = 'COPD辅助检查或疗效评估指标'
            else:
                status = '保留'
                note = f'可能是COPD相关检查，待确认'
        else:
            status = '删除'
            note = f'方向错误：{head_type}→{tail_type}不符合检查-疾病定义'
    
    # 6. 疾病-并发症关系审核
    elif relation == '疾病-并发症':
        if head_type == 'Disease' and tail_type == 'Complication':
            if tail in COPD_COMPLICATIONS or tail in COPD_COMORBIDITIES:
                status = '保留'
                note = 'COPD常见并发症/合并症'
            elif tail in {'反流症状', '气道反流问卷'}:
                status = '删除'
                note = 'GERD相关术语，非COPD并发症（来自被过滤的GERD文献）'
            elif tail in {'心绞痛', '抑郁症', '糖尿病', '骨质疏松'}:
                status = '保留'
                note = 'COPD常见合并症'
            else:
                status = '保留'
                note = f'可能是COPD并发症，待确认'
        else:
            status = '删除'
            note = f'方向错误：{head_type}→{tail_type}不符合疾病-并发症定义'
    
    else:
        status = '保留'
        note = f'关系类型{relation}，默认保留待确认'
    
    # 通用规则：检查医学常识错误
    if '治愈' in tail or '根治' in tail:
        status = '删除'
        note = 'COPD不可治愈，医学常识错误'
    
    # 检查是否为孤立/噪声实体
    if head in {'防止过无喘息', '气道反流问卷'} or tail in {'防止过无喘息', '气道反流问卷'}:
        status = '删除'
        note = '截断词或噪声实体'
    
    return status, suggestion, note


def audit_cooccur(row):
    """审核cooccur（相关）关系，判断是否可以细化为具体关系"""
    head = row['头实体']
    head_type = row['头类型']
    tail = row['尾实体']
    tail_type = row['尾类型']
    context = row.get('精简上下文', '')
    
    status = '保留'
    suggestion = ''
    note = ''
    
    # 根据实体类型组合判断可能的细化方向
    
    # Disease + Symptom → 疾病-症状
    if head_type == 'Disease' and tail_type == 'Symptom':
        if tail in COPD_SYMPTOMS:
            status = '保留'
            suggestion = '疾病-症状'
            note = f'{tail}是COPD常见症状，建议细化为疾病-症状'
        else:
            status = '删除'
            note = f'{tail}不是COPD标准症状，共现无实际关系'
    
    # Disease + Treatment → 疾病-治疗
    elif head_type == 'Disease' and tail_type == 'Treatment':
        if tail in COPD_TREATMENTS:
            status = '保留'
            suggestion = '疾病-治疗'
            note = f'{tail}是COPD标准治疗措施'
        elif tail == '戒烟':
            status = '保留'
            suggestion = '疾病-治疗'
            note = '戒烟是COPD最重要干预措施'
        else:
            status = '保留'
            note = '可能是COPD治疗措施'
    
    # Medication + Disease → 药物-治疗-疾病
    elif head_type == 'Medication' and tail_type == 'Disease':
        if any(med in head for med in COPD_MEDICATIONS) or head in COPD_MEDICATIONS:
            status = '保留'
            suggestion = '药物-治疗-疾病'
            note = f'{head}是治疗COPD的标准药物'
        else:
            status = '保留'
            note = f'{head}可能用于COPD治疗'
    
    # RiskFactor + Disease → 危险因素-疾病
    elif head_type == 'RiskFactor' and tail_type == 'Disease':
        if any(rf in head for rf in COPD_RISK_FACTORS) or head in COPD_RISK_FACTORS:
            status = '保留'
            suggestion = '危险因素-疾病'
            note = f'{head}是COPD公认危险因素'
        else:
            status = '保留'
            note = f'可能是COPD危险因素'
    
    # Examination + Disease → 检查-辅助诊断-疾病
    elif head_type == 'Examination' and tail_type == 'Disease':
        if any(ex in head for ex in COPD_EXAMINATIONS) or head in COPD_EXAMINATIONS:
            status = '保留'
            suggestion = '检查-辅助诊断-疾病'
            note = f'{head}是COPD诊断相关检查'
        else:
            status = '保留'
            note = f'可能是COPD相关检查'
    
    # Disease + Complication → 疾病-并发症
    elif head_type == 'Disease' and tail_type == 'Complication':
        if tail in COPD_COMPLICATIONS or tail in COPD_COMORBIDITIES:
            status = '保留'
            suggestion = '疾病-并发症'
            note = f'{tail}是COPD常见并发症/合并症'
        elif tail in {'反流症状', '气道反流问卷'}:
            status = '删除'
            note = 'GERD相关，非COPD并发症'
        else:
            status = '保留'
            note = f'可能是COPD并发症'
    
    # Disease + Disease → 可能是并发症或相关疾病
    elif head_type == 'Disease' and tail_type == 'Disease':
        if tail in COPD_COMPLICATIONS or tail in COPD_COMORBIDITIES or tail in COPD_RELATED_DISEASES:
            status = '保留'
            if tail in {'哮喘', '支气管哮喘'}:
                note = '哮喘与COPD常共存（ACO）'
            elif tail in {'慢性支气管炎', '肺气肿'}:
                suggestion = '疾病-并发症'
                note = '慢性支气管炎/肺气肿是COPD的病理基础'
            else:
                note = f'{tail}与COPD相关'
        elif tail in {'肺结核', '鼻窦炎', 'COVID-19', '过敏性肺炎', '囊性纤维化'}:
            status = '删除'
            note = f'{tail}来自非COPD文献，与COPD无直接关联'
        else:
            status = '保留'
            note = '两疾病可能相关'
    
    # Symptom + Symptom → 删除（同类型无意义）
    elif head_type == 'Symptom' and tail_type == 'Symptom':
        status = '删除'
        note = '同类型症状之间无明确关系'
    
    # Medication + Medication → 删除（同类型无意义）
    elif head_type == 'Medication' and tail_type == 'Medication':
        status = '删除'
        note = '同类型药物之间无明确关系'
    
    # 过于宽泛的实体
    elif head in {'抗菌药物', '镇咳药物', '抗胆碱能药物'} and tail_type == 'Disease':
        status = '保留'
        suggestion = '药物-治疗-疾病'
        note = '药物类别，医学正确'
    
    # 噪声实体处理
    elif '防止过无喘息' in head or '防止过无喘息' in tail:
        status = '删除'
        note = '截断词，噪声实体'
    
    # 默认处理
    else:
        status = '保留'
        note = f'{head_type}→{tail_type}共现关系，需人工判断'
    
    return status, suggestion, note


# ==================== 主程序 ====================

def process_file(input_name, output_name, audit_func):
    """处理单个文件"""
    input_path = os.path.join(OUTPUT_DIR, input_name)
    output_path = os.path.join(OUTPUT_DIR, output_name)
    
    # 读取数据
    rows = []
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    print(f"  读取 {len(rows)} 条数据...")
    
    # 逐条审核
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
    
    # 样式
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # 列宽
    col_widths = {
        '关系类型': 16, '头实体': 18, '头类型': 10, '尾实体': 18, '尾类型': 10,
        '头原文': 14, '尾原文': 14, '文献编号': 35, '匹配类型': 10,
        '精简上下文': 50, '审核状态': 10, '修改建议': 16, '备注': 30,
    }
    
    # 写入表头
    for col_idx, col_name in enumerate(fieldnames, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[cell.column_letter].width = col_widths.get(col_name, 15)
    
    # 写入数据
    for row_idx, row_data in enumerate(results, 2):
        for col_idx, col_name in enumerate(fieldnames, 1):
            value = row_data.get(col_name, '')
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            
            # 审核状态颜色
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
    
    # 冻结首行
    ws.freeze_panes = 'A2'
    ws.row_dimensions[1].height = 25
    for r in range(2, len(results) + 2):
        ws.row_dimensions[r].height = 40
    
    # 数据验证
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


# 执行
print("=" * 60)
print("开始基于COPD医学知识自动审核...")
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
print(f"总计: 保留={total_keep} ({total_keep/981*100:.1f}%), 删除={total_del} ({total_del/981*100:.1f}%), 修改={total_mod}")
print("\n生成文件:")
print("  - 医学审核_explicit_高质量.xlsx")
print("  - 医学审核_cooccur_兜底.xlsx")
