# -*- coding: utf-8 -*-
"""
COPD医学文本关系抽取系统 v4 — 最大覆盖版
改进目标: 最小化孤立实体
策略:
  1. 保留咳嗽指南(COPD与慢性咳嗽高度重叠)
  2. 增加兜底"相关"关系
  3. 增加病理/概念关系
  4. 放宽距离限制
  5. 跨句匹配
"""
import config  # 统一路径配置


import os
import re
import csv
import json
from collections import defaultdict

SEED_DICT_PATH = str(config.BASE_DIR / r"种子词典构建结果\29_全部中文文献_最终种子词典_严格清理1.tsv")
TEXT_DIR = str(config.BASE_DIR / r"抽取结果\cleaned_texts")
OUTPUT_DIR = str(config.BASE_DIR / r"关系抽取结果")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================== 改进1: 更精细的文献筛选 ====================
# 策略: 只过滤明显非COPD的文献(GERD/COVID/囊性纤维化/胸外科等)
# 保留咳嗽指南(因为COPD患者常有慢性咳嗽,咳嗽指南中的很多实体对COPD也适用)
NON_COPD_BLACKLIST = [
    'GERD', '胃食管反流', 'COVID', '新冠', 
    '囊性纤维化', 'cystic-fibrosis', '胸外科', 'thoracic',
    'Miller', '肺血栓', '支气管扩张症临床疗效',
    'Long-term-outcomes', '3-year-outcomes', 'Patterns-of-respiratory-infections',
]

def is_copd_core_document(filename):
    for kw in NON_COPD_BLACKLIST:
        if kw.lower() in filename.lower():
            return False, f'非COPD:{kw}'
    # 保留中文文献和COPD相关英文文献
    if re.search(r'[\u4e00-\u9fff]', filename):
        return True, '中文文献'
    if any(kw in filename for kw in ['COPD', 'GOLD', 'chronic', 'obstructive']):
        return True, 'COPD英文'
    return False, '英文/非核心'

# ==================== 模块1: 种子词典 ====================
class SeedDictionary:
    def __init__(self, tsv_path):
        self.term2type = {}
        self.term2standard = {}
        self.all_terms = []
        self._load(tsv_path)
        print(f"[词典] 标准:{len(self.term2type)} 别名:{len(self.term2standard)} 总匹配:{len(self.all_terms)}")
    
    def _load(self, path):
        with open(path, 'rb') as f:
            raw = f.read()
        if raw.startswith(b'\xff\xfe'):
            text = raw.decode('utf-16-le')
        else:
            text = raw.decode('utf-8-sig')
        from io import StringIO
        reader = csv.DictReader(StringIO(text), delimiter='\t')
        term_set = set()
        for row in reader:
            std = row['标准术语'].strip()
            typ = row['类型'].strip()
            alias_str = row['同义词'].strip()
            self.term2type[std] = typ
            term_set.add(std)
            if alias_str and alias_str != '-':
                for alias in alias_str.split('、'):
                    alias = alias.strip()
                    if alias:
                        self.term2standard[alias] = std
                        term_set.add(alias)
        self.all_terms = sorted(term_set, key=len, reverse=True)
    
    def get_std(self, word):
        return self.term2standard.get(word, word)
    
    def get_type(self, word):
        return self.term2type.get(self.get_std(word), 'Unknown')
    
    def match(self, text):
        entities = []
        i, n = 0, len(text)
        while i < n:
            found = False
            for term in self.all_terms:
                if text.startswith(term, i):
                    entities.append((i, i+len(term), term, self.get_std(term), self.get_type(term)))
                    i += len(term)
                    found = True
                    break
            if not found:
                i += 1
        if not entities:
            return []
        entities.sort(key=lambda x: (x[0], -(x[1]-x[0])))
        result = [entities[0]]
        for e in entities[1:]:
            if e[0] >= result[-1][1]:
                result.append(e)
        return result


# ==================== 模块2: 关系规则(6类明确+兜底) ====================

EXPLICIT_RULES = [
    ('疾病-症状', 'Disease', 'Symptom', [
        r'{A}.*?(主要症状|可出现|常伴有|表现为|常见症状|主要表现|临床症状|典型症状).*?{B}',
        r'{B}.*?(是|为|提示|见于|考虑|可见于).*?{A}',
        r'患有.*?{A}.*?出现.*?{B}',
        r'{A}.*?患者.*?{B}',
        r'{A}.*?伴.*?{B}',
    ]),
    ('药物-治疗-疾病', 'Medication', 'Disease', [
        r'{A}.*?(用于|治疗|改善|控制|缓解).*?{B}',
        r'治疗.*?{B}.*?(给予|使用|推荐|选择|应用).*?{A}',
        r'{B}.*?患者.*?(使用|给予|应用).*?{A}',
        r'{A}.*?(是|为).*?{B}.*?(一线|首选|标准)',
        r'{A}.*?(可|能).*?治疗.*?{B}',
    ]),
    ('检查-辅助诊断-疾病', 'Examination', 'Disease', [
        r'{A}.*?(诊断|评估|检查|监测|评价).*?{B}',
        r'诊断.*?{B}.*?(需|应|行|依据|结合).*?{A}',
        r'{B}.*?进行.*?{A}',
        r'{A}.*?(有助于|用于|可).*?(诊断|鉴别|评估).*?{B}',
    ]),
    ('疾病-并发症', 'Disease', 'Complication', [
        r'{A}.*?(合并|并发|导致|引起|继发|诱发).*?{B}',
        r'{B}.*?(是|为).*?{A}.*?(并发症|合并症)',
        r'{A}.*?患者.*?(发生|出现|易).*?{B}',
        r'{A}.*?(与|和).*?{B}.*?(相关|有关)',
    ]),
    ('疾病-治疗', 'Disease', 'Treatment', [
        r'{A}.*?(患者|应|可|需|建议|推荐|给予|使用|采用|进行|接受|联合).*?{B}',
        r'{B}.*?(用于|治疗|改善|控制|缓解|是).*?{A}',
        r'对.*?{A}.*?{B}',
        r'{A}.*?合并.*?{B}',
        r'{B}.*?(可|能).*?减轻.*?{A}',
        r'{B}.*?(可|能).*?改善.*?{A}',
    ]),
    ('危险因素-疾病', 'RiskFactor', 'Disease', [
        r'{A}.*?(增加|导致|引起|诱发|是|为).*?{B}.*?(危险|风险|病因|原因)',
        r'{B}.*?(与|和).*?{A}.*?(相关|有关|密切|明确)',
        r'{A}.*?(是|为).*?{B}.*?(重要|主要|常见).*?(因素|原因)',
        r'{B}.*?(危险|风险|高危).*?{A}',
        r'暴露于.*?{A}.*?{B}',
        r'{A}.*?(与|和).*?{B}.*?(发生|发展|进展)',
        r'{B}.*?(患者|人群).*?{A}',
    ]),
    # 新增: 疾病-病理
    ('疾病-病理', 'Disease', 'Pathology', [
        r'{A}.*?(出现|存在|伴有|导致|引起).*?{B}',
        r'{B}.*?(是|为).*?{A}.*?(特征|表现|病理|机制)',
        r'{A}.*?(与|和).*?{B}.*?(相关|有关)',
        r'{B}.*?(见于|见于).*?{A}',
    ]),
    # 新增: 疾病-概念
    ('疾病-概念', 'Disease', 'Concept', [
        r'{A}.*?(增加|降低|改善|影响).*?{B}',
        r'{B}.*?(是|为).*?{A}.*?(指标|标志)',
        r'{A}.*?(与|和).*?{B}.*?(相关|有关)',
    ]),
]

# 兜底关系: 允许的类型对(用于共现匹配)
COOCCUR_ALLOWED_PAIRS = [
    ('Disease', 'Symptom'),
    ('Disease', 'Medication'),
    ('Disease', 'Examination'),
    ('Disease', 'Complication'),
    ('Disease', 'Treatment'),
    ('Disease', 'RiskFactor'),
    ('Disease', 'Pathology'),
    ('Disease', 'Concept'),
    ('Medication', 'Symptom'),
    ('Examination', 'Symptom'),
    ('Treatment', 'Symptom'),
]

# ==================== 模块3: 工具函数 ====================
NOISE_KEYWORDS = [
    '[PAGE__NO_TEXT]', '内容目录', '目录', '免责声明', '基金项目',
    '通讯作者', '参考文献', '版权声明', '版权所有', '页码',
    'Table of Contents', 'CONTENTS', 'Figure', 'Table',
    '收稿日期', '修回日期', 'DOI:', 'doi:', 'http',
]

def is_noise_sentence(sentence):
    for kw in NOISE_KEYWORDS:
        if kw in sentence:
            return True
    if len(sentence) > 300:
        return True
    if len(sentence) < 15:
        return True
    if sentence.isdigit():
        return True
    en_num = sum(1 for c in sentence if c.isascii())
    if len(sentence) > 20 and en_num / len(sentence) > 0.6:
        return True
    return False

def split_sentences(text):
    parts = re.split(r'([。！？；])', text)
    sentences = []
    cur = ""
    for p in parts:
        cur += p
        if p in '。！？；':
            s = cur.strip()
            if len(s) > 12 and not is_noise_sentence(s):
                sentences.append(s)
            cur = ""
    if cur.strip() and len(cur.strip()) > 12 and not is_noise_sentence(cur.strip()):
        sentences.append(cur.strip())
    return sentences


def extract_from_sentence(sentence, entities, doc_id, explicit_only=False):
    """
    抽取关系
    explicit_only: True=只抽取明确模板关系, False=也抽取兜底共现关系
    """
    triples = []
    matched_pairs = set()  # 记录已匹配的实体对,避免兜底重复
    
    by_type = defaultdict(list)
    for e in entities:
        by_type[e[4]].append(e)
    
    # Step 1: 明确规则匹配
    for rel_name, type_a, type_b, templates in EXPLICIT_RULES:
        list_a = by_type.get(type_a, [])
        list_b = by_type.get(type_b, [])
        if not list_a or not list_b:
            continue
        
        for ea in list_a:
            for eb in list_b:
                if ea[3] == eb[3]:
                    continue
                dist = min(abs(ea[1]-eb[0]), abs(eb[1]-ea[0]))
                if dist > 120:  # 改进: 放宽到120字符
                    continue
                
                matched = False
                for tmpl in templates:
                    pat1 = tmpl.format(A=re.escape(ea[3]), B=re.escape(eb[3]))
                    if re.search(pat1, sentence):
                        matched = True
                        break
                    pat2 = tmpl.format(A=re.escape(ea[2]), B=re.escape(eb[2]))
                    if re.search(pat2, sentence):
                        matched = True
                        break
                
                if matched:
                    key = (ea[3], eb[3])
                    matched_pairs.add(key)
                    triples.append({
                        'relation': rel_name,
                        'head': ea[3], 'head_type': type_a,
                        'tail': eb[3], 'tail_type': type_b,
                        'head_raw': ea[2], 'tail_raw': eb[2],
                        'sentence': sentence, 'doc_id': doc_id,
                        'match_type': 'explicit',
                    })
    
    # Step 2: 兜底共现关系(改进2: 同一句话中不同类型实体建立"相关"关系)
    if not explicit_only:
        for type_a, type_b in COOCCUR_ALLOWED_PAIRS:
            list_a = by_type.get(type_a, [])
            list_b = by_type.get(type_b, [])
            if not list_a or not list_b:
                continue
            
            for ea in list_a:
                for eb in list_b:
                    if ea[3] == eb[3]:
                        continue
                    key = (ea[3], eb[3])
                    if key in matched_pairs:
                        continue  # 已有明确关系,不再兜底
                    
                    dist = min(abs(ea[1]-eb[0]), abs(eb[1]-ea[0]))
                    if dist > 120:
                        continue
                    
                    # 建立兜底关系
                    triples.append({
                        'relation': '相关',
                        'head': ea[3], 'head_type': type_a,
                        'tail': eb[3], 'tail_type': type_b,
                        'head_raw': ea[2], 'tail_raw': eb[2],
                        'sentence': sentence, 'doc_id': doc_id,
                        'match_type': 'cooccur',
                    })
                    matched_pairs.add(key)
    
    return triples


# ==================== 主流程 ====================
def main():
    print("=" * 60)
    print("COPD关系抽取系统 v4 — 最大覆盖版")
    print("=" * 60)
    
    print("\n[Step 1] 加载种子词典...")
    seed_dict = SeedDictionary(SEED_DICT_PATH)
    
    print("[Step 2] 扫描并筛选文献...")
    all_txt_files = sorted([f for f in os.listdir(TEXT_DIR) if f.endswith('.txt')])
    
    txt_files = []
    filtered_out = []
    for f in all_txt_files:
        is_core, reason = is_copd_core_document(f)
        if is_core:
            txt_files.append(f)
        else:
            filtered_out.append((f, reason))
    
    print(f"  总文献: {len(all_txt_files)} 篇")
    print(f"  保留: {len(txt_files)} 篇")
    print(f"  过滤: {len(filtered_out)} 篇")
    if filtered_out:
        print("  被过滤:")
        for fname, reason in filtered_out[:10]:
            print(f"    - {fname[:45]}... ({reason})")
        if len(filtered_out) > 10:
            print(f"    ... 等{len(filtered_out)}篇")
    
    all_triples = []
    total_sents = 0
    
    for idx, txt_name in enumerate(txt_files, 1):
        txt_path = os.path.join(TEXT_DIR, txt_name)
        print(f"  [{idx}/{len(txt_files)}] {txt_name[:40]}...", end=' ')
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        sentences = split_sentences(text)
        doc_triples = 0
        
        for sent in sentences:
            entities = seed_dict.match(sent)
            if len(entities) < 2:
                continue
            triples = extract_from_sentence(sent, entities, txt_name, explicit_only=False)
            all_triples.extend(triples)
            doc_triples += len(triples)
        
        total_sents += len(sentences)
        print(f"句子{len(sentences)} 三元组{doc_triples}")
    
    print(f"\n[完成] 原始三元组: {len(all_triples)}")
    
    # 去重
    print("[Step 3] 去重...")
    seen = {}
    for t in all_triples:
        key = (t['relation'], t['head'], t['tail'])
        if key not in seen or len(t['sentence']) > len(seen[key]['sentence']):
            seen[key] = t
    all_triples = list(seen.values())
    print(f"  去重后: {len(all_triples)}")
    
    # 统计明确 vs 兜底
    explicit_cnt = sum(1 for t in all_triples if t['match_type'] == 'explicit')
    cooccur_cnt = sum(1 for t in all_triples if t['match_type'] == 'cooccur')
    print(f"  其中明确关系: {explicit_cnt} | 兜底共现关系: {cooccur_cnt}")
    
    # 保存
    print("[Step 4] 保存...")
    suffix = "v4_最大覆盖版"
    
    csv_path = os.path.join(OUTPUT_DIR, f'{suffix}_原始三元组_带溯源.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['关系类型','头实体','头类型','尾实体','尾类型',
                         '头原文','尾原文','原始句子','文献编号','匹配类型'])
        for t in all_triples:
            writer.writerow([t['relation'],t['head'],t['head_type'],
                            t['tail'],t['tail_type'],t['head_raw'],
                            t['tail_raw'],t['sentence'],t['doc_id'],t.get('match_type','')])
    
    json_path = os.path.join(OUTPUT_DIR, f'{suffix}_原始三元组_带溯源.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_triples, f, ensure_ascii=False, indent=2)
    
    report_path = os.path.join(OUTPUT_DIR, f'{suffix}_关系抽取统计报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:

        f.write(f"COPD关系抽取统计报告 ({suffix})\n" + "="*50 + "\n\n")
        f.write(f"处理文献: {len(txt_files)} 篇\n")
        f.write(f"处理句子: {total_sents} 句\n")
        f.write(f"去重三元组: {len(all_triples)} 条\n")
        f.write(f"  - 明确模板匹配: {explicit_cnt} 条\n")
        f.write(f"  - 兜底共现匹配: {cooccur_cnt} 条\n\n")
        
        rel_cnt = defaultdict(int)
        for t in all_triples:
            rel_cnt[t['relation']] += 1
        f.write("【关系分布】\n")
        for rel, cnt in sorted(rel_cnt.items(), key=lambda x: -x[1]):
            f.write(f"  {rel}: {cnt}\n")
        
        f.write("\n【Top 50 三元组】\n")
        for i, t in enumerate(all_triples[:50], 1):
            f.write(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']} ({t.get('match_type','')})\n")
            f.write(f"   句: {t['sentence'][:70]}...\n")
            f.write(f"   源: {t['doc_id'][:40]}\n\n")
    
    print(f"\n[已保存]\n  CSV: {csv_path}\n  JSON: {json_path}\n  报告: {report_path}")
    
    # 实体覆盖度分析
    print("\n" + "="*60)
    print("实体覆盖度分析")
    print("="*60)
    entity_in_triples = set()
    for t in all_triples:
        entity_in_triples.add(t['head'])
        entity_in_triples.add(t['tail'])
    
    participated = len(entity_in_triples)
    isolated = len(seed_dict.term2type) - participated
    print(f"种子词典实体: {len(seed_dict.term2type)}")
    print(f"参与三元组: {participated} ({participated/len(seed_dict.term2type)*100:.1f}%)")
    print(f"孤立实体: {isolated} ({isolated/len(seed_dict.term2type)*100:.1f}%)")
    
    TYPE_LABELS = {'Disease':'疾病','Symptom':'症状','Examination':'检查','Medication':'药物','Treatment':'治疗','Pathology':'病理','Complication':'并发症','RiskFactor':'危险因素','Guideline':'指南','Organization':'机构','TCM_Syndrome':'中医证候','Concept':'概念','Anatomical':'解剖'}
    print(f"\n{'类型':<12} {'总数':>4} {'参与':>4} {'孤立':>4} {'参与率':>6}")
    print('-' * 40)
    for typ in ['Disease','Symptom','Examination','Medication','Treatment','Pathology','Complication','RiskFactor','Guideline','Organization','TCM_Syndrome','Concept','Anatomical']:
        total = sum(1 for e,t in seed_dict.term2type.items() if t == typ)
        if total == 0: continue
        in_t = sum(1 for e,t in seed_dict.term2type.items() if t == typ and e in entity_in_triples)
        iso = total - in_t
        print(f"{TYPE_LABELS.get(typ,typ):<10} {total:>4} {in_t:>4} {iso:>4} {in_t/total*100:>5.1f}%")
    
    # 列出剩余孤立实体
    print("\n=== 剩余孤立实体 ===")
    for typ in ['Disease','Symptom','Examination','Medication','Treatment','Pathology','Complication','RiskFactor','Guideline','Organization','TCM_Syndrome','Concept','Anatomical']:
        isolated_list = [e for e,t in seed_dict.term2type.items() if t == typ and e not in entity_in_triples]
        if isolated_list:
            print(f"\n[{TYPE_LABELS.get(typ,typ)}] 孤立 {len(isolated_list)} 个:")
            for e in isolated_list:
                print(f"  - {e}")

if __name__ == '__main__':
    main()
