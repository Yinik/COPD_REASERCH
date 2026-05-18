# -*- coding: utf-8 -*-
"""
COPD医学文本关系抽取系统（规则模板版）
输入: 种子词典 + 原始PDF文献
输出: 带原文溯源的三元组CSV
"""

import os
import re
import csv
import json
import pdfplumber
from collections import defaultdict

# ==================== 配置 ====================
SEED_DICT_PATH = r"I:\101实验专题\种子词典构建结果\29_全部中文文献_最终种子词典_严格清理1.tsv"
PDF_DIR = r"I:\101实验专题\原始文献数据"
OUTPUT_DIR = r"I:\101实验专题\关系抽取结果"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 只处理这些中文PDF（排除英文和明显非COPD的文献，可选）
# 如选择方案A全量，保留所有；如聚焦COPD，可在此筛选
TARGET_PDFS = None  # None表示处理全部PDF
MAX_PDFS = 20  # 先测试前20篇，避免超时

# ==================== 模块1: 种子词典加载 ====================

class SeedDictionary:
    """种子词典管理器: 支持标准术语+同义词的贪心最长匹配"""
    
    def __init__(self, tsv_path):
        self.term2type = {}      # 标准术语 -> 类型
        self.term2standard = {}  # 同义词 -> 标准术语
        self.type2terms = defaultdict(set)  # 类型 -> 术语集合
        self._load(tsv_path)
    
    def _load(self, path):
        # 自动检测编码: 先尝试utf-8, 失败则试utf-16-le
        import codecs
        with open(path, 'rb') as f:
            raw = f.read()
        # 检测BOM
        if raw.startswith(b'\xff\xfe'):
            text = raw.decode('utf-16-le')
        elif raw.startswith(b'\xfe\xff'):
            text = raw.decode('utf-16-be')
        elif raw.startswith(b'\xef\xbb\xbf'):
            text = raw.decode('utf-8-sig')
        else:
            text = raw.decode('utf-8')
        
        from io import StringIO
        f = StringIO(text)
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
                std = row['标准术语'].strip()
                typ = row['类型'].strip()
                alias_str = row['同义词'].strip()
                
                self.term2type[std] = typ
                self.type2terms[typ].add(std)
                
                # 同义词映射到标准术语
                if alias_str and alias_str != '-':
                    for alias in alias_str.split('、'):
                        alias = alias.strip()
                        if alias:
                            self.term2standard[alias] = std
                            self.type2terms[typ].add(alias)
        
        # 按长度降序排序，保证贪心最长匹配
        self.all_terms = sorted(
            set(self.term2type.keys()) | set(self.term2standard.keys()),
            key=len, reverse=True
        )
        print(f"[词典加载] 标准术语:{len(self.term2type)} 同义词:{len(self.term2standard)} 总匹配项:{len(self.all_terms)}")
    
    def get_standard(self, word):
        """获取标准术语"""
        return self.term2standard.get(word, word)
    
    def get_type(self, word):
        """获取术语类型（基于标准术语）"""
        std = self.get_standard(word)
        return self.term2type.get(std, 'Unknown')
    
    def match_entities(self, text):
        """
        贪心最长匹配识别文本中的实体
        返回: [(start, end, raw_term, standard_term, entity_type), ...]
        """
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
        # 去重重叠（保留最长）
        entities = self._remove_overlap(entities)
        return entities
    
    def _remove_overlap(self, entities):
        """去除重叠实体，优先保留最长的"""
        if not entities:
            return []
        # 按起始位置排序，相同起始位置保留最长的
        entities.sort(key=lambda x: (x[0], -(x[1]-x[0])))
        result = [entities[0]]
        for e in entities[1:]:
            last = result[-1]
            if e[0] >= last[1]:  # 无重叠
                result.append(e)
            # 有重叠则跳过（因为已按长度降序，前面的更长）
        return result


# ==================== 模块2: PDF文本预处理 ====================

def extract_text_from_pdf(pdf_path):
    """提取PDF全文文本"""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        print(f"  [警告] 无法读取PDF: {os.path.basename(pdf_path)} - {e}")
        return ""
    return "\n".join(text_parts)


def clean_text(text):
    """清洗医学文本: 去除页眉页脚/DOI/参考文献等噪声"""
    # 去除DOI
    text = re.sub(r'DOI[：:]\s*10\.\S+', '', text, flags=re.IGNORECASE)
    # 去除网址
    text = re.sub(r'https?://\S+', '', text)
    # 去除英文email
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    # 去除数字编号行（如 [1], [2], 1., 2.）在参考文献区域
    # 这里简化处理，主要依靠后续分句过滤短句
    return text


def split_sentences(text):
    """将文本分句，保留句子结束符"""
    # 中文分句: 。！？；为分隔符，但保留在句尾
    sentences = re.split(r'([。！？；])', text)
    result = []
    current = ""
    for s in sentences:
        current += s
        if s in '。！？；':
            stripped = current.strip()
            if len(stripped) > 10:  # 过滤过短的句子（可能是标题/噪声）
                result.append(stripped)
            current = ""
    if current.strip() and len(current.strip()) > 10:
        result.append(current.strip())
    return result


# ==================== 模块3: 关系规则模板库 ====================

class RelationExtractor:
    """基于规则模板的关系抽取引擎"""
    
    # 四类核心关系定义
    RELATIONS = {
        '疾病-症状': {
            'types': ('Disease', 'Symptom'),
            'templates': [
                r'{A}.*?主要症状.*?{B}',
                r'{A}.*?可出现.*?{B}',
                r'{A}.*?常伴有.*?{B}',
                r'{A}.*?表现为.*?{B}',
                r'{A}.*?常见症状.*?{B}',
                r'{B}.*?是.*?{A}.*?典型表现',
                r'{B}.*?是.*?{A}.*?常见症状',
                r'{B}.*?提示.*?{A}',
                r'{B}.*?见于.*?{A}',
                r'患有.*?{A}.*?出现.*?{B}',
            ],
            'direction': 'A→B',  # Disease → Symptom
        },
        '药物-治疗-疾病': {
            'types': ('Medication', 'Disease'),
            'templates': [
                r'{A}.*?用于.*?治疗.*?{B}',
                r'{A}.*?治疗.*?{B}',
                r'{A}.*?可改善.*?{B}',
                r'{A}.*?控制.*?{B}',
                r'治疗.*?{B}.*?给予.*?{A}',
                r'治疗.*?{B}.*?使用.*?{A}',
                r'治疗.*?{B}.*?推荐.*?{A}',
                r'{B}.*?患者.*?使用.*?{A}',
                r'{B}.*?患者.*?给予.*?{A}',
                r'{A}.*?是.*?{B}.*?一线',
            ],
            'direction': 'A→B',  # Medication → Disease
        },
        '检查-辅助诊断-疾病': {
            'types': ('Examination', 'Disease'),
            'templates': [
                r'{A}.*?诊断.*?{B}',
                r'{A}.*?评估.*?{B}',
                r'{A}.*?检查.*?{B}',
                r'诊断.*?{B}.*?{A}',
                r'诊断.*?{B}.*?依据.*?{A}',
                r'{B}.*?需.*?{A}',
                r'{B}.*?进行.*?{A}',
                r'{B}.*?通过.*?{A}',
                r'{A}.*?有助于.*?{B}',
                r'{A}.*?可.*?鉴别.*?{B}',
            ],
            'direction': 'A→B',  # Examination → Disease
        },
        '疾病-并发症': {
            'types': ('Disease', 'Complication'),
            'templates': [
                r'{A}.*?合并.*?{B}',
                r'{A}.*?并发.*?{B}',
                r'{A}.*?导致.*?{B}',
                r'{A}.*?引起.*?{B}',
                r'{B}.*?是.*?{A}.*?并发症',
                r'{B}.*?是.*?{A}.*?合并症',
                r'{A}.*?患者.*?发生.*?{B}',
                r'{A}.*?易发生.*?{B}',
                r'{A}.*?与.*?{B}.*?相关',
            ],
            'direction': 'A→B',  # Disease → Complication
        },
    }
    
    def __init__(self, seed_dict):
        self.seed_dict = seed_dict
        self._compile_patterns()
    
    def _compile_patterns(self):
        """预编译正则模板（将{A}{B}替换为实际实体词）"""
        self.compiled = {}
        for rel_name, config in self.RELATIONS.items():
            self.compiled[rel_name] = {
                'types': config['types'],
                'direction': config['direction'],
                'patterns': config['templates'],
            }
    
    def extract_relations(self, sentence, entities, doc_id):
        """
        从句子中抽取关系
        entities: [(start, end, raw, standard, type), ...]
        返回: [(relation_type, entity1, entity2, evidence), ...]
        """
        triples = []
        
        # 按类型分组实体
        type_entities = defaultdict(list)
        for e in entities:
            type_entities[e[4]].append(e)
        
        # 对每种关系类型，尝试匹配
        for rel_name, config in self.compiled.items():
            type_a, type_b = config['types']
            
            # 获取该关系需要的实体对
            entities_a = type_entities.get(type_a, [])
            entities_b = type_entities.get(type_b, [])
            
            if not entities_a or not entities_b:
                continue
            
            # 枚举所有实体对
            for ea in entities_a:
                for eb in entities_b:
                    # 避免同一实体自环
                    if ea[3] == eb[3]:
                        continue
                    
                    # 构建带占位符的句子用于匹配
                    match_result = self._match_pair(sentence, ea, eb, config['patterns'])
                    if match_result:
                        triples.append({
                            'relation': rel_name,
                            'head': ea[3],      # 标准术语
                            'head_type': type_a,
                            'tail': eb[3],      # 标准术语
                            'tail_type': type_b,
                            'head_raw': ea[2],  # 原文中的形式
                            'tail_raw': eb[2],
                            'sentence': sentence,
                            'doc_id': doc_id,
                            'match_pattern': match_result,
                        })
        
        return triples
    
    def _match_pair(self, sentence, entity_a, entity_b, patterns):
        """判断两个实体在句子中是否满足任一模板"""
        std_a = re.escape(entity_a[3])
        std_b = re.escape(entity_b[3])
        raw_a = re.escape(entity_a[2])
        raw_b = re.escape(entity_b[2])
        
        for tmpl in patterns:
            # 尝试用标准术语匹配
            pat = tmpl.format(A=std_a, B=std_b)
            if re.search(pat, sentence):
                return pat
            # 尝试用原文形式匹配
            pat_raw = tmpl.format(A=raw_a, B=raw_b)
            if re.search(pat_raw, sentence):
                return pat_raw
        return None


# ==================== 模块4: 主流程 ====================

def main():
    print("=" * 60)
    print("COPD医学文本关系抽取系统")
    print("=" * 60)
    
    # Step 1: 加载种子词典
    print("\n[Step 1] 加载种子词典...")
    seed_dict = SeedDictionary(SEED_DICT_PATH)
    
    # Step 2: 初始化关系抽取引擎
    print("[Step 2] 初始化关系抽取引擎...")
    extractor = RelationExtractor(seed_dict)
    
    # Step 3: 遍历PDF文献
    print("\n[Step 3] 处理PDF文献...")
    all_triples = []
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith('.pdf')]
    
    if TARGET_PDFS:
        pdf_files = [f for f in pdf_files if f in TARGET_PDFS]
    
    print(f"  待处理PDF: {len(pdf_files)} 篇")
    
    pdf_files = pdf_files[:MAX_PDFS] if MAX_PDFS else pdf_files
    for idx, pdf_name in enumerate(pdf_files, 1):
        pdf_path = os.path.join(PDF_DIR, pdf_name)
        print(f"  [{idx}/{len(pdf_files)}] {pdf_name}")
        
        # 提取文本
        raw_text = extract_text_from_pdf(pdf_path)
        if not raw_text:
            continue
        
        # 清洗
        cleaned = clean_text(raw_text)
        
        # 分句
        sentences = split_sentences(cleaned)
        print(f"    提取到 {len(sentences)} 个句子")
        
        # 逐句处理
        doc_triples = 0
        for sent in sentences:
            # 实体识别
            entities = seed_dict.match_entities(sent)
            if len(entities) < 2:
                continue
            
            # 关系抽取
            triples = extractor.extract_relations(sent, entities, pdf_name)
            all_triples.extend(triples)
            doc_triples += len(triples)
        
        print(f"    抽取到 {doc_triples} 个三元组")
    
    print(f"\n[完成] 总计抽取 {len(all_triples)} 个原始三元组")
    
    # Step 4: 去重（相同head/relation/tail只保留一条，保留最长证据句）
    print("[Step 4] 去重与整理...")
    unique = {}
    for t in all_triples:
        key = (t['relation'], t['head'], t['tail'])
        if key not in unique or len(t['sentence']) > len(unique[key]['sentence']):
            unique[key] = t
    all_triples = list(unique.values())
    print(f"  去重后: {len(all_triples)} 个三元组")
    
    # Step 5: 保存结果
    print("[Step 5] 保存结果...")
    
    # CSV格式
    csv_path = os.path.join(OUTPUT_DIR, '原始三元组_带溯源.csv')
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['关系类型', '头实体', '头实体类型', '尾实体', '尾实体类型', 
                         '头实体原文', '尾实体原文', '原始句子', '文献编号'])
        for t in all_triples:
            writer.writerow([
                t['relation'], t['head'], t['head_type'], 
                t['tail'], t['tail_type'],
                t['head_raw'], t['tail_raw'],
                t['sentence'], t['doc_id']
            ])
    
    # JSON格式
    json_path = os.path.join(OUTPUT_DIR, '原始三元组_带溯源.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_triples, f, ensure_ascii=False, indent=2)
    
    # 统计报告
    report_path = os.path.join(OUTPUT_DIR, '关系抽取统计报告.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("COPD关系抽取统计报告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"处理文献数: {len(pdf_files)}\n")
        f.write(f"原始三元组数: {len(all_triples)}\n\n")
        
        f.write("【关系类型分布】\n")
        rel_counts = defaultdict(int)
        for t in all_triples:
            rel_counts[t['relation']] += 1
        for rel, cnt in sorted(rel_counts.items(), key=lambda x: -x[1]):
            f.write(f"  {rel}: {cnt} 条\n")
        
        f.write("\n【实体对示例（前30条）】\n")
        for i, t in enumerate(all_triples[:30], 1):
            f.write(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']}\n")
            f.write(f"   证据: {t['sentence'][:80]}...\n")
            f.write(f"   来源: {t['doc_id']}\n\n")
    
    print(f"\n[已保存]")
    print(f"  CSV: {csv_path}")
    print(f"  JSON: {json_path}")
    print(f"  报告: {report_path}")
    
    # 预览
    print("\n" + "=" * 60)
    print("Top 20 抽取结果预览")
    print("=" * 60)
    for i, t in enumerate(all_triples[:20], 1):
        print(f"{i}. [{t['relation']}] {t['head']} -> {t['tail']}")
        print(f"   句: {t['sentence'][:60]}...")


if __name__ == '__main__':
    main()
