#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COPD医学知识图谱 - 端到端抽取演示系统

功能：输入一段COPD临床文本 -> 自动识别实体 -> 抽取关系 -> 增量更新Neo4j图谱

使用方式：
    1. 确保Neo4j数据库已启动且已有基础图谱数据
    2. 运行脚本，按提示输入COPD相关文本
    3. 脚本自动完成实体识别、关系抽取、图谱更新
    4. 打开Neo4j Browser查看新增节点和关系

依赖：
    pip install py2neo

作者：COPD知识图谱小组
"""

import csv
import re
import os
from collections import defaultdict

# ==================== 配置区域 ====================

# Neo4j连接配置（根据你的实际设置修改）
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "19950824"  # Neo4j数据库密码

# 资源文件路径
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
NODES_CSV = os.path.join(PROJECT_DIR, '关系抽取结果', 'import', 'nodes.csv')
TRIPLES_TSV = os.path.join(PROJECT_DIR, '关系抽取结果', '方向规范化_疾病统一在头.tsv')

# ==================== 全局知识库 ====================

class KnowledgeBase:
    """COPD医学知识库：包含实体词典、关系模板、已有三元组"""
    
    def __init__(self):
        self.entities = {}  # name -> type
        self.entity_by_type = defaultdict(list)  # type -> [name, ...]
        self.existing_triples = set()  # (head, relation, tail)
        self.relation_templates = []
        self._load_entities()
        self._load_existing_triples()
        self._build_templates()
    
    def _load_entities(self):
        """从nodes.csv加载126个实体"""
        if not os.path.exists(NODES_CSV):
            print(f"[警告] 未找到实体文件: {NODES_CSV}")
            print(f"[提示] 请先运行 '生成Neo4j导入.py' 生成资源文件")
            return
        
        with open(NODES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['name']
                etype = row['type']
                self.entities[name] = etype
                self.entity_by_type[etype].append(name)
        
        print(f"[知识库] 已加载 {len(self.entities)} 个实体")
        for etype, names in sorted(self.entity_by_type.items()):
            print(f"  - {etype}: {len(names)} 个")
    
    def _load_existing_triples(self):
        """从TSV加载已有的675条三元组，避免重复"""
        if not os.path.exists(TRIPLES_TSV):
            print(f"[警告] 未找到三元组文件: {TRIPLES_TSV}")
            return
        
        with open(TRIPLES_TSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                triple = (row['头实体'], row['关系类型'], row['尾实体'])
                self.existing_triples.add(triple)
        
        print(f"[知识库] 已加载 {len(self.existing_triples)} 条已有三元组")
    
    def _build_templates(self):
        """构建13种关系类型的规则模板"""
        
        # 定义核心动词和句式模式
        # 格式: (关系类型, 头实体类型, 尾实体类型, 正向正则, 反向正则(可选))
        template_defs = [
            # 1. 药物-治疗-疾病
            {
                'rel_type': '药物-治疗-疾病',
                'head_type': 'Medication',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:用于|可以|可|能)(?:治疗|控制|改善|缓解|管理)(?:.+?)(.+?)(?:的|患者|病人)?',
                    r'(.+?)(?:是|为)(?:治疗|控制)(?:.+?)(.+?)(?:的|一线|首选|常用)?(?:药物|用药|疗法)',
                    r'(?:治疗|控制)(?:.+?)(.+?)(?:可|可以|可用)(?:使用|用|给予|应用)(.+?)(?:治疗|控制)?',
                ],
                'reverse': True  # 需要方向判断
            },
            
            # 2. 疾病-症状
            {
                'rel_type': '疾病-症状',
                'head_type': 'Disease',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:患者|病人)?(?:出现|伴有|表现为|主要表现|常见症状|引起|导致|产生)(?:.+?)(.+?)(?:等症状)?',
                    r'(.+?)(?:的)?(?:主要|常见|典型|临床)(?:症状|表现)(?:为|是|包括)(?:.+?)(.+?)(?:等)?',
                    r'(.+?)(?:可|可能|常)?(?:引起|导致|产生|造成)(?:.+?)(.+?)(?:等症状)?',
                ],
                'reverse': False
            },
            
            # 3. 诱发-急性加重
            {
                'rel_type': '诱发-急性加重',
                'head_type': 'Disease',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:可|可能|常)?(?:诱发|引起|导致|触发|加重|使)(?:.+?)(?:急性加重|AECOPD|加重期)(?:.+?)(.+?)?',
                    r'(.+?)(?:是|为)(.+?)(?:急性加重|AECOPD|加重期)?(?:的)?(?:主要|常见|重要)?(?:诱因|原因|危险因素)',
                ],
                'reverse': False
            },
            
            # 4. 药物-缓解-症状
            {
                'rel_type': '药物-缓解-症状',
                'head_type': 'Medication',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:可|可以|能|能够)(?:缓解|减轻|改善|控制|减轻|止咳|平喘)(?:.+?)(.+?)(?:等症状)?',
                    r'(.+?)(?:用于|适用于)(?:缓解|减轻|改善)(?:.+?)(.+?)(?:等症状)?',
                ],
                'reverse': True
            },
            
            # 5. 检查-辅助诊断-疾病
            {
                'rel_type': '检查-辅助诊断-疾病',
                'head_type': 'Examination',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:是|为|用于|可用于|对)(?:.+?)(?:诊断|确诊|辅助诊断|评估|筛查)(?:.+?)(.+?)(?:有)?(?:重要|关键|辅助)?(?:价值|意义|作用)?',
                    r'(.+?)(?:可|可以|能)(?:诊断|确诊|辅助诊断|评估|判断)(?:.+?)(.+?)(?:的|患者)?',
                ],
                'reverse': True
            },
            
            # 6. 治疗-改善-症状
            {
                'rel_type': '治疗-改善-症状',
                'head_type': 'Treatment',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:可|可以|能|能够)(?:改善|缓解|减轻|控制|减轻)(?:.+?)(.+?)(?:等症状)?',
                    r'(.+?)(?:用于|适用于)(?:改善|缓解|减轻)(?:.+?)(.+?)(?:等症状)?',
                ],
                'reverse': True
            },
            
            # 7. 疾病-并发症
            {
                'rel_type': '疾病-并发症',
                'head_type': 'Disease',
                'tail_type': 'Complication',
                'patterns': [
                    r'(.+?)(?:可|可能|常)?(?:并发|合并|继发|引起|导致|产生)(?:.+?)(.+?)(?:等)?(?:并发症)?',
                    r'(.+?)(?:的)?(?:常见|主要|可能)?(?:并发症|合并症)(?:为|是|包括)(?:.+?)(.+?)(?:等)?',
                ],
                'reverse': False
            },
            
            # 8. 疾病-治疗
            {
                'rel_type': '疾病-治疗',
                'head_type': 'Disease',
                'tail_type': 'Treatment',
                'patterns': [
                    r'(.+?)(?:的)?(?:治疗|治疗方案|治疗原则|管理)(?:包括|有|为|采用|推荐)(?:.+?)(.+?)(?:等)?',
                    r'(.+?)(?:患者|病人)?(?:需要|应|应该|推荐|建议|可|可以)(?:进行|接受|采用|使用)(?:.+?)(.+?)(?:治疗)?',
                ],
                'reverse': False
            },
            
            # 9. 危险因素-疾病
            {
                'rel_type': '危险因素-疾病',
                'head_type': 'RiskFactor',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:是|为)(.+?)(?:的)?(?:主要|重要|常见|已知)?(?:危险因素|风险因素|病因|诱因)',
                    r'(.+?)(?:可|可能|会|增加)?(?:引起|导致|诱发|增加)(?:.+?)(.+?)(?:的)?(?:风险|发病率|患病率|发生)?',
                ],
                'reverse': False
            },
            
            # 10. 检查-评估-疾病
            {
                'rel_type': '检查-评估-疾病',
                'head_type': 'Examination',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:用于|可用于|对)(?:.+?)(?:评估|评价|判断|监测|随访)(?:.+?)(.+?)(?:的)?(?:严重|严重程|严重度|程度|进展|预后)?',
                ],
                'reverse': True
            },
            
            # 11. 检查-评估-症状
            {
                'rel_type': '检查-评估-症状',
                'head_type': 'Examination',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:用于|可用于)(?:.+?)(?:评估|评价|量化|测量|记录)(?:.+?)(.+?)(?:的)?(?:严重|严重程|程度)?',
                ],
                'reverse': True
            },
            
            # 12. 药物-导致-并发症
            {
                'rel_type': '药物-导致-并发症',
                'head_type': 'Medication',
                'tail_type': 'Complication',
                'patterns': [
                    r'(.+?)(?:可|可能|会)?(?:引起|导致|产生|诱发|造成|增加)(?:.+?)(.+?)(?:等)?(?:并发症|不良|副作用|风险)?',
                ],
                'reverse': False
            },
            
            # 13. 检查-筛查-疾病
            {
                'rel_type': '检查-筛查-疾病',
                'head_type': 'Examination',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:用于|可用于|对)(?:.+?)(?:筛查|早期发现|诊断|检测)(?:.+?)(.+?)(?:患者)?',
                ],
                'reverse': True
            },
        ]
        
        for td in template_defs:
            for pat in td['patterns']:
                self.relation_templates.append({
                    'rel_type': td['rel_type'],
                    'head_type': td['head_type'],
                    'tail_type': td['tail_type'],
                    'pattern': re.compile(pat),
                    'reverse': td.get('reverse', False)
                })
        
        print(f"[知识库] 已加载 {len(self.relation_templates)} 条关系模板")


# ==================== 核心算法模块 ====================

class EntityRecognizer:
    """基于种子词典的贪心最长匹配实体识别器"""
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        # 按长度降序排列实体，确保贪心最长匹配
        self.sorted_entities = sorted(
            kb.entities.keys(), 
            key=len, 
            reverse=True
        )
    
    def recognize(self, text: str):
        """
        贪心最长匹配实体识别
        
        返回: [(start_pos, end_pos, entity_name, entity_type), ...]
        """
        entities = []
        i = 0
        n = len(text)
        matched_positions = set()
        
        while i < n:
            matched = False
            for ent_name in self.sorted_entities:
                if text.startswith(ent_name, i):
                    # 检查是否已被更长的匹配覆盖
                    if i not in matched_positions:
                        ent_type = self.kb.entities[ent_name]
                        entities.append((i, i + len(ent_name), ent_name, ent_type))
                        # 标记已匹配位置
                        for p in range(i, i + len(ent_name)):
                            matched_positions.add(p)
                        i += len(ent_name)
                        matched = True
                        break
            if not matched:
                i += 1
        
        # 按位置排序
        entities.sort(key=lambda x: x[0])
        return entities


class RelationExtractor:
    """基于规则模板的关系抽取器"""
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
    
    def extract(self, text: str, entities: list):
        """
        基于规则模板的关系抽取
        
        参数:
            text: 原始文本
            entities: 实体识别结果 [(start, end, name, type), ...]
        
        返回: [dict, ...] 每个dict包含 head, head_type, tail, tail_type, relation, context
        """
        triples = []
        
        for template in self.kb.relation_templates:
            matches = template['pattern'].findall(text)
            
            for match in matches:
                if isinstance(match, str):
                    match = (match, '')
                
                group1 = match[0] if len(match) > 0 else ''
                group2 = match[1] if len(match) > 1 else ''
                
                # 在匹配组中查找符合类型的实体
                head_candidates = self._find_entities_in_text(
                    group1, entities, template['head_type']
                ) + self._find_entities_in_text(
                    group2, entities, template['head_type']
                )
                
                tail_candidates = self._find_entities_in_text(
                    group1, entities, template['tail_type']
                ) + self._find_entities_in_text(
                    group2, entities, template['tail_type']
                )
                
                # 处理方向：如果模板是反向的（如"检查-辅助诊断-疾病"），
                # 检查可能在group2，疾病在group1
                if template['reverse']:
                    # 尝试另一种组合：检查group2中的head_type和group1中的tail_type
                    h_from_g2 = self._find_entities_in_text(group2, entities, template['head_type'])
                    t_from_g1 = self._find_entities_in_text(group1, entities, template['tail_type'])
                    
                    for h in h_from_g2:
                        for t in t_from_g1:
                            triples.append({
                                'head': h,
                                'head_type': template['head_type'],
                                'tail': t,
                                'tail_type': template['tail_type'],
                                'relation': template['rel_type'],
                                'context': text
                            })
                
                # 正向组合
                for h in head_candidates:
                    for t in tail_candidates:
                        if h != t:  # 避免自环
                            triples.append({
                                'head': h,
                                'head_type': template['head_type'],
                                'tail': t,
                                'tail_type': template['tail_type'],
                                'relation': template['rel_type'],
                                'context': text
                            })
        
        # 去重
        seen = set()
        unique_triples = []
        for t in triples:
            key = (t['head'], t['relation'], t['tail'])
            if key not in seen and key not in self.kb.existing_triples:
                seen.add(key)
                unique_triples.append(t)
        
        return unique_triples
    
    def _find_entities_in_text(self, segment: str, entities: list, target_type: str):
        """在指定文本段中查找指定类型的实体"""
        result = []
        for ent in entities:
            name, etype = ent[2], ent[3]
            if etype == target_type and name in segment:
                result.append(name)
        return list(set(result))


class Neo4jUpdater:
    """Neo4j图谱增量更新器"""
    
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.uri = uri
        self.user = user
        self.password = password
        self.graph = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """连接Neo4j数据库"""
        try:
            from py2neo import Graph
            self.graph = Graph(self.uri, auth=(self.user, self.password))
            # 测试连接
            result = self.graph.run("RETURN 1 as test").data()
            self.connected = True
            print(f"[Neo4j] 连接成功: {self.uri}")
        except ImportError:
            print("[提示] 未安装py2neo，请运行: pip install py2neo")
        except Exception as e:
            print(f"[提示] 未检测到Neo4j: {e}")
            print("[提示] 无Neo4j也能运行实体识别和关系抽取，仅跳过图谱可视化")
            print("[提示] 如需图谱展示，请启动Neo4j并修改密码配置")

    def update(self, triples: list):
        """增量更新三元组到Neo4j"""
        if not self.connected or not self.graph:
            print("[错误] Neo4j未连接，跳过图谱更新")
            return 0
        
        count = 0
        for t in triples:
            try:
                # 使用Cypher MERGE避免重复
                self.graph.run("""
                    MERGE (a:Entity {name: $head})
                    SET a.type = $head_type
                    MERGE (b:Entity {name: $tail})
                    SET b.type = $tail_type
                    MERGE (a)-[r:RELATION {type: $relation}]->(b)
                    SET r.context = $context
                """, parameters={
                    'head': t['head'],
                    'head_type': t['head_type'],
                    'tail': t['tail'],
                    'tail_type': t['tail_type'],
                    'relation': t['relation'],
                    'context': t['context']
                })
                count += 1
            except Exception as e:
                print(f"[警告] 插入失败 ({t['head']} -> {t['tail']}): {e}")
        
        return count
    
    def get_stats(self):
        """获取当前图谱统计"""
        if not self.connected:
            return None
        
        node_count = self.graph.run("MATCH (n) RETURN count(n) as c").data()[0]['c']
        rel_count = self.graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]['c']
        return {'nodes': node_count, 'relations': rel_count}


# ==================== 端到端流水线 ====================

class COPDKGPipeline:
    """COPD知识图谱端到端抽取流水线"""
    
    def __init__(self):
        print("=" * 60)
        print("COPD医学知识图谱 - 端到端抽取系统")
        print("=" * 60)
        print()
        
        # 初始化知识库
        self.kb = KnowledgeBase()
        
        # 初始化各模块
        self.recognizer = EntityRecognizer(self.kb)
        self.extractor = RelationExtractor(self.kb)
        self.updater = Neo4jUpdater()
        
        print()
    
    def process(self, text: str, update_neo4j: bool = True):
        """
        处理单段文本的完整流程
        
        参数:
            text: COPD临床文本
            update_neo4j: 是否更新到Neo4j（False则只输出结果不更新）
        
        返回:
            dict: 包含 entities, triples, is_new 的处理结果
        """
        print("-" * 60)
        print("【输入文本】")
        print(text[:200] + ("..." if len(text) > 200 else ""))
        print("-" * 60)
        
        # Step 1: 实体识别
        print("\n[Step 1] 实体识别（贪心最长匹配）...")
        entities = self.recognizer.recognize(text)
        
        if not entities:
            print("  [WARN] 未识别到任何已知实体")
            return {'entities': [], 'triples': [], 'is_new': False}
        
        print(f"  [OK] 识别到 {len(entities)} 个实体:")
        for ent in entities:
            print(f"    - {ent[2]} ({ent[3]})")
        
        # Step 2: 关系抽取
        print("\n[Step 2] 关系抽取（规则模板匹配）...")
        triples = self.extractor.extract(text, entities)
        
        if not triples:
            print("  [WARN] 未抽取到任何关系")
            return {'entities': entities, 'triples': [], 'is_new': False}
        
        # 区分已有三元组和新三元组
        new_triples = []
        existing_triples = []
        for t in triples:
            key = (t['head'], t['relation'], t['tail'])
            if key in self.kb.existing_triples:
                existing_triples.append(t)
            else:
                new_triples.append(t)
        
        print(f"  [OK] 共抽取 {len(triples)} 个关系:")
        if existing_triples:
            print(f"    - {len(existing_triples)} 个已存在于知识库（灰色）")
        if new_triples:
            print(f"    - {len(new_triples)} 个新关系（绿色，将入库）:")
            for t in new_triples[:5]:  # 只显示前5个
                print(f"      -> {t['head']} --[{t['relation']}]--> {t['tail']}")
            if len(new_triples) > 5:
                print(f"      ... 还有 {len(new_triples) - 5} 个")
        
        # Step 3: Neo4j更新
        if update_neo4j and new_triples and self.updater.connected:
            print("\n[Step 3] 增量更新到Neo4j...")
            inserted = self.updater.update(new_triples)
            print(f"  [OK] 成功插入 {inserted} 条新关系到Neo4j")
            
            # 显示更新后统计
            stats = self.updater.get_stats()
            if stats:
                print(f"  📊 当前图谱: {stats['nodes']} 节点, {stats['relations']} 关系")
        elif not self.updater.connected:
            print("\n[Step 3] Neo4j未连接，跳过更新")
            print("  生成Cypher语句供手动执行:")
            for t in new_triples[:3]:
                print(f"    MERGE (a:Entity {{name: '{t['head']}'}})")
                print(f"    MERGE (b:Entity {{name: '{t['tail']}'}})")
                print(f"    MERGE (a)-[r:RELATION {{type: '{t['relation']}'}}]->(b);")
        
        return {
            'entities': entities,
            'triples': triples,
            'new_triples': new_triples,
            'is_new': len(new_triples) > 0
        }
    
    def interactive(self):
        """交互式运行模式"""
        print()
        print("=" * 60)
        print("进入交互模式，请输入COPD相关临床文本")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'stats' 查看当前图谱统计")
        print("=" * 60)
        print()
        
        # 预设示例文本
        examples = [
            "慢性阻塞性肺疾病患者出现呼吸困难和咳嗽，可使用沙丁胺醇缓解症状。",
            "肺功能检查用于诊断慢性阻塞性肺疾病，FEV1/FVC比值是关键指标。",
            "吸烟是慢性阻塞性肺疾病的主要危险因素，长期吸烟可导致急性加重。",
            "慢性阻塞性肺疾病患者可并发肺心病和呼吸衰竭，需要氧疗治疗。",
        ]
        
        print("【示例文本】输入数字1-4快速体验，或直接粘贴文本:")
        for i, ex in enumerate(examples, 1):
            print(f"  {i}. {ex}")
        print()
        
        while True:
            try:
                user_input = input(">>> ").strip()
            except KeyboardInterrupt:
                print("\n再见!")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("再见!")
                break
            
            if user_input.lower() == 'stats':
                stats = self.updater.get_stats()
                if stats:
                    print(f"当前图谱: {stats['nodes']} 节点, {stats['relations']} 关系")
                else:
                    print("Neo4j未连接")
                continue
            
            # 检查是否是示例编号
            if user_input in ('1', '2', '3', '4'):
                user_input = examples[int(user_input) - 1]
                print(f"使用示例: {user_input}")
            
            # 处理文本
            self.process(user_input)
            print()


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    pipeline = COPDKGPipeline()
    pipeline.interactive()
