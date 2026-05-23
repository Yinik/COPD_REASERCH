"""
医学审核脚本v3：严格标准
重点处理：疾病-共病（因果关系）、治疗-预防混淆、检查-症状不匹配、中成药笼统
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
        
        # 删除：定义关系（A是B的组成部分/表型）
        if (h == '慢性支气管炎' and tail == '慢性阻塞性肺疾病') or \
           (h == '慢性阻塞性肺疾病' and tail == '慢性支气管炎') or \
           (h == '慢性阻塞性肺疾病' and tail == '支气管炎'):
            return False, "慢性支气管炎是COPD的表型/组成部分，不是共病"
        
        # 删除：因果关系（A导致B）
        causal = {
            ('支气管炎', '肺炎'), ('肺动脉高压', '呼吸衰竭'),
            ('呼吸衰竭', '右心衰竭'), ('慢性阻塞性肺疾病', '肺动脉高压'),
            ('肺动脉高压', '心力衰竭'), ('心力衰竭', '肺栓塞'),
            ('心血管疾病', '心力衰竭'), ('肺炎', '心力衰竭'),
            ('气道炎症', '支气管扩张'), ('气道炎症', '肺癌'),
            ('支气管扩张', '肺癌'), ('肺炎', '肺栓塞'),
            ('鼻后滴流综合征', '鼻窦炎'), ('鼻后滴流综合征', '支气管炎'),
            ('鼻后滴流综合征', 'CVA'), ('CVA', '鼻后滴流综合征'),
            ('慢性阻塞性肺疾病', '肺炎'), ('肺炎', '支气管扩张'),
            ('心力衰竭', '呼吸衰竭'), ('慢性阻塞性肺疾病', '呼吸衰竭'),
            ('气道炎症', '慢性阻塞性肺疾病'), ('支气管炎', '慢性支气管炎'),
            ('支气管炎', '细支气管炎'), ('流行性感冒', '鼻窦炎'),
            ('流行性感冒', '支气管炎'), ('肺栓塞', '肺动脉高压'),
            ('右心衰竭', '肺动脉高压'), ('气道炎症', '肺结核'),
            ('慢性阻塞性肺疾病', '心力衰竭'), ('慢性阻塞性肺疾病', '肺癌'),
            ('肺炎', '慢性阻塞性肺疾病'), ('支气管炎', '呼吸衰竭'),
            ('阻塞性睡眠呼吸暂停', '红细胞增多症'),
            ('胃食管反流', '贫血'), ('胃食管反流', '红细胞增多症'),
            ('肺癌', '肺炎'), ('肺炎', '支气管炎'),
        }
        if (h, tail) in causal or (tail, h) in causal:
            return False, "属于因果关系或并发症，不是共病"
        
        # 删除：病理基础关系
        pathological = {
            ('支气管哮喘', '气道炎症'), ('支气管扩张', '气道炎症'),
            ('支气管炎', '气道炎症'),
        }
        if (h, tail) in pathological or (tail, h) in pathological:
            return False, "属于病理基础关系，不是共病"
        
        # 删除：危险因素关系
        risk_factor = {
            ('慢性阻塞性肺疾病', '肺癌'), ('支气管扩张', '肺癌'),
            ('肺癌', '支气管扩张'), ('糖尿病', '肺结核'),
            ('心血管疾病', '肺动脉高压'),
        }
        if (h, tail) in risk_factor or (tail, h) in risk_factor:
            return False, "属于危险因素关系，不是共病"
        
        # 删除：不会共存的
        incompatible = {
            ('贫血', '红细胞增多症'), ('红细胞增多症', '贫血'),
        }
        if (h, tail) in incompatible:
            return False, "两种疾病不会共存"
        
        # 删除：极罕见
        rare = {
            ('肺癌', '复发性多软骨炎'), ('支气管扩张', '复发性多软骨炎'),
            ('复发性多软骨炎', '变应性鼻炎'), ('心肌梗死', '支气管炎'),
            ('心肌梗死', '肺炎'), ('阻塞性睡眠呼吸暂停', '贫血'),
            ('气道炎症', '胃食管反流'), ('肺癌', '气道炎症'),
        }
        if (h, tail) in rare or (tail, h) in rare:
            return False, "临床上罕见或无明确共病关系"
        
        return True, "医学上可共存"
    
    # ========== 治疗-改善-疾病 ==========
    if r == '治疗-改善-疾病':
        # 删除：预防性措施（疫苗、戒烟）不是治疗
        preventive = {
            ('流感疫苗', '肺炎'), ('流感疫苗', '心力衰竭'),
            ('流感疫苗', '慢性阻塞性肺疾病'), ('戒烟', '肺炎'),
            ('戒烟', '心力衰竭'), ('戒烟', '肺癌'), ('戒烟', '心肌梗死'),
            ('戒烟', '胃食管反流'),
        }
        if (h, tail) in preventive:
            return False, "疫苗/戒烟是预防措施，不是治疗"
        
        # 删除：治疗不针对该疾病
        wrong = {
            ('无创通气', '慢性阻塞性肺疾病'), ('无创通气', '肺炎'),
            ('肺康复', '肺栓塞'), ('肺康复', '肺炎'),
            ('抗感染', '心力衰竭'),
        }
        if (h, tail) in wrong:
            return False, "治疗方法不针对该疾病"
        
        # 删除：中医治疗需辨证论治
        if h in ('补肺', '活血', '益肺灸') and tail == '慢性阻塞性肺疾病':
            return False, "中医治疗需辨证论治，不能笼统归为治疗关系"
        
        return True, "治疗针对该疾病"
    
    # ========== 检查-评估-症状 ==========
    if r == '检查-评估-症状':
        # 删除：检查不用于评估该症状
        wrong = {
            ('线胸片', '慢性咳嗽'), ('线胸片', '咳痰'), ('线胸片', '呼吸困难'),
            ('线胸片', '啰音'), ('线胸片', '变应性咳嗽'), ('线胸片', '胸闷'),
            ('CT', '慢性咳嗽'), ('CT', '咳痰'), ('CT', '呼吸困难'),
            ('CT', '啰音'), ('CT', '心动过速'),
            ('肺功能', '肌肉酸痛'), ('肺功能', '乏力'), ('肺功能', '胸闷'),
            ('血气分析', '呼吸困难'),
            ('超声心动图', '咳痰'),
            ('吸气流速', '呕吐'), ('吸气流速', '啰音'),
            ('肺功能', '肺脾气虚'), ('肺功能', '呕吐'),
            ('心电图', '心动过速'),
            ('BMI', '呼吸困难'),
        }
        if (h, tail) in wrong:
            return False, "该检查不用于评估该症状"
        
        # 保留：中医脉诊
        if h == '脉浮':
            return True, "中医脉诊评估症状"
        
        return True, "检查可评估该症状"
    
    # ========== 检查-辅助诊断-疾病 ==========
    if r == '检查-辅助诊断-疾病':
        # 删除：检查不用于诊断该病
        wrong = {
            ('BMI', '慢性支气管炎'), ('肺功能', '胃食管反流'),
            ('肺功能', '反复发生肺炎'), ('线胸片', 'CVA'),
            ('血常规', 'CVA'), ('肺功能', '肺栓塞'),
            ('线胸片', '复发性多软骨炎'), ('线胸片', '变应性鼻炎'),
            ('肺功能', '气道炎症'), ('肺功能', '支气管炎'),
            ('肺功能', '细支气管炎'), ('CT', '心肌梗死'),
            ('超声心动图', '慢性阻塞性肺疾病'),
        }
        if (h, tail) in wrong:
            return False, "该检查不用于诊断该疾病"
        
        return True, "检查可用于辅助诊断"
    
    # ========== 疾病-症状 ==========
    if r == '疾病-症状':
        # 删除：非典型症状
        wrong = {
            ('心肌梗死', '失眠'), ('心肌梗死', '头晕'),
            ('慢性阻塞性肺疾病', '呕吐'), ('慢性阻塞性肺疾病', '肌肉酸痛'),
        }
        if (h, tail) in wrong:
            return False, "不是该疾病的典型症状"
        
        # 删除：心动过速不是哮喘/支气管炎的"症状"
        if tail == '心动过速' and h in ('支气管哮喘', '支气管炎'):
            return False, "心动过速不是该疾病的典型症状"
        
        return True, "该疾病的典型或常见症状"
    
    # ========== 药物-缓解-症状 ==========
    if r == '药物-缓解-症状':
        # 删除：药物不缓解该症状，甚至加重/引起
        wrong = {
            ('糖皮质激素', '结核中毒症状'), ('抗组胺药物', '结核中毒症状'),
            ('ACEI', '慢性咳嗽'), ('罗氟司特', '呕吐'),
            ('抗菌药物', '抽动性咳嗽'), ('激动剂', '自汗'),
        }
        if (h, tail) in wrong:
            return False, "药物不缓解该症状，甚至引起或加重"
        
        # 删除：中成药过于笼统（无法确认具体药物）
        if h == '中成药' and tail in ('头痛', '咳痰', '胸闷', '喘息', '肌肉酸痛', '气虚', '呼吸困难', '意识障碍', '呕吐'):
            return False, "中成药表述过于笼统，无法确认具体药物及适应症"
        
        return True, "药物可缓解该症状"
    
    # ========== 药物-治疗-疾病 ==========
    if r == '药物-治疗-疾病':
        # 删除：药物不治疗该疾病
        wrong = {
            ('茶碱', '支气管扩张'), ('茶碱', '心力衰竭'),
            ('罗氟司特', '心肌梗死'), ('乙酰半胱氨酸', '心力衰竭'),
            ('促胃动力药', '鼻后滴流综合征'), ('异丙托溴铵', '肺炎'),
            ('减充血剂', 'CVA'), ('布地奈德', '支气管扩张'),
            ('左氧氟沙星', '慢性阻塞性肺疾病'),  # 治疗感染，不是COPD本身
        }
        if (h, tail) in wrong:
            return False, "药物不治疗该疾病"
        
        # 删除：罗氟司特适应症
        if h == '罗氟司特' and tail == '慢性支气管炎':
            return False, "罗氟司特治疗COPD（重度伴慢性支气管炎），不单纯治疗慢性支气管炎"
        
        # 删除：中成药过于笼统
        if h == '中成药' and tail == '慢性阻塞性肺疾病':
            return False, "中成药需辨证论治，不能笼统归为治疗COPD"
        
        return True, "药物可治疗该疾病"
    
    # ========== 治疗-改善-症状 ==========
    if r == '治疗-改善-症状':
        # 删除：不直接改善
        wrong = {
            ('流感疫苗', '呼吸困难'),
        }
        if (h, tail) in wrong:
            return False, "治疗不直接改善该症状"
        
        return True, "治疗可改善该症状"
    
    # ========== 疾病-并发症 ==========
    if r == '疾病-并发症':
        wrong = {
            ('流行性感冒', '非酸反流'), ('胃食管反流', '弱酸反流'),
            ('胃食管反流', '代谢综合征'), ('阻塞性睡眠呼吸暂停', '代谢综合征'),
            ('贫血', '代谢综合征'),
        }
        if (h, tail) in wrong:
            return False, "不属于并发症关系"
        
        return True, "属于并发症"
    
    # ========== 药物-导致-并发症 ==========
    if r == '药物-导致-并发症':
        return True, "药物可导致该并发症"
    
    # ========== 危险因素-疾病 ==========
    if r == '危险因素-疾病':
        # 删除：病原体不是危险因素
        if h in ('肺炎链球菌', '肺炎衣原体', '肺炎支原体'):
            return False, "病原体感染属于因果关系，不是危险因素"
        
        # 删除：过于宽泛不直接相关
        if h == '呼吸道感染' and tail in ('心血管疾病', '流行性感冒', '鼻窦炎'):
            return False, "不属于直接危险因素"
        
        # 删除：因果关系
        if h == '呼吸道感染' and tail == '肺炎':
            return False, "呼吸道感染可导致肺炎，属于因果关系"
        
        return True, "医学上成立的危险因素"
    
    return True, "默认保留"

for t in triples:
    keep, reason = review(t)
    if keep:
        kept.append(t)
    else:
        t['remove_reason'] = reason
        removed.append(t)

print("===== 医学审核结果v3（严格标准）=====")
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
lines.append("医学审核报告v3（严格标准）")
lines.append("=" * 70)
lines.append("")
lines.append("审核原则：")
lines.append("1. 疾病-共病：严格删除因果关系、并发症、病理基础、定义关系")
lines.append("2. 治疗-改善-疾病：删除预防性措施（疫苗、戒烟）")
lines.append("3. 检查-评估-症状：删除不用于评估该症状的检查")
lines.append("4. 药物-缓解-症状：删除中成药过于笼统的、药物引起症状的")
lines.append("5. 记录所有删除理由")
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
