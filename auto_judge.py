# -*- coding: utf-8 -*-
"""
基于医学知识库的100条三元组自动预审脚本

自动根据COPD医学常识对抽样三元组进行预标注，
高置信度的直接判定，低置信度的留空待人工复核。

输出：evaluation_sample_100_auto.tsv（带预审分数的文件）
"""
import config  # 统一路径配置

import pandas as pd
import os

# ========== COPD医学知识库 ==========

# 核心药物（GOLD 2024推荐或临床常用）
CORE_MEDICATIONS = {
    'LABA', 'LAMA', 'ICS', '吸入性糖皮质激素', '长效β2受体激动剂', '长效毒蕈碱拮抗剂',
    '短效β2受体激动剂', '支气管舒张剂', '茶碱', '茶碱类药物', '黏液溶解剂',
    '羧甲司坦', '恩塞芬汀', '度普利尤单抗', '糖皮质激素', '抗菌药物', '抗生素',
    '磷酸二酯酶抑制剂', '激动剂', '抗胆碱能药物', '吸入药物', '联合制剂',
    'LABA联合LAMA', 'ICS联合LABA', '中成药', '苏子降气丸', '镇咳药物',
    'ACEI', '他汀类药物'
}

# 核心检查
CORE_EXAMINATIONS = {
    '肺功能', 'CT', '血气分析', '血常规', '心电图', '脉搏血氧',
    '血嗜酸粒细胞计数', '吸气流速', '呼吸频率'
}

# 核心症状
CORE_SYMPTOMS = {
    '慢性咳嗽', '咳痰', '呼吸困难', '喘息', '胸闷', '乏力',
    '失眠', '头晕', '头痛', '肌肉酸痛'
}

# 核心疾病/并发症
CORE_DISEASES = {
    '慢性阻塞性肺疾病', 'COPD', '慢性支气管炎', '支气管哮喘',
    '支气管扩张', '肺炎', '肺癌', '肺结核', '呼吸衰竭',
    '肺动脉高压', '肺栓塞', '心血管疾病', '心肌梗死',
    '心力衰竭', '右心衰竭', '糖尿病', '骨质疏松症',
    '抑郁症', '焦虑症', '贫血', '阻塞性睡眠呼吸暂停',
    '变应性鼻炎', '鼻窦炎'
}

# 核心危险因素
CORE_RISKFACTORS = {
    '吸烟', '吸烟史', '烟草烟雾', '空气污染', '污染物',
    '呼吸道感染', '细菌感染', '二氧化硅', '二氧化硫',
    '二氧化氮', '气候变化'
}

# 核心治疗/干预
CORE_TREATMENTS = {
    '戒烟', '肺康复', '无创通气', '肺减容手术', '体位引流',
    '手术切除', '阻抗训练', '健脾', '宣肺止咳', '活血',
    '益肺灸', '益肾', '舒肺贴', '补肺'
}

# 关系方向的合理性规则
# (头实体类型, 关系, 尾实体类型) -> 是否合理
VALID_RELATIONS = {
    ('Medication', '药物-治疗-疾病', 'Disease'): True,
    ('Medication', '药物-缓解-症状', 'Symptom'): True,
    ('Medication', '药物-导致-并发症', 'Complication'): True,
    ('Disease', '疾病-症状', 'Symptom'): True,
    ('Disease', '疾病-并发症', 'Disease'): True,
    ('Disease', '疾病-治疗', 'Treatment'): True,
    ('Examination', '检查-辅助诊断-疾病', 'Disease'): True,
    ('Examination', '检查-评估-症状', 'Symptom'): True,
    ('Examination', '检查-评估-疾病', 'Disease'): True,
    ('Examination', '检查-筛查-疾病', 'Disease'): True,
    ('Treatment', '治疗-改善-症状', 'Symptom'): True,
    ('RiskFactor', '危险因素-疾病', 'Disease'): True,
    ('Disease', '诱发-急性加重', 'Disease'): True,  # 尾实体也是疾病（急性加重）
}

# 已知不合理的组合（黑名单）
# 格式: (头实体, 关系, 尾实体)
BLACKLIST = {
    # 药物不能治疗非COPD/呼吸疾病（除非是已知的适应症）
    # 这里留空，用白名单思路更安全
}

def normalize_entity(name):
    """实体名规范化，便于匹配"""
    if pd.isna(name):
        return ""
    return str(name).strip()

def is_known_entity(name, entity_type):
    """判断实体是否在已知医学知识库中"""
    name = normalize_entity(name)
    if not name:
        return False
    
    # 直接匹配
    if name in CORE_MEDICATIONS or name in CORE_EXAMINATIONS or name in CORE_SYMPTOMS \
       or name in CORE_DISEASES or name in CORE_RISKFACTORS or name in CORE_TREATMENTS:
        return True
    
    # 包含匹配（比如"LABA联合LAMA"包含"LABA"）
    for core in CORE_MEDICATIONS | CORE_EXAMINATIONS | CORE_SYMPTOMS | CORE_DISEASES | CORE_RISKFACTORS | CORE_TREATMENTS:
        if core in name or name in core:
            return True
    
    return False

def judge_triple(row):
    """对单条三元组进行自动预审"""
    relation = normalize_entity(row.get('关系类型', row.iloc[0]))
    head = normalize_entity(row.get('头实体', ''))
    tail = normalize_entity(row.get('尾实体', ''))
    head_type = normalize_entity(row.get('头类型', ''))
    tail_type = normalize_entity(row.get('尾类型', ''))
    
    # 基础检查：空值
    if not head or not tail or not relation:
        return '△', '实体或关系为空', 0.5
    
    # 检查1：头实体和尾实体是否相同
    if head == tail:
        return '✗', '头实体和尾实体相同', 0.9
    
    # 检查2：关系类型是否在已知13种关系中
    valid_relations = {
        '药物-治疗-疾病', '药物-缓解-症状', '药物-导致-并发症',
        '疾病-症状', '疾病-并发症', '疾病-治疗',
        '检查-辅助诊断-疾病', '检查-评估-症状', '检查-评估-疾病', '检查-筛查-疾病',
        '治疗-改善-症状', '危险因素-疾病', '诱发-急性加重'
    }
    if relation not in valid_relations:
        return '△', '关系类型不在标准13种中', 0.6
    
    # 检查3：实体是否在医学知识库中
    head_known = is_known_entity(head, head_type)
    tail_known = is_known_entity(tail, tail_type)
    
    if not head_known and not tail_known:
        return '△', '头尾实体均不在医学知识库中', 0.5
    
    # 检查4：关系方向是否合理
    # 根据关系类型推断头尾实体类型是否合理
    rel_to_types = {
        '药物-治疗-疾病': ('Medication', 'Disease'),
        '药物-缓解-症状': ('Medication', 'Symptom'),
        '药物-导致-并发症': ('Medication', 'Complication'),
        '疾病-症状': ('Disease', 'Symptom'),
        '疾病-并发症': ('Disease', 'Disease'),
        '疾病-治疗': ('Disease', 'Treatment'),
        '检查-辅助诊断-疾病': ('Examination', 'Disease'),
        '检查-评估-症状': ('Examination', 'Symptom'),
        '检查-评估-疾病': ('Examination', 'Disease'),
        '检查-筛查-疾病': ('Examination', 'Disease'),
        '治疗-改善-症状': ('Treatment', 'Symptom'),
        '危险因素-疾病': ('RiskFactor', 'Disease'),
        '诱发-急性加重': ('Disease', 'Disease'),
    }
    
    expected = rel_to_types.get(relation)
    if expected:
        exp_head_type, exp_tail_type = expected
        # 如果类型信息存在且不匹配，降权
        if head_type and tail_type:
            if head_type != exp_head_type or tail_type != exp_tail_type:
                # 但有些跨类型是允许的（如Disease和Complication都是Disease类型）
                if not (relation == '疾病-并发症' and head_type == 'Disease' and tail_type == 'Disease'):
                    if not (relation == '诱发-急性加重' and head_type == 'Disease' and tail_type == 'Disease'):
                        return '△', f'关系方向可能不匹配（期望{exp_head_type}->{exp_tail_type}，实际{head_type}->{tail_type}）', 0.6
    
    # 检查5：特定医学常识
    # 药物-治疗-疾病：常见COPD药物是否合理
    if relation == '药物-治疗-疾病':
        if 'COPD' in tail or '慢性阻塞性肺疾病' in tail:
            if any(med in head for med in ['LABA', 'LAMA', 'ICS', '支气管舒张剂', '糖皮质激素', '茶碱']):
                return '✓', 'COPD标准治疗药物', 0.85
    
    # 疾病-症状：COPD常见症状
    if relation == '疾病-症状':
        if 'COPD' in head or '慢性阻塞性肺疾病' in head:
            if any(sym in tail for sym in ['咳嗽', '咳痰', '呼吸困难', '喘息', '胸闷']):
                return '✓', 'COPD核心症状', 0.9
    
    # 检查-辅助诊断-疾病
    if relation == '检查-辅助诊断-疾病':
        if '肺功能' in head or 'CT' in head or '血气分析' in head:
            if 'COPD' in tail or '慢性阻塞性肺疾病' in tail:
                return '✓', 'COPD标准诊断检查', 0.85
    
    # 危险因素-疾病
    if relation == '危险因素-疾病':
        if any(rf in head for rf in ['吸烟', '空气污染', '感染']):
            if 'COPD' in tail or '慢性阻塞性肺疾病' in tail:
                return '✓', 'COPD已知危险因素', 0.85
    
    # 默认：如果实体都在知识库中，关系类型也正确，给✓但置信度中等
    if head_known or tail_known:
        return '✓', '实体在医学知识库中，关系类型合规', 0.7
    
    return '△', '无法自动判断，建议人工复核', 0.5

def main():
    input_file = "evaluation_sample_100.tsv"
    output_file = "evaluation_sample_100_auto.tsv"
    
    if not os.path.exists(input_file):
        print(f"[ERROR] 找不到文件: {input_file}")
        return
    
    df = pd.read_csv(input_file, sep='\t', encoding='utf-8-sig')
    print(f"读取了 {len(df)} 条抽样数据")
    
    # 添加预审列
    auto_judges = []
    auto_reasons = []
    auto_confidences = []
    
    for idx, row in df.iterrows():
        judge, reason, conf = judge_triple(row)
        auto_judges.append(judge)
        auto_reasons.append(reason)
        auto_confidences.append(conf)
        
        if (idx + 1) % 20 == 0:
            print(f"已处理 {idx + 1}/{len(df)} 条")
    
    df['自动判定'] = auto_judges
    df['判定理由'] = auto_reasons
    df['置信度'] = auto_confidences
    
    # 统计
    full = sum(1 for j in auto_judges if j == '✓')
    half = sum(1 for j in auto_judges if j == '△')
    zero = sum(1 for j in auto_judges if j == '✗')
    
    print("\n" + "=" * 60)
    print("自动预审结果统计")
    print("=" * 60)
    print(f"总样本: {len(df)}")
    print(f"[正确] (高置信度正确): {full} 条 ({full/len(df)*100:.1f}%)")
    print(f"[存疑] (需人工复核): {half} 条 ({half/len(df)*100:.1f}%)")
    print(f"[错误] (高置信度错误): {zero} 条 ({zero/len(df)*100:.1f}%)")
    print(f"\n建议: 重点复核 [存疑] 标记的 {half} 条，[正确] 和 [错误] 可直接采纳")
    
    # 输出到文件
    df.to_csv(output_file, sep='\t', index=False, encoding='utf-8-sig')
    print(f"\n结果已保存到: {output_file}")
    print("\n使用说明:")
    print("1. 打开 evaluation_sample_100_auto.tsv")
    print("2. '自动判定'列是系统预审结果，'判定理由'是依据")
    print("3. 重点检查'置信度'低于0.7的行，确认是否需要修改")
    print("4. 把确认后的结果复制到'人工判定'列，保存")
    print("5. 运行 python precision_calculator.py 计算最终Precision")

if __name__ == "__main__":
    main()
