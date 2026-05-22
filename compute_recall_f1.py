# -*- coding: utf-8 -*-
"""
基于GOLD 2024核心推荐计算Recall，并结合Precision计算F1

思路：将GOLD 2024的52条核心推荐转化为52个标准三元组（ground truth），
统计实际抽取的675条三元组中覆盖了多少个GOLD三元组，作为Recall的proxy。
"""
import config  # 统一路径配置

import pandas as pd

# ========== GOLD 2024 标准三元组 (ground truth) ==========
# 基于 gold_coverage.py 中的 GOLD_RECOMMENDATIONS 转化

GOLD_TRIPLES = []

# Medication (17条) -> 药物-治疗-疾病 -> COPD
MEDICATIONS = [
    'LABA', 'LAMA', 'ICS', '吸入性糖皮质激素', '短效β2受体激动剂',
    '长效β2受体激动剂', '长效毒蕈碱拮抗剂', '茶碱', '茶碱类药物',
    '黏液溶解剂', '罗氟司特', '恩塞芬汀', '度普利尤单抗',
    '抗菌药物', '抗生素', '糖皮质激素', '吸入药物'
]
for med in MEDICATIONS:
    GOLD_TRIPLES.append({'head': med, 'relation': '药物-治疗-疾病', 'tail': '慢性阻塞性肺疾病'})

# Examination (10条)
EXAMINATIONS = [
    ('肺功能', '检查-辅助诊断-疾病'),
    ('CT', '检查-辅助诊断-疾病'),
    ('血气分析', '检查-评估-疾病'),
    ('血常规', '检查-评估-疾病'),
    ('心电图', '检查-评估-疾病'),
    ('脉搏血氧', '检查-评估-疾病'),
    ('血嗜酸粒细胞计数', '检查-评估-疾病'),
    ('吸气流速', '检查-评估-疾病'),
    ('呼吸频率', '检查-评估-疾病'),
    ('6分钟步行试验', '检查-评估-疾病'),
]
for exam, rel in EXAMINATIONS:
    GOLD_TRIPLES.append({'head': exam, 'relation': rel, 'tail': '慢性阻塞性肺疾病'})

# Symptom (6条) -> COPD-疾病-症状
SYMPTOMS = ['慢性咳嗽', '咳痰', '呼吸困难', '喘息', '胸闷', '乏力']
for sym in SYMPTOMS:
    GOLD_TRIPLES.append({'head': '慢性阻塞性肺疾病', 'relation': '疾病-症状', 'tail': sym})

# RiskFactor (4条)
RISKFACTORS = ['吸烟', '吸烟史', '空气污染', '呼吸道感染']
for rf in RISKFACTORS:
    GOLD_TRIPLES.append({'head': rf, 'relation': '危险因素-疾病', 'tail': '慢性阻塞性肺疾病'})

# Complication (9条) -> COPD-疾病-并发症
COMPLICATIONS = ['心血管疾病', '心肌梗死', '心力衰竭', '右心衰竭', '糖尿病',
                   '骨质疏松症', '抑郁症', '焦虑症', '贫血']
for comp in COMPLICATIONS:
    GOLD_TRIPLES.append({'head': '慢性阻塞性肺疾病', 'relation': '疾病-并发症', 'tail': comp})

# Treatment (6条) -> COPD-疾病-治疗
TREATMENTS = ['戒烟', '肺康复', '无创通气', '肺减容手术', '体位引流', '手术切除']
for trt in TREATMENTS:
    GOLD_TRIPLES.append({'head': '慢性阻塞性肺疾病', 'relation': '疾病-治疗', 'tail': trt})

print(f'GOLD标准三元组总数: {len(GOLD_TRIPLES)}')

# ========== 加载实际抽取的三元组 ==========
df = pd.read_csv('关系抽取结果/方向规范化_疾病统一在头.tsv', sep='\t', encoding='utf-8')

actual_triples = []
for _, row in df.iterrows():
    actual_triples.append({
        'head': str(row.iloc[1]).strip(),
        'relation': str(row.iloc[0]).strip(),
        'tail': str(row.iloc[2]).strip()
    })

print(f'实际抽取三元组总数: {len(actual_triples)}')

# 实体别名映射
ENTITY_ALIASES = {
    '慢性阻塞性肺疾病': ['慢性阻塞性肺疾病', 'COPD', '慢阻肺'],
}

def entity_match(gold_entity, actual_entity):
    """判断两个实体是否匹配（支持别名）"""
    # 直接包含匹配
    if gold_entity in actual_entity or actual_entity in gold_entity:
        return True
    # 别名匹配
    aliases = ENTITY_ALIASES.get(gold_entity, [gold_entity])
    for alias in aliases:
        if alias in actual_entity or actual_entity in alias:
            return True
    return False

# 方向规范化后，部分关系的实际方向与语义方向相反
# 例如"药物-治疗-疾病"在数据中是"疾病→药物"而非"药物→疾病"
REVERSED_RELATIONS = {'药物-治疗-疾病', '检查-辅助诊断-疾病', '检查-评估-疾病', '危险因素-疾病'}

# ========== 匹配函数 ==========
def match_gold_triple(gold, actual_list):
    """判断GOLD三元组是否被实际三元组覆盖"""
    rel = gold['relation']
    is_reversed = rel in REVERSED_RELATIONS
    
    for act in actual_list:
        # 关系类型必须精确匹配
        if act['relation'] != rel:
            continue
        
        if is_reversed:
            # 方向反转的关系：GOLD头→尾 对应 实际尾→头
            head_match = entity_match(gold['head'], act['tail'])
            tail_match = entity_match(gold['tail'], act['head'])
        else:
            # 正常方向的关系
            head_match = entity_match(gold['head'], act['head'])
            tail_match = entity_match(gold['tail'], act['tail'])
        
        if head_match and tail_match:
            return True
    return False

# ========== 计算Recall ==========
matched = 0
matched_details = []
unmatched_details = []

for gold in GOLD_TRIPLES:
    if match_gold_triple(gold, actual_triples):
        matched += 1
        matched_details.append(gold)
    else:
        unmatched_details.append(gold)

recall = matched / len(GOLD_TRIPLES) * 100

print(f'\n匹配结果: {matched}/{len(GOLD_TRIPLES)} = {recall:.1f}%')

# ========== Precision (已计算) ==========
precision = 76.00

# ========== 计算F1 ==========
f1 = 2 * precision * recall / (precision + recall)

print(f'Precision: {precision:.2f}%')
print(f'Recall:    {recall:.2f}%')
print(f'F1:        {f1:.2f}%')

# ========== 输出详细报告 ==========
with open('PRECISION_RECALL_F1_REPORT.md', 'w', encoding='utf-8') as f:
    f.write('# 知识图谱关系抽取 Precision / Recall / F1 评估报告\n\n')
    f.write('## 一、评估方法说明\n\n')
    f.write('### Precision（精确率）\n\n')
    f.write('从675条抽取三元组中随机抽取100条（seed=42），基于COPD医学知识库\n')
    f.write('进行自动预审和人工复核，最终判定76条正确、24条错误。\n\n')
    f.write('**Precision = 76 / 100 = 76.00%**\n\n')
    f.write('> 注：100条样本在95%置信水平下，推断总体Precision约为66%~86%（±10%）。\n\n')
    
    f.write('### Recall（召回率）\n\n')
    f.write('由于缺乏完整的人工标注ground truth，Recall采用**GOLD 2024核心推荐三元组覆盖率**\n')
    f.write('作为proxy指标。具体做法：\n\n')
    f.write('1. 将GOLD 2024的52条核心临床推荐转化为52个标准三元组（ground truth）\n')
    f.write('2. 统计实际抽取的675条三元组中覆盖了多少个GOLD三元组\n\n')
    f.write('转化规则示例：\n')
    f.write('- Medication推荐（如LABA）→ "LABA-药物-治疗-疾病-慢性阻塞性肺疾病"\n')
    f.write('- Symptom推荐（如慢性咳嗽）→ "慢性阻塞性肺疾病-疾病-症状-慢性咳嗽"\n')
    f.write('- RiskFactor推荐（如吸烟）→ "吸烟-危险因素-疾病-慢性阻塞性肺疾病"\n\n')
    f.write(f'**Recall = {matched} / {len(GOLD_TRIPLES)} = {recall:.2f}%**\n\n')
    
    f.write('### F1值\n\n')
    f.write('F1 = 2 × Precision × Recall / (Precision + Recall)\n\n')
    f.write(f'**F1 = 2 × {precision:.2f}% × {recall:.2f}% / ({precision:.2f}% + {recall:.2f}%) = {f1:.2f}%**\n\n')
    
    f.write('---\n\n')
    f.write('## 二、核心指标汇总\n\n')
    f.write('| 指标 | 数值 | 计算方法 |\n')
    f.write('|------|------|----------|\n')
    f.write(f'| Precision | {precision:.2f}% | 100条抽样人工判定 |\n')
    f.write(f'| Recall | {recall:.2f}% | GOLD 2024三元组覆盖率（{matched}/{len(GOLD_TRIPLES)}） |\n')
    f.write(f'| F1 | {f1:.2f}% | 调和平均 |\n\n')
    
    f.write('## 三、GOLD三元组覆盖详情\n\n')
    f.write(f'### 已覆盖（{matched}条）\n\n')
    for g in matched_details:
        f.write(f'- {g["head"]} —{g["relation"]}→ {g["tail"]}\n')
    
    f.write(f'\n### 未覆盖（{len(unmatched_details)}条）\n\n')
    for g in unmatched_details:
        f.write(f'- {g["head"]} —{g["relation"]}→ {g["tail"]}\n')
    
    f.write('\n## 四、局限与说明\n\n')
    f.write('1. **Recall是proxy指标**：GOLD 2024的52条推荐并未穷尽COPD领域所有应抽取的\n')
    f.write('   三元组，实际ground truth可能更大，因此Recall可能被高估。\n')
    f.write('2. **匹配采用宽松策略**：头尾实体采用包含匹配（如"LABA联合LAMA"包含"LABA"即算匹配），\n')
    f.write('   因此Recall可能略高于严格精确匹配的结果。\n')
    f.write('3. **Precision基于抽样**：76%是100条抽样的结果，总体Precision的95%置信区间约为66%~86%。\n')
    f.write('4. **综合结论**：在基于规则的抽取框架下，Precision 76% + Recall {:.1f}% + F1 {:.1f}%\n'
            .format(recall, f1))
    f.write('   的组合表明系统具有较好的精确率和指南对齐度，但仍有优化空间。\n')

print(f'\n详细报告已保存: PRECISION_RECALL_F1_REPORT.md')
