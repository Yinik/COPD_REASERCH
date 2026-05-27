#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COPD知识图谱核心功能单元测试
覆盖：实体识别、关系抽取、BERT验证、Neo4j连接、端到端流水线
运行方式：python run_tests.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import socket

# 禁用BERT避免加载模型（测试中只验证接口）
import COPD图谱端到端抽取系统_v2 as _pipe_mod
_pipe_mod.USE_BERT = False

from COPD图谱端到端抽取系统_v2 import (
    KnowledgeBase, EntityRecognizer, RelationExtractor,
    BERTVerifier, COPDKGPipeline, Neo4jUpdater
)


class TestEntityRecognizer(unittest.TestCase):
    """实体识别器单元测试"""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()
        cls.recognizer = EntityRecognizer(cls.kb)

    def test_recognize_basic(self):
        """基本实体识别：应识别疾病和症状"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难和慢性咳嗽"
        entities = self.recognizer.recognize(text)
        names = [e[2] for e in entities]
        self.assertIn("慢性阻塞性肺疾病", names)
        self.assertIn("呼吸困难", names)
        self.assertIn("慢性咳嗽", names)

    def test_greedy_longest_matching(self):
        """贪婪最长匹配：应完整匹配8字实体而非截断"""
        text = "慢性阻塞性肺疾病"
        entities = self.recognizer.recognize(text)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0][2], "慢性阻塞性肺疾病")
        self.assertEqual(entities[0][3], "Disease")

    def test_entity_types(self):
        """实体类型标注正确性"""
        text = "糖皮质激素和支气管舒张剂可治疗慢性阻塞性肺疾病"
        entities = self.recognizer.recognize(text)
        types = {e[2]: e[3] for e in entities}
        self.assertEqual(types.get("慢性阻塞性肺疾病"), "Disease")
        self.assertEqual(types.get("糖皮质激素"), "Medication")
        self.assertEqual(types.get("支气管舒张剂"), "Medication")

    def test_no_entities(self):
        """无实体文本应返回空列表"""
        text = "今天天气很好，我们去公园散步"
        entities = self.recognizer.recognize(text)
        self.assertEqual(len(entities), 0)

    def test_partial_match_boundary(self):
        """边界测试：部分匹配不应识别"""
        text = "慢性（不是完整疾病名）"
        entities = self.recognizer.recognize(text)
        names = [e[2] for e in entities]
        self.assertNotIn("慢性", names)  # 不应单独匹配"慢性"


class TestRelationExtractor(unittest.TestCase):
    """关系抽取器单元测试"""

    @classmethod
    def setUpClass(cls):
        cls.kb = KnowledgeBase()
        cls.extractor = RelationExtractor(cls.kb)
        cls.recognizer = EntityRecognizer(cls.kb)

    def test_cooccurrence_disease_symptom(self):
        """共现匹配：疾病-症状关系"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难和慢性咳嗽"
        entities = self.recognizer.recognize(text)
        triples = self.extractor.extract(text, entities)
        rels = [(t['head'], t['relation'], t['tail']) for t in triples]
        self.assertIn(("慢性阻塞性肺疾病", "疾病-症状", "呼吸困难"), rels)
        self.assertIn(("慢性阻塞性肺疾病", "疾病-症状", "慢性咳嗽"), rels)

    def test_cooccurrence_medication_disease(self):
        """共现匹配：药物-治疗-疾病关系"""
        text = "糖皮质激素和支气管舒张剂可治疗慢性阻塞性肺疾病"
        entities = self.recognizer.recognize(text)
        triples = self.extractor.extract(text, entities)
        rels = [(t['head'], t['relation'], t['tail']) for t in triples]
        self.assertIn(("糖皮质激素", "药物-治疗-疾病", "慢性阻塞性肺疾病"), rels)
        self.assertIn(("支气管舒张剂", "药物-治疗-疾病", "慢性阻塞性肺疾病"), rels)

    def test_template_match(self):
        """模板/共现匹配：疾病-并发症关系"""
        text = "慢性阻塞性肺疾病患者可并发肺动脉高压"
        entities = self.recognizer.recognize(text)
        triples = self.extractor.extract(text, entities)
        rels = [(t['head'], t['relation'], t['tail'], t.get('source')) for t in triples]
        # 检查是否涉及慢性阻塞性肺疾病和肺动脉高压的关系
        has_rel = any(
            (t[0] == "慢性阻塞性肺疾病" and t[2] == "肺动脉高压") or
            (t[0] == "肺动脉高压" and t[2] == "慢性阻塞性肺疾病")
            for t in rels
        )
        self.assertTrue(
            has_rel,
            f"未找到预期关系，实际关系: {rels}"
        )

    def test_source_field(self):
        """三元组应包含来源标注（cooccurrence或template）"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难"
        entities = self.recognizer.recognize(text)
        triples = self.extractor.extract(text, entities)
        self.assertTrue(len(triples) > 0)
        for t in triples:
            self.assertIn(t.get('source'), ['cooccurrence', 'template'])

    def test_entity_type_consistency(self):
        """三元组中头尾实体类型应与关系类型匹配"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难和慢性咳嗽"
        entities = self.recognizer.recognize(text)
        triples = self.extractor.extract(text, entities)
        for t in triples:
            if t['relation'] == '疾病-症状':
                self.assertEqual(t['head_type'], 'Disease')
                self.assertEqual(t['tail_type'], 'Symptom')


class TestBERTVerifier(unittest.TestCase):
    """BERT验证器单元测试（模型加载已禁用）"""

    def test_model_availability(self):
        """无模型时应标记为不可用，不抛出异常"""
        verifier = BERTVerifier()
        # 可用性取决于模型文件是否存在，测试不应依赖文件状态
        self.assertIsInstance(verifier.available, bool)

    def test_label_map_loaded(self):
        """标签映射应正确加载"""
        verifier = BERTVerifier()
        if verifier.available:
            self.assertIsNotNone(verifier.label_map)
            self.assertIsNotNone(verifier.id2label)
            self.assertGreater(len(verifier.label_map), 0)


class TestNeo4jConnection(unittest.TestCase):
    """Neo4j连接单元测试"""

    def _is_neo4j_running(self):
        """检查Neo4j是否运行"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(('localhost', 7687))
            s.close()
            return True
        except:
            return False

    @unittest.skipUnless(
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('localhost', 7687)) == 0,
        "Neo4j未运行，跳过连接测试"
    )
    def test_connection(self):
        """Neo4j连接成功"""
        updater = Neo4jUpdater()
        self.assertTrue(updater.connected)

    @unittest.skipUnless(
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('localhost', 7687)) == 0,
        "Neo4j未运行，跳过统计测试"
    )
    def test_stats(self):
        """统计查询返回正确格式"""
        updater = Neo4jUpdater()
        stats = updater.get_stats()
        self.assertIsNotNone(stats)
        self.assertIn('nodes', stats)
        self.assertIn('relations', stats)
        self.assertIsInstance(stats['nodes'], int)
        self.assertIsInstance(stats['relations'], int)


class TestPipeline(unittest.TestCase):
    """端到端流水线单元测试"""

    @classmethod
    def setUpClass(cls):
        cls.pipeline = COPDKGPipeline()

    def test_process_format(self):
        """返回结果应包含必需字段"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难和慢性咳嗽"
        result = self.pipeline.process(text, update_neo4j=False)
        self.assertIn('entities', result)
        self.assertIn('triples', result)
        self.assertIn('verified_triples', result)
        self.assertIn('new_triples', result)
        self.assertIn('is_new', result)

    def test_process_entities(self):
        """应识别到至少2个实体"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难和慢性咳嗽"
        result = self.pipeline.process(text, update_neo4j=False)
        self.assertGreaterEqual(len(result['entities']), 2)

    def test_process_triples(self):
        """应抽取到至少1个关系三元组"""
        text = "慢性阻塞性肺疾病患者出现呼吸困难和慢性咳嗽"
        result = self.pipeline.process(text, update_neo4j=False)
        total = len(result.get('triples', []))
        self.assertGreaterEqual(total, 1)

    def test_process_no_entities(self):
        """无实体文本应返回空结果"""
        text = "今天天气很好"
        result = self.pipeline.process(text, update_neo4j=False)
        self.assertEqual(len(result['entities']), 0)
        self.assertEqual(len(result['triples']), 0)

    def test_process_medication_disease(self):
        """药物-疾病关系抽取"""
        text = "糖皮质激素可治疗慢性阻塞性肺疾病"
        result = self.pipeline.process(text, update_neo4j=False)
        triples = result.get('triples', [])
        rels = [(t['head'], t['relation'], t['tail']) for t in triples]
        self.assertTrue(
            any(t[0] == "糖皮质激素" and "药物" in t[1] and t[2] == "慢性阻塞性肺疾病" for t in rels)
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
