# -*- coding: utf-8 -*-
"""
COPD医学文本关系抽取系统 v2（高效版）
优化: Trie树实体识别 + 提前过滤 + 批量处理
"""
import config  # 统一路径配置


import os
import re
import csv
import json
import pdfplumber
from collections import defaultdict

# ==================== 配置 ====================
SEED_DICT_PATH = str(config.BASE_DIR / r"种子词典构建结果\29_全部中文文献_最终种子词典_严格清理1.tsv")
PDF_DIR = str(config.BASE_DIR / r"原始文献数据")
OUTPUT_DIR = str(config.BASE_DIR / r"关系抽取结果")
os.makedirs(OUTPUT_DIR, exist_ok=True)
MAX_PDFS = 30  # 测试时限制数量，None表示全部

# ==================== 模块1: 高效种子词典 ====================

class SeedDictionary:
    def __init__(self, tsv_path):
        self.term2type = {}
        self.term2standard = {}
        self.type2terms = defaultdict(set)
        self._load(tsv_path)
        # 构建用于快速查找的term集合
        self.all_term_set = set(self.term2type.keys()) | set(self.term2standard.keys())
        # 按长度降序
        self.all_terms = sorted(self.all_term_set, key=len, reverse=True)
        # 构建类型过滤集合
        self.type_terms = {}
        for typ in ['Disease', 'Symptom', 'Examination', 'Medication', 
                    'Treatment', 'Pathology', 'Complication', 'RiskFactor',
                    'Guideline', 'Organization', 'TCM_Syndrome', 'Concept', 'Anatomical']:
            self.type_terms[typ] = set()
        for term, typ in self.term2type.items():
            self.type_terms[typ].add(term)
            # 同义词也加入
            for alias, std in self.term2standard.items():
                if std == term:
                    self.type_terms[typ].add(alias)
        print(f"[词典加载] 标准术语:{len(self.term2type)} 同义词:{len(self.term2standard)}")
    
    def _load(self, path):
        with open(path, 'rb') as f:
            raw = f.read()
        if raw.startswith(b'\xff\xfe'):
            text = raw.decode('utf-16-le')
        elif raw.startswith(b'\xfe\xff'):
            text = raw.decode('utf-16-be')
        else:
            text = raw.decode('utf-8-sig')
        
        from io import StringIO
        reader = csv.DictReader(StringIO(text), delimiter='\t')
        for row in reader:
            std = row['标准术语'].strip()
            typ = row['类型'].strip()
            alias_str = row['同义词'].strip()
            self.term2type[std] = typ
            if alias_str and alias_str != '-':
                for alias in alias_str.split('、'):
                    alias = alias.strip()
                    if alias:
                        self.term2standard[alias] = std
    
    def get_standard(self, word):
        return self.term2standard.get(word, word)
    
    def get_type(self, word):
        return self.term2type.get(self.get_standard(word), 'Unknown')
    
    def match_entities(self, text):
        """贪心最长匹配，返回[(start, end, raw, standard, type), ...]"""
        entities = []
        i = 0
        n = len(text)
        while i < n:
            matched = False
            for term in self.all_terms:
                if text.startswith(term, i):
                    std = self.get_standard(term)
                    typ = self.get_type(term)
                    entities.append((i, i + len(term), term, std, typ))
                    i += len(term)
                    matched = True
                    break
            if not matched:
                i += 1
        # 去重重叠
        if not entities:
            return []
        entities.sort(key=lambda x: (x[0], -(x[1]-x[0])))
        result = [entities[0]]
        for e in entities[1:]:
            if e[0] >= result[-1][1]:
                result.append(e)
        return result


# ==================== 模块2: 关系模板库 ====================

RELATION_RULES = [
    # (关系名, 头实体类型, 尾实体类型, 模板列表)
    ('疾病-症状', 'Disease', 'Symptom', [
        r'{A}.*?(主要症状|可出现|常伴有|表现为|常见症状|主要表现|临床症状).*?{B}',
        r'{B}.*?(是|为|提示|见于|考虑).*?{A}',
        r'患有.*?{A}.*?出现.*?{B}',
        r'{A}.*?患者.*?{B}',
    ]),
    ('药物-治疗-疾病', 'Medication', 'Disease', [
        r'{A}.*?(用于|治疗|改善|控制|缓解).*?{B}',
        r'治疗.*?{B}.*?(给予|使用|推荐|选择|应用).*?{A}',
        r'{B}.*?患者.*?(使用|给予|应用).*?{A}',
        r'{A}.*?(是|为).*?{B}.*?(一线|首选|标准)',
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
]

# 预编译所有模板
COMPILED_RULES = []
for rel_name, type_a, type_b, templates in RELATION_RULES:
    compiled = []
    for tmpl in templates:
        compiled.append(tmpl)
    COMPILED_RULES.append((rel_name, type_a, type_b, compiled))


# ==================== 模块3: 工具函数 ====================

def extract_pdf_text(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            parts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            return '\n'.join(parts)
    except Exception as e:
        return ""

def clean_text(text):
    text = re.sub(r'DOI[：:]\s*10\.\S+', '', text, flags=re.I)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    return text

def split_sentences(text):
    parts = re.split(r'([。！？；])', text)
    sentences = []
    cur = ""
    for p in parts:
        cur += p
        if p in '。！？；':
            s = cur.strip()
            if len(s) > 12:
                sentences.append(s)
            cur = ""
    if cur.strip() and len(cur.strip()) > 12:
        sentences.append(cur.strip())
    return sentences

def extract_relations(sentence, entities, doc_id):
    triples = []
    # 按类型分组
    by_type = defaultdict(list)
    for e in entities:
        by_type[e[4]].append(e)
    
    for rel_name, type_a, type_b, templates in COMPILED_RULES:
        list_a = by_type.get(type_a, [])
        list_b = by_type.get(type_b, [])
        if not list_a or not list_b:
            continue
        
        for ea in list_a:
            for eb in list_b:
                if ea[3] == eb[3]:
                    continue
                # 距离过滤：实体间隔太远则跳过
                if abs(ea[0] - eb[1]) > 80 and abs(eb[0] - ea[1]) > 80:
                    continue
                
                std_a, std_b = re.escape(ea[3]), re.escape(eb[3])
                raw_a, raw_b = re.escape(ea[2]), re.escape(eb[2])
                
                for tmpl in templates:
                    pat = tmpl.format(A=std_a, B=std_b)
                    if re.search(pat, sentence):
                        triples.append({
                            'relation': rel_name,
                            'head': ea[3], 'head_type': type_a,
                            'tail': eb[3], 'tail_type': type_b,
                            'head_raw': ea[2], 'tail_raw': eb[2],
                            'sentence': sentence, 'doc_id': doc_id,
                            'pattern': pat,
                        })
                        break
                    pat_raw = tmpl.format(A=raw_a, B=raw_b)
                    if re.search(pat_raw, sentence):
                        triples.append({
                            'relation': rel_name,
                            'head': ea[3], 'head_type': type_a,
                            'tail': eb[3], 'tail_type': type_b,
                            'head_raw': ea[2], 'tail_raw': eb[2],
                            'sentence': sentence, 'doc_id': doc_id,
                            'pattern': pat_raw,
                        })
                        break
    return triples


# ==================== 主流程 ====================

def main():
    print("=" * 60)
    print("COPD关系抽取系统 v2")
    print("=" * 60)
    
    print("\n[Step 1] 加载种子词典...")
    seed_dict = SeedDictionary(SEED_DICT_PATH)
    
    print("[Step 2] 扫描PDF文献...")
    pdf_files = sorted([f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')])
    if MAX_PDFS:
        pdf_files = pdf_files[:MAX_PDFS]
    print(f"  待处理: {len(pdf_files)} 篇")
    
    all_triples = []
    stats = defaultdict(int)
    
    for idx, pdf_name in enumerate(pdf_files, 1):
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        print(f"  [{idx}/{len(pdf_files)}] {pdf_name[:40]}...", end=' ')
        
        text = extract_pdf_text(pdf_path)
        if not text:
            print("[读取失败]")
            continue
        
        cleaned = clean_text(text)
        sentences = split_sentences(cleaned)
        
        doc_triples = 0
        for sent in sentences:
            entities = seed_dict.match_entities(sent)
            if len(entities) < 2:
                continue
            triples = extract_relations(sent, entities, pdf_name)
            all_triples.extend(triples)
            doc_triples += len(triples)
        
        print(f"句子{len(sentences)} 三元组{doc_triples}")
        stats['total_sentences'] += len(sentences)
    
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
    
    # 保存
    print("[Step 4] 保存结果...")
    csv_path = os.path.join(OUTPUT_DIR, '原始三元组_带溯源.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['关系类型','头实体','头类型','尾实体','尾类型',
                         '头原文','尾原文','原始句子','文献编号'])
        for t in all_triples:
            writer.writerow([t['relation'],t['head'],t['head_type'],
                            t['tail'],t['tail_type'],t['head_raw'],
                            t['tail_raw'],t['sentence'],t['doc_id']])
    
    json_path = os.path.join(OUTPUT_DIR, '原始三元组_带溯源.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_triples, f, ensure_ascii=False, indent=2)
    
    report_path = os.path.join(OUTPUT_DIR, '关系抽取统计报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:

        f.write("COPD关系抽取统计报告\n" + "="*50 + "\n\n")
        f.write(f"处理文献: {len(pdf_files)} 篇\n")
        f.write(f"处理句子: {stats['total_sentences']} 句\n")
        f.write(f"去重三元组: {len(all_triples)} 条\n\n")
        
        rel_cnt = defaultdict(int)
        for t in all_triples:
            rel_cnt[t['relation']] += 1
        f.write("【关系分布】\n")
        for rel, cnt in sorted(rel_cnt.items(), key=lambda x: -x[1]):
            f.write(f"  {rel}: {cnt}\n")
        
        f.write("\n【Top 30 三元组】\n")
        for i, t in enumerate(all_triples[:30], 1):
            f.write(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']}\n")
            f.write(f"   {t['sentence'][:70]}...\n")
            f.write(f"   [{t['doc_id'][:30]}...]\n\n")
    
    print(f"\n[已保存]\n  CSV: {csv_path}\n  JSON: {json_path}\n  报告: {report_path}")
    
    print("\n" + "="*60)
    print("Top 20 预览")
    print("="*60)
    for i, t in enumerate(all_triples[:20], 1):
        print(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']}")
        print(f"   {t['sentence'][:55]}...")

if __name__ == '__main__':
    main()
