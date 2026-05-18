# -*- coding: utf-8 -*-
"""
COPD医学文本关系抽取系统 v3
基于已有清洗文本，避免重复PDF解析
"""

import os
import re
import csv
import json
from collections import defaultdict

# ==================== 配置 ====================
SEED_DICT_PATH = r"I:\101实验专题\种子词典构建结果\29_全部中文文献_最终种子词典_严格清理1.tsv"
TEXT_DIR = r"I:\101实验专题\抽取结果\cleaned_texts"
OUTPUT_DIR = r"I:\101实验专题\关系抽取结果"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 改进B: COPD核心文献白名单（根据文件名自动筛选，或手动指定）
# 策略: 文件名中包含这些关键词的文献被认为是COPD核心文献
COPD_CORE_KEYWORDS_IN_FILENAME = [
    '慢阻肺', 'COPD', '慢性阻塞性肺疾病', '慢性阻塞性肺病',
    '慢性阻塞性肺',
]

# 明确非COPD文献黑名单（慢性咳嗽、GERD、COVID-19、囊性纤维化等）
NON_COPD_BLACKLIST_IN_FILENAME = [
    '咳嗽', 'GERD', '胃食管反流', 'COVID', '新冠', 
    '囊性纤维化', 'cystic-fibrosis', '胸外科', 'thoracic',
    'Miller', '肺血栓', '支气管扩张症临床疗效',  # 非COPD核心
]

def is_copd_core_document(filename):
    """判断文献是否为COPD核心文献"""
    # 如果在黑名单中，直接排除
    for kw in NON_COPD_BLACKLIST_IN_FILENAME:
        if kw.lower() in filename.lower():
            return False, f'非COPD文献:{kw}'
    # 如果在白名单关键词中，保留
    for kw in COPD_CORE_KEYWORDS_IN_FILENAME:
        if kw in filename:
            return True, f'COPD核心:{kw}'
    # 其他文献：如果是中文文献且未匹配黑名单，可以保留（可能是COPD相关）
    # 但如果是纯英文文献（无中文关键词），可能不是核心
    if re.search(r'[\u4e00-\u9fff]', filename):
        return True, '中文文献(未匹配黑名单)'
    return False, '英文/非核心文献'

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
        """贪心最长匹配"""
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
        # 去重重叠
        entities.sort(key=lambda x: (x[0], -(x[1]-x[0])))
        result = [entities[0]]
        for e in entities[1:]:
            if e[0] >= result[-1][1]:
                result.append(e)
        return result


# ==================== 模块2: 关系规则 ====================

RULES = [
    # 原有4类关系
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
    # 新增: 疾病-治疗 (覆盖Treatment类型实体)
    ('疾病-治疗', 'Disease', 'Treatment', [
        r'{A}.*?(患者|应|可|需|建议|推荐|给予|使用|采用|进行|接受|联合).*?{B}',
        r'{B}.*?(用于|治疗|改善|控制|缓解|是).*?{A}',
        r'对.*?{A}.*?{B}',
        r'{A}.*?合并.*?{B}',
        r'{B}.*?(可|能).*?减轻.*?{A}',
        r'{B}.*?(可|能).*?改善.*?{A}',
        r'{A}.*?(戒烟|氧疗|康复|通气|手术|训练|营养).*?{B}',  # 反向匹配
    ]),
    # 新增: 危险因素-疾病 (覆盖RiskFactor类型实体)
    ('危险因素-疾病', 'RiskFactor', 'Disease', [
        r'{A}.*?(增加|导致|引起|诱发|是|为).*?{B}.*?(危险|风险|病因|原因)',
        r'{B}.*?(与|和).*?{A}.*?(相关|有关|密切|明确)',
        r'{A}.*?(是|为).*?{B}.*?(重要|主要|常见).*?(因素|原因)',
        r'{B}.*?(危险|风险|高危).*?{A}',
        r'暴露于.*?{A}.*?{B}',
        r'{A}.*?(与|和).*?{B}.*?(发生|发展|进展)',
        r'{B}.*?(患者|人群).*?{A}',
    ]),
]


# ==================== 模块3: 工具函数 ====================

# 噪声句子的关键词
NOISE_KEYWORDS = [
    '[PAGE__NO_TEXT]', '内容目录', '目录', '免责声明', '基金项目',
    '通讯作者', '参考文献', '版权声明', '版权所有', '页码',
    'Table of Contents', 'CONTENTS', 'Figure', 'Table',
    '收稿日期', '修回日期', 'DOI:', 'doi:', 'http',
]

def is_noise_sentence(sentence):
    """判断句子是否为噪声"""
    # 过滤含有噪声关键词的句子
    for kw in NOISE_KEYWORDS:
        if kw in sentence:
            return True, f'噪声关键词:{kw}'
    # 过滤过长句子（可能是表格、目录）
    if len(sentence) > 300:
        return True, '过长句子(>300字)'
    # 过滤过短句子
    if len(sentence) < 15:
        return True, '过短句子(<15字)'
    # 过滤纯数字/英文比例过高的句子（可能是参考文献/DOI/页码）
    if sentence.isdigit():
        return True, '纯数字'
    # 如果句子中超过50%是英文字母+数字+标点，可能是英文段落或参考文献
    en_num_punct = sum(1 for c in sentence if c.isascii())
    if len(sentence) > 20 and en_num_punct / len(sentence) > 0.6:
        return True, '高ASCII比例(疑似英文/参考文献)'
    return False, None

def split_sentences(text):
    parts = re.split(r'([。！？；])', text)
    sentences = []
    cur = ""
    for p in parts:
        cur += p
        if p in '。！？；':
            s = cur.strip()
            if len(s) > 12:
                is_noise, reason = is_noise_sentence(s)
                if not is_noise:
                    sentences.append(s)
            cur = ""
    if cur.strip() and len(cur.strip()) > 12:
        is_noise, reason = is_noise_sentence(cur.strip())
        if not is_noise:
            sentences.append(cur.strip())
    return sentences


def extract_from_sentence(sentence, entities, doc_id):
    triples = []
    by_type = defaultdict(list)
    for e in entities:
        by_type[e[4]].append(e)
    
    for rel_name, type_a, type_b, templates in RULES:
        list_a = by_type.get(type_a, [])
        list_b = by_type.get(type_b, [])
        if not list_a or not list_b:
            continue
        
        for ea in list_a:
            for eb in list_b:
                if ea[3] == eb[3]:
                    continue
                # 距离过滤：超过60字符跳过
                dist = min(abs(ea[1]-eb[0]), abs(eb[1]-ea[0]))
                if dist > 60:
                    continue
                
                for tmpl in templates:
                    pat1 = tmpl.format(A=re.escape(ea[3]), B=re.escape(eb[3]))
                    if re.search(pat1, sentence):
                        triples.append({
                            'relation': rel_name,
                            'head': ea[3], 'head_type': type_a,
                            'tail': eb[3], 'tail_type': type_b,
                            'head_raw': ea[2], 'tail_raw': eb[2],
                            'sentence': sentence, 'doc_id': doc_id,
                        })
                        break
                    pat2 = tmpl.format(A=re.escape(ea[2]), B=re.escape(eb[2]))
                    if re.search(pat2, sentence):
                        triples.append({
                            'relation': rel_name,
                            'head': ea[3], 'head_type': type_a,
                            'tail': eb[3], 'tail_type': type_b,
                            'head_raw': ea[2], 'tail_raw': eb[2],
                            'sentence': sentence, 'doc_id': doc_id,
                        })
                        break
    return triples


# ==================== 主流程 ====================

def main():
    print("=" * 60)
    print("COPD关系抽取系统 v3")
    print("=" * 60)
    
    print("\n[Step 1] 加载种子词典...")
    seed_dict = SeedDictionary(SEED_DICT_PATH)
    
    print("[Step 2] 扫描并筛选COPD核心文献...")
    all_txt_files = sorted([f for f in os.listdir(TEXT_DIR) if f.endswith('.txt')])
    
    # 应用改进B: 文献筛选 (开关: True=启用筛选, False=全部保留)
    ENABLE_DOC_FILTER = True  # 当前模式: 改进A+B(句子清洗+文献筛选)
    
    if ENABLE_DOC_FILTER:
        txt_files = []
        filtered_out = []
        for f in all_txt_files:
            is_core, reason = is_copd_core_document(f)
            if is_core:
                txt_files.append(f)
            else:
                filtered_out.append((f, reason))
        print(f"  总文献: {len(all_txt_files)} 篇")
        print(f"  保留(COPD核心): {len(txt_files)} 篇")
        print(f"  过滤(非COPD): {len(filtered_out)} 篇")
        if filtered_out:
            print("  被过滤的文献:")
            for fname, reason in filtered_out:
                print(f"    - {fname[:50]}... ({reason})")
    else:
        txt_files = all_txt_files
        print(f"  模式: 改进A(句子清洗) — 处理全部 {len(txt_files)} 篇文献")
    
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
            triples = extract_from_sentence(sent, entities, txt_name)
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
    
    # 保存 (根据模式自动命名)
    print("[Step 4] 保存...")
    if ENABLE_DOC_FILTER:
        suffix = "A+B_句子清洗+文献筛选"
    else:
        suffix = "改进A_仅句子清洗"
    
    csv_path = os.path.join(OUTPUT_DIR, f'{suffix}_原始三元组_带溯源.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['关系类型','头实体','头类型','尾实体','尾类型',
                         '头原文','尾原文','原始句子','文献编号'])
        for t in all_triples:
            writer.writerow([t['relation'],t['head'],t['head_type'],
                            t['tail'],t['tail_type'],t['head_raw'],
                            t['tail_raw'],t['sentence'],t['doc_id']])
    
    json_path = os.path.join(OUTPUT_DIR, f'{suffix}_原始三元组_带溯源.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_triples, f, ensure_ascii=False, indent=2)
    
    report_path = os.path.join(OUTPUT_DIR, f'{suffix}_关系抽取统计报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"COPD关系抽取统计报告 ({suffix})\n" + "="*50 + "\n\n")
        f.write(f"处理文献: {len(txt_files)} 篇\n")
        f.write(f"处理句子: {total_sents} 句\n")
        f.write(f"去重三元组: {len(all_triples)} 条\n\n")
        
        rel_cnt = defaultdict(int)
        for t in all_triples:
            rel_cnt[t['relation']] += 1
        f.write("【关系分布】\n")
        for rel, cnt in sorted(rel_cnt.items(), key=lambda x: -x[1]):
            f.write(f"  {rel}: {cnt}\n")
        
        f.write("\n【Top 50 三元组】\n")
        for i, t in enumerate(all_triples[:50], 1):
            f.write(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']}\n")
            f.write(f"   句: {t['sentence'][:70]}...\n")
            f.write(f"   源: {t['doc_id'][:40]}\n\n")
    
    print(f"\n[已保存]\n  CSV: {csv_path}\n  JSON: {json_path}\n  报告: {report_path}")
    
    print("\n" + "="*60)
    print("Top 20 预览")
    print("="*60)
    for i, t in enumerate(all_triples[:20], 1):
        print(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']}")
        print(f"   {t['sentence'][:55]}...")

if __name__ == '__main__':
    main()
