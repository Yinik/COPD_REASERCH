"""
医学审核脚本v2：放宽标准，保留医学上合理的
"""
import json
from collections import defaultdict

with open('output/new_triples.json', 'r', encoding='utf-8') as f:
    triples = json.load(f)

kept = []
removed = []

def review(t):
    h, r, tail = t['head'], t['relation'], t['tail']
    
    # ========== 疾病-共病 ==========
    if r == '疾病-共病':
        if h == tail:
            return False, "自环关系"
        
        # 仅删除：定义关系（A是B的组成部分/表型）
        if (h == '慢性支气管炎' and tail == '慢性阻塞性肺疾病') or \
           (h == '慢性阻塞性肺疾病' and tail == '慢性支气管炎'):
            return False, "慢性支气管炎是COPD的表型，不是共病"
        
        # 仅删除：极罕见组合
        rare = {
            ('肺癌', '复发性多软骨炎'), ('支气管扩张', '复发性多软骨炎'),
            ('复发性多软骨炎', '变应性鼻炎'),
        }
        if (h, tail) in rare or (tail, h) in rare:
            return False, "临床上非常罕见的组合"
        
        # 放宽：因果关系导致的共存也保留（临床上是共存的）
        # 如COPD+肺动脉高压、COPD+心衰、肺炎+心衰等
        return True, "医学上可共存"
    
    # ========== 危险因素-疾病 ==========
    if r == '危险因素-疾病':
        # 删除：病原体不是危险因素
        if h in ('肺炎链球菌', '肺炎衣原体', '肺炎支原体'):
            return False, "病原体感染属于因果关系，不是危险因素"
        # 删除：过于宽泛不直接相关
        if h == '呼吸道感染' and tail == '心血管疾病':
            return False, "呼吸道感染不是心血管疾病的直接危险因素"
        # 删除：流感是呼吸道感染的一种
        if h == '呼吸道感染' and tail == '流行性感冒':
            return False, "流感是呼吸道感染的一种"
        return True, "医学上成立的危险因素"
    
    # ========== 治疗-改善-疾病 ==========
    if r == '治疗-改善-疾病':
        # 删除：明显不针对
        wrong = {
            ('肺康复', '肺栓塞'), ('肺康复', '肺炎'),
            ('抗感染', '心力衰竭'),
            ('无创通气', '肺炎'),
        }
        if (h, tail) in wrong:
            return False, "治疗方法不针对该疾病"
        
        # 放宽：疫苗/戒烟作为预防/管理措施保留
        # 放宽：无创通气用于急性加重保留（COPD/心衰的急性处理）
        # 放宽：中医治疗保留
        return True, "治疗方法针对或管理该疾病"
    
    # ========== 检查-辅助诊断-疾病 ==========
    if r == '疾病-辅助诊断-疾病':
        r = '检查-辅助诊断-疾病'  # 修正可能的错误
    
    if r == '检查-辅助诊断-疾病':
        # 删除：明显错误
        wrong = {
            ('BMI', '慢性支气管炎'),
            ('血常规', 'CVA'),
            ('CT', '心肌梗死'),
            ('超声心动图', '慢性阻塞性肺疾病'),
        }
        if (h, tail) in wrong:
            return False, "该检查不用于诊断该疾病"
        
        # 放宽：肺功能、胸片、CT等影像检查在呼吸疾病诊断中广泛使用
        # 即使不是金标准，也是辅助诊断手段
        return True, "检查可用于辅助诊断该疾病"
    
    # ========== 疾病-症状 ==========
    if r == '疾病-症状':
        # 删除：明显非典型
        wrong = {
            ('慢性阻塞性肺疾病', '呕吐'),
            ('慢性阻塞性肺疾病', '肌肉酸痛'),
        }
        if (h, tail) in wrong:
            return False, "不是该疾病的典型症状"
        
        # 放宽：心梗可伴头晕/失眠（虽然不典型，但可能）；哮喘/支气管炎可伴心动过速
        return True, "该疾病的症状或可能伴随表现"
    
    # ========== 药物-缓解-症状 ==========
    if r == '药物-缓解-症状':
        # 删除：明显错误（药物引起/加重该症状）
        wrong = {
            ('ACEI', '慢性咳嗽'),  # ACEI是慢性咳嗽的常见原因
            ('罗氟司特', '呕吐'),  # 罗氟司特副作用是恶心呕吐
        }
        if (h, tail) in wrong:
            return False, "药物不缓解该症状，甚至引起或加重"
        
        # 放宽：中成药保留（文献可能确实提及）
        # 放宽：抗菌药物用于感染相关咳嗽保留
        return True, "药物可缓解该症状"
    
    # ========== 检查-评估-症状 ==========
    if r == '检查-评估-症状':
        # 删除：明显不相关
        wrong = {
            ('BMI', '呼吸困难'),
            ('吸气流速', '呕吐'),
            ('吸气流速', '啰音'),
            ('肺功能', '肺脾气虚'),
            ('肺功能', '呕吐'),
        }
        if (h, tail) in wrong:
            return False, "该检查不用于评估该症状"
        
        # 放宽：胸片/CT/肺功能在呼吸疾病中是常规评估手段
        # 放宽：心电图评估心动过速保留
        return True, "检查可用于评估该症状"
    
    # ========== 药物-治疗-疾病 ==========
    if r == '药物-治疗-疾病':
        # 删除：明显错误
        wrong = {
            ('茶碱', '心力衰竭'),
            ('罗氟司特', '心肌梗死'),
            ('乙酰半胱氨酸', '心力衰竭'),
            ('促胃动力药', '鼻后滴流综合征'),
            ('减充血剂', 'CVA'),
        }
        if (h, tail) in wrong:
            return False, "药物不治疗该疾病"
        
        # 删除：茶碱→支气管扩张（茶碱治哮喘/COPD，不是"支气管扩张"这个病）
        if h == '茶碱' and tail == '支气管扩张':
            return False, "茶碱治疗的是哮喘/COPD，不是支气管扩张疾病"
        
        # 删除：布地奈德→支气管扩张（同上）
        if h == '布地奈德' and tail == '支气管扩张':
            return False, "布地奈德治疗的是哮喘/COPD，不是支气管扩张疾病"
        
        # 放宽：左氧氟沙星→COPD（AECOPD的抗感染治疗是合理的）
        # 放宽：罗氟司特→慢性支气管炎（罗氟司特说明书适应症：COPD伴慢性支气管炎）
        # 放宽：中成药保留
        return True, "药物可治疗或用于该疾病"
    
    # ========== 治疗-改善-症状 ==========
    if r == '治疗-改善-症状':
        # 删除：不直接相关
        wrong = {
            ('流感疫苗', '呼吸困难'),
        }
        if (h, tail) in wrong:
            return False, "治疗不直接改善该症状"
        
        return True, "治疗可改善该症状"
    
    # ========== 疾病-并发症 ==========
    if r == '疾病-并发症':
        # 删除：不成立
        wrong = {
            ('流行性感冒', '非酸反流'),
            ('胃食管反流', '弱酸反流'),  # 弱酸反流是GERD的分型
            ('胃食管反流', '代谢综合征'),
            ('阻塞性睡眠呼吸暂停', '代谢综合征'),
            ('贫血', '代谢综合征'),
        }
        if (h, tail) in wrong:
            return False, "不属于并发症关系"
        
        return True, "属于并发症"
    
    # ========== 药物-导致-并发症 ==========
    if r == '药物-导致-并发症':
        # 放宽：激素/支扩剂导致高碳酸血症保留（理论上可能）
        return True, "药物可导致该并发症"
    
    return True, "默认保留"

for t in triples:
    keep, reason = review(t)
    if keep:
        kept.append(t)
    else:
        t['remove_reason'] = reason
        removed.append(t)

print("===== 医学审核结果v2（放宽标准）=====")
print(f"原始条数: {len(triples)}")
print(f"保留条数: {len(kept)}")
print(f"删除条数: {len(removed)}")
print()

kept_by_rel = defaultdict(int)
removed_by_rel = defaultdict(int)
for t in kept:
    kept_by_rel[t['relation']] += 1
for t in removed:
    removed_by_rel[t['relation']] += 1

print("各类别统计:")
for rel in sorted(set(list(kept_by_rel.keys()) + list(removed_by_rel.keys()))):
    k = kept_by_rel.get(rel, 0)
    r = removed_by_rel.get(rel, 0)
    print(f"  {rel}: 保留{k}条, 删除{r}条")

# 导出
with open('output/new_triples_reviewed.json', 'w', encoding='utf-8') as f:
    json.dump(kept, f, ensure_ascii=False, indent=2)

with open('output/removed_triples.json', 'w', encoding='utf-8') as f:
    json.dump(removed, f, ensure_ascii=False, indent=2)

import csv
with open('output/new_triples_reviewed.tsv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(['head', 'relation', 'tail', 'head_type', 'tail_type', 'source', 'doc'])
    for t in kept:
        writer.writerow([t['head'], t['relation'], t['tail'], t['head_type'], t['tail_type'], t['source'], t['doc']])

# 生成报告
lines = []
lines.append("=" * 70)
lines.append("医学审核报告v2（放宽标准）")
lines.append("=" * 70)
lines.append("")
lines.append("审核原则：")
lines.append("1. 基于正确医学知识逐条判断")
lines.append("2. 不要太敏感——因果关系导致的共存也保留（临床上确实共存）")
lines.append("3. 影像/肺功能检查与呼吸疾病的关联保留")
lines.append("4. 记录所有删除理由")
lines.append("")
lines.append(f"原始条数: {len(triples)}")
lines.append(f"保留条数: {len(kept)}")
lines.append(f"删除条数: {len(removed)}")
lines.append("")
lines.append("各类别统计:")
for rel in sorted(set(list(kept_by_rel.keys()) + list(removed_by_rel.keys()))):
    k = kept_by_rel.get(rel, 0)
    r = removed_by_rel.get(rel, 0)
    lines.append(f"  {rel}: 保留{k}条, 删除{r}条")

lines.append("")
lines.append("=" * 70)
lines.append("删除详情（按类别）")
lines.append("=" * 70)

for rel in sorted(removed_by_rel.keys()):
    items = [t for t in removed if t['relation'] == rel]
    lines.append("")
    lines.append(f"【{rel}】删除{len(items)}条:")
    for t in items:
        reason = t.get('remove_reason', '')
        lines.append(f"  {t['head']} -> {t['tail']} ({reason})")

with open('output/medical_review_report.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("\n已更新导出文件")
