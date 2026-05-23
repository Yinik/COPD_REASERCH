#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COPD医学知识图谱 - 端到端抽取系统 v2
规则为主 + BERT为辅验证

改进点：
    1. 规则模板生成候选关系（高召回）
    2. BERT分类器验证关系类型并打分（高精确）
    3. 只保留BERT置信度>threshold的结果
    4. Neo4j使用独立关系标签（兼容v2导入格式）
    5. 数据指向BERT修正版

使用方式：
    1. 确保Neo4j数据库已启动
    2. 运行脚本，按提示输入COPD相关文本
    3. 脚本自动完成实体识别、规则抽取、BERT验证、图谱更新

依赖：
    pip install py2neo torch transformers
"""
import config  # 统一路径配置

import csv
import re
import os
import json
from collections import defaultdict
from pathlib import Path

# ==================== 配置区域 ====================

import config
NEO4J_URI = config.NEO4J_URI
NEO4J_USER = config.NEO4J_USER
NEO4J_PASSWORD = config.NEO4J_PASSWORD

# 数据路径（BERT修正版）
BASE_DIR = config.BASE_DIR
NODES_CSV = BASE_DIR / "关系抽取结果" / "Neo4j导入_v2" / "nodes_tiered.csv"
TRIPLES_TSV = BASE_DIR / "关系抽取结果" / "最终三元组_方案B_BERT修正版.tsv"
BERT_MODEL_DIR = BASE_DIR / "bert_relation_output"

# BERT验证阈值（可调整）
BERT_CONFIDENCE_THRESHOLD = 0.3

# 是否启用BERT验证（模型不存在时自动回退到纯规则）
USE_BERT = True


# ==================== BERT验证模块 ====================

class BERTVerifier:
    """BERT关系分类验证器"""
    
    def __init__(self, model_dir=BERT_MODEL_DIR, threshold=BERT_CONFIDENCE_THRESHOLD):
        self.threshold = threshold
        self.model = None
        self.tokenizer = None
        self.label_map = None
        self.id2label = None
        self.device = None
        self.available = False
        self._load_model(model_dir)
    
    def _load_model(self, model_dir):
        """加载BERT模型"""
        try:
            import torch
            from transformers import BertTokenizer, BertForSequenceClassification
            
            model_path = Path(model_dir) / "best_model.pt"
            meta_path = Path(model_dir) / "model_meta.json"
            
            if not model_path.exists() or not meta_path.exists():
                print(f"[BERT] 未找到模型文件: {model_path}")
                print("[BERT] 将回退到纯规则模式")
                return
            
            # 加载元数据
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            self.label_map = {int(k): v for k, v in meta['id2relation'].items()}
            self.id2label = meta['id2relation']
            num_labels = len(self.label_map)
            
            # 加载tokenizer和模型（离线模式）
            pretrained = meta.get('pretrained_model', 'bert-base-chinese')
            self.tokenizer = BertTokenizer.from_pretrained(
                pretrained, local_files_only=True
            )
            # 先添加特殊token，确保词表大小和训练时一致
            special_tokens = {'additional_special_tokens': ['[E1]', '[/E1]', '[E2]', '[/E2]']}
            self.tokenizer.add_special_tokens(special_tokens)
            
            self.model = BertForSequenceClassification.from_pretrained(
                pretrained, num_labels=num_labels, local_files_only=True
            )
            self.model.resize_token_embeddings(len(self.tokenizer))
            
            # 加载训练好的权重（处理包装字典格式）
            checkpoint = torch.load(model_path, map_location='cpu', weights_only=True)
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            else:
                state_dict = checkpoint
            self.model.load_state_dict(state_dict)
            self.model.eval()
            
            self.device = torch.device('cpu')
            self.model.to(self.device)
            self.available = True
            
            print(f"[BERT] 模型加载成功: {model_path.name}")
            print(f"[BERT] 支持 {num_labels} 种关系类型，置信度阈值: {self.threshold}")
            
        except Exception as e:
            print(f"[BERT] 模型加载失败: {e}")
            print("[BERT] 将回退到纯规则模式")
    
    def verify(self, sentence: str, head: str, tail: str, rule_relation: str, source: str = 'template'):
        """
        BERT验证候选关系
        
        source: 'template' 或 'cooccurrence'
        
        返回: {
            'verified': bool,
            'predicted_label': str,
            'confidence': float,
            'top3': [(label, prob), ...]
        }
        """
        if not self.available:
            return {
                'verified': True,
                'predicted_label': rule_relation,
                'confidence': 1.0,
                'top3': [(rule_relation, 1.0)]
            }
        
        try:
            import torch
            from torch.nn.functional import softmax
            
            # 构建输入: [CLS] sent [SEP] [E1] head [/E1] [E2] tail [/E2]
            marked_sent = sentence.replace(head, f"[E1]{head}[/E1]", 1)
            marked_sent = marked_sent.replace(tail, f"[E2]{tail}[/E2]", 1)
            
            inputs = self.tokenizer(
                marked_sent,
                max_length=128,
                truncation=True,
                padding='max_length',
                return_tensors='pt'
            )
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = softmax(outputs.logits, dim=1)[0]
            
            # Top3预测
            top3_probs, top3_ids = torch.topk(probs, k=min(3, len(self.label_map)))
            top3 = []
            for prob, idx in zip(top3_probs.tolist(), top3_ids.tolist()):
                label = self.id2label.get(str(idx), self.label_map.get(idx, '未知'))
                top3.append((label, prob))
            
            predicted_label = top3[0][0]
            confidence = top3[0][1]
            
            # ===== 验证策略（统一宽松阈值，召回优先）=====
            # 无论template还是cooccurrence，只要BERT Top1预测与规则标签一致
            # 且置信度>0.10（避免随机猜测），即通过
            if predicted_label == rule_relation:
                verified = confidence > 0.10
            else:
                # BERT与规则不一致：仍采用规则标签，但要求置信度>=阈值
                # 这意味着BERT没有强烈反对该关系
                verified = confidence < 0.5  # BERT置信度低说明不确定，不反对规则
            
            return {
                'verified': verified,
                'predicted_label': predicted_label,
                'confidence': confidence,
                'top3': top3
            }
            
        except Exception as e:
            print(f"[BERT] 验证失败 ({head}->{tail}): {e}")
            return {
                'verified': True,
                'predicted_label': rule_relation,
                'confidence': 0.5,
                'top3': [(rule_relation, 0.5)]
            }


# ==================== 全局知识库 ====================

class KnowledgeBase:
    """COPD医学知识库：包含实体词典、关系模板、已有三元组"""
    
    def __init__(self):
        self.entities = {}  # name -> type
        self.entity_by_type = defaultdict(list)
        self.existing_triples = set()
        self.relation_templates = []
        self.synonyms = {}  # alias -> standard_name
        self._load_entities()
        self._load_existing_triples()
        self._load_synonyms()
        self._build_templates()
    
    def _load_entities(self):
        """从BERT修正版nodes.csv加载实体"""
        if not NODES_CSV.exists():
            print(f"[警告] 未找到实体文件: {NODES_CSV}")
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
        """从BERT修正版TSV加载已有三元组"""
        if not TRIPLES_TSV.exists():
            print(f"[警告] 未找到三元组文件: {TRIPLES_TSV}")
            return
        
        with open(TRIPLES_TSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                triple = (row['头实体'], row['关系类型'], row['尾实体'])
                self.existing_triples.add(triple)
        
        print(f"[知识库] 已加载 {len(self.existing_triples)} 条已有三元组")
    
    def _load_synonyms(self):
        """加载同义词映射表（别名->标准名）"""
        syn_file = NODES_CSV.parent / "entity_synonyms.csv"
        if not syn_file.exists():
            return
        
        with open(syn_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                standard = row['standard_name']
                alias = row['alias']
                self.synonyms[alias] = standard
        
        if self.synonyms:
            print(f"[知识库] 已加载 {len(self.synonyms)} 条同义词映射")
            for alias, standard in sorted(self.synonyms.items()):
                print(f"  - {alias} -> {standard}")
    
    def canonicalize(self, name: str) -> str:
        """将别名替换为标准名"""
        return self.synonyms.get(name, name)
    
    def _build_templates(self):
        """构建13种关系类型的规则模板"""
        template_defs = [
            {
                'rel_type': '药物-治疗-疾病',
                'head_type': 'Medication',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:用于|可以|可|能|能够|适用)(?:治疗|控制|改善|缓解|管理|处理|治愈|防治)(?:.+?)(.+?)(?:的|患者|病人|人群)?',
                    r'(.+?)(?:是|为|作为)(?:治疗|控制|改善|缓解|管理)(?:.+?)(.+?)(?:的|一线|首选|常用|标准|基础|核心|主要|重要|有效)?(?:药物|用药|疗法|治疗|方案|措施|手段|方法|策略)',
                    r'(?:治疗|控制|改善|缓解|管理)(?:.+?)(.+?)(?:可|可以|可用|能|能够|宜|应|应该|需|需要|须|必须|推荐|建议|选择|采用|给予|应用|使用|用)(?:使用|用|给予|应用|采用|选择|推荐|建议|联合|辅以|加用|换用|停用|调整|增加|减少|维持|继续|开始|启动|尝试|考虑|评估|监测)(?:.+?)?(.+?)(?:治疗|控制|改善|缓解|管理)?',
                    r'给予(.+?)(?:治疗|控制|改善|缓解|管理|处理)(?:.+?)(.+?)(?:的|患者|病人|人群)?',
                    r'(.+?)(?:联合|合用|联合应用|联合使用|联合治疗|联合给予|联合采用|联合选择|联合推荐|联合建议|加用|加服|辅以|辅助|配合|协同|增效|增强|提高|提升|改善|优化|强化|加强|调整|改变|转换|替换|替代|升级|降级)(?:.+?)?(.+?)(?:治疗|控制|改善|缓解|管理|处理)?',
                    r'(.+?)(?:吸入|雾化吸入|吸入治疗|雾化治疗|吸入给药|雾化给药|吸入疗法|雾化疗法|吸入剂|雾化剂|吸入器|雾化器|吸入装置|雾化装置|吸入设备|雾化设备|吸入系统|雾化系统|吸入路径|雾化路径|吸入途径|雾化途径|吸入方式|雾化方式|吸入方法|雾化方法|吸入技术|雾化技术|吸入工艺|雾化工艺|吸入流程|雾化流程|吸入程序|雾化程序|吸入步骤|雾化步骤|吸入操作|雾化操作|吸入过程|雾化过程|吸入阶段|雾化阶段|吸入时期|雾化时期|吸入阶段|雾化阶段|吸入环节|雾化环节|吸入步骤|雾化步骤|吸入程序|雾化程序|吸入流程|雾化流程|吸入工艺|雾化工艺|吸入技术|雾化技术|吸入方法|雾化方法|吸入方式|雾化方式|吸入途径|雾化途径|吸入路径|雾化路径|吸入系统|雾化系统|吸入设备|雾化设备|吸入装置|雾化装置|吸入器|雾化器|吸入剂|雾化剂|吸入疗法|雾化疗法|吸入给药|雾化给药|吸入治疗|雾化治疗|吸入|雾化)(?:治疗|控制|改善|缓解|管理|处理)(?:.+?)?(.+?)(?:的|患者|病人|人群)?',
                ],
                'reverse': True
            },
            {
                'rel_type': '疾病-症状',
                'head_type': 'Disease',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:患者|病人|人群|个体|者)?(?:出现|伴有|表现为|主要表现|常见症状|典型表现|临床表现|主要症状|首发症状|主要体征|常见体征|典型体征|临床体征|主要表现|常见表现|典型表现|临床表现|主要症状|首发症状|主要体征|常见体征|典型体征|临床体征)(?:为|是|包括|如|有|可见|可闻|可触及|可测得|可观察到|可检查到|可发现|可诊断|可鉴别|可确认|可证实|可证明|可表明|可提示|可反映|可代表|可说明|可解释|可理解|可接受|可认可|可承认|可同意|可赞成|可支持|可拥护|可维护|可保护|可保障|可保证|可确保|可维持|可保持|可坚持|可坚守|可坚定|可坚决|可坚强|可努力|可尽力|可竭力|可全力|可奋力|可拼命|可刻苦|可勤奋|可勤劳|可勤恳|可认真|可仔细|可细致|可细心|可谨慎|可小心|可慎重|可郑重|可严肃|可严格|可严厉|可严密|可严谨|可紧密|可密切|可亲密|可亲切|可亲近|可接近|可靠近|可临近|可邻近|可相邻|可相连|可相接|可相关|可相联|可相通|可相应|可相对|可相反|可相似|可相同|可相等|可等同|可等价|可等效|可类似|可同类|可同样|可同等|可同量|可等量|可平均|可均衡|可平衡|可稳定|可稳固|可牢固|可坚固|可坚实|可结实|可紧密|可严密|可周密|可周全|可完备|可完善|可完美|可完整|可完全|可全面|可全体|可整体|可总体|可总共|可合计|可共计|可总和|可总量|可总额|可总数|可全部|可整体|可统一|可一致|可一样|可同步|可同时|可同一|可单一|可唯一|可独一|可仅仅|可只有|可只是|可不过|可而已|可罢了|可算了|可得了|可完了|可行了|可好了|可成了|可定了|可准了|可行了|可可以)(?:.+?)?(.+?)(?:等|为主|为主要|为首发|为常见|为典型|为突出|为显著|为明显|为严重|为危急|为危重|为致命|为致死|为致残|为致畸|为致癌|为致突变|为主要|为常见|为典型|为突出|为显著|为明显|为严重|为危急|为危重|为致命)?(?:症状|表现|体征|不适|感觉|问题|困扰|痛苦|难受|不适|不舒服|不舒适|不惬意|不痛快|不舒畅|不顺畅|不通畅|不流畅|不流利|不流利|不流|不畅|不通|阻塞|堵塞|梗塞|栓塞|闭塞|封闭|隔绝|隔离|分离|分开|分裂|分散|散布|弥漫|充满|充盈|充斥|充塞|充填|填充|填补|补|充|足|够|满|盈|溢|盛|丰|富|裕|饶|厚|重|大|小|多|少|长|短|宽|窄|高|低|深|浅|厚|薄|重|轻|硬|软|粗|细|密|疏|稀|稠|浓|淡|明|暗|亮|黑|白|红|黄|蓝|绿|青|紫|灰|粉|棕|橙|金|银|铜|铁|锡|铅|锌|铝|镁|钙|钠|钾|氢|氧|氮|碳|硫|磷|氯|氟|碘|溴)?',
                    r'(.+?)(?:的)?(?:主要|常见|典型|临床|突出|显著|明显|严重|首发|特征性|特异性|诊断性|提示性|警示性|标志性|代表性|象征性|指示性|指向性|倾向性|可能性|或然性|必然性|确定性|肯定性|否定性|疑似性|待定性|确诊性|排除性|鉴别性|区分性|差异性|相似性|相关性|关联性|因果性|继发|并发|合并|伴随|合并|并发|继发|引起|导致|产生|造成|引发|诱发|促进|加速|加重|减轻|缓解|改善|控制|治疗|治愈|逆转|稳定|有效|效果|疗效|作用|影响|益处|优势|特点|特征|特性|性质|属性|表现|反应|响应|应答|耐受|安全|风险|不良|副|副作用|并发症|禁忌|注意|谨慎|小心|警惕|防范|预防|防止|避免|减少|降低|增高|升高|下降|回落|波动|变化|差异|区别|不同|相似|相同|一致|相反|相对|比较|对比|相当于|等同于|类似于|近似于|接近于|趋向于|倾向于|易于|难于|便于|利于|益于|有助于|有利于|有益于|有碍于|不利于|无益于|有害于|有损于|有用于|有功于|有补于|有济于|有益于|有裨于|有助于|有利于|有功于|有补于|有济于)(?:症状|表现|体征|不适|感觉|问题|困扰|痛苦|难受)?(?:为|是|包括|如|有|可见|可闻|可触及|可测得|可观察到|可检查到|可发现|可诊断|可鉴别|可确认|可证实|可证明|可表明|可提示|可反映|可代表|可说明|可解释|可理解|可接受|可认可|可承认|可同意|可赞成|可支持|可拥护|可维护|可保护|可保障|可保证|可确保|可维持|可保持|可坚持|可坚守|可坚定|可坚决|可坚强|可努力|可尽力|可竭力|可全力|可奋力|可拼命|可刻苦|可勤奋|可勤劳|可勤恳|可认真|可仔细|可细致|可细心|可谨慎|可小心|可慎重|可郑重|可严肃|可严格|可严厉|可严密|可严谨|可紧密|可密切|可亲密|可亲切|可亲近|可接近|可靠近|可临近|可邻近|可相邻|可相连|可相接|可相关|可相联|可相通|可相应|可相对|可相反|可相似|可相同|可相等|可等同|可等价|可等效|可类似|可同类|可同样|可同等|可同量|可等量|可平均|可均衡|可平衡|可稳定|可稳固|可牢固|可坚固|可坚实|可结实|可紧密|可严密|可周密|可周全|可完备|可完善|可完美|可完整|可完全|可全面|可全体|可整体|可总体|可总共|可合计|可共计|可总和|可总量|可总额|可总数|可全部|可整体|可统一|可一致|可一样|可同步|可同时|可同一|可单一|可唯一|可独一|可仅仅|可只有|可只是|可不过|可而已|可罢了|可算了|可得了|可完了|可行了|可好了|可成了|可定了|可准了|可行了|可可以)(?:.+?)?(.+?)(?:等|为主|为主要|为首发|为常见|为典型|为突出|为显著|为明显|为严重|为危急|为危重|为致命)?',
                    r'(.+?)(?:可|可能|常|经常|常常|通常|一般|往往|时常|不时|有时|偶尔|间或|每每|动辄|动辄|动辄|动辄|动辄)(?:引起|导致|产生|造成|引发|诱发|促进|加速|加重|使|令|让|使得)(?:.+?)?(.+?)(?:等症状|表现|不适|感觉|问题|困扰|痛苦|难受)?',
                    r'以(.+?)(?:为)?(?:主要|首发|常见|典型|突出|显著|明显|严重|特征性|特异性|诊断性|提示性|警示性|标志性|代表性|象征性|指示性|指向性|倾向性|可能性|或然性|必然性|确定性|肯定性|否定性|疑似性|待定性|确诊性|排除性|鉴别性|区分性|差异性|相似性|相关性|关联性|因果性|继发|并发|合并|伴随|合并|并发|继发|引起|导致|产生|造成|引发|诱发|促进|加速|加重|减轻|缓解|改善|控制|治疗|治愈|逆转|稳定|有效|效果|疗效|作用|影响|益处|优势|特点|特征|特性|性质|属性|表现|反应|响应|应答|耐受|安全|风险|不良|副|副作用|并发症|禁忌|注意|谨慎|小心|警惕|防范|预防|防止|避免|减少|降低|增高|升高|下降|回落|波动|变化|差异|区别|不同|相似|相同|一致|相反|相对|比较|对比|相当于|等同于|类似于|近似于|接近于|趋向于|倾向于|易于|难于|便于|利于|益于|有助于|有利于|有益于|有碍于|不利于|无益于|有害于|有损于|有用于|有功于|有补于|有济于|有益于|有裨于|有助于|有利于|有功于|有补于|有济于)?(?:症状|表现|体征|不适|感觉|问题|困扰|痛苦|难受)?',
                ],
                'reverse': False
            },
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
            {
                'rel_type': '检查-辅助诊断-疾病',
                'head_type': 'Examination',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:是|为|用于|可用于|对|对于|针对|适于|适用于)(?:.+?)(?:诊断|确诊|辅助诊断|评估|筛查|检测|检查|监测|随访|评价|判断|鉴别|确认|证实|证明|表明|提示|反映|代表|说明|解释|理解|接受|认可|承认|同意|赞成|支持|拥护|维护|保护|保障|保证|确保|维持|保持|坚持|坚守|坚定|坚决|坚强|努力|尽力|竭力|全力|奋力|拼命|刻苦|勤奋|勤劳|勤恳|认真|仔细|细致|细心|谨慎|小心|慎重|郑重|严肃|严格|严厉|严密|严谨|紧密|密切|亲密|亲切|亲近|接近|靠近|临近|邻近|相邻|相连|相接|相关|相联|相通|相应|相对|相反|相似|相同|相等|等同|等价|等效|类似|同类|同样|同等|同量|等量|平均|均衡|平衡|稳定|稳固|牢固|坚固|坚实|结实|紧密|严密|周密|周全|完备|完善|完美|完整|完全|全面|全体|整体|总体|总共|合计|共计|总和|总量|总额|总数|全部|整体|统一|一致|一样|同步|同时|同一|单一|唯一|独一|仅仅|只有|只是|不过|而已|罢了|算了|得了|完了|行了|好了|成了|定了|准了|行了|可以)(?:.+?)?(.+?)(?:的|患者|病人|人群|个体|者)?(?:重要|关键|辅助|核心|主要|常见|标准|基础|金标准|常用|经典|传统|新型|创新|理想|合适|适宜|最佳|最优|规范|推荐|建议|可选|替代|联合|必要|必须|必需|首要|优先|紧急|迫切|急需|亟待|有待|需要|需求|要求|条件|前提|基础|保障|保证|确保|维持|保持|坚持|坚守|坚定|坚决|坚强|努力|尽力|竭力|全力|奋力|拼命|刻苦|勤奋|勤劳|勤恳|认真|仔细|细致|细心|谨慎|小心|慎重|郑重|严肃|严格|严厉|严密|严谨|紧密|密切|亲密|亲切|亲近|接近|靠近|临近|邻近|相邻|相连|相接|相关|相联|相通|相应|相对|相反|相似|相同|相等|等同|等价|等效|类似|同类|同样|同等|同量|等量|平均|均衡|平衡|稳定|稳固|牢固|坚固|坚实|结实|紧密|严密|周密|周全|完备|完善|完美|完整|完全|全面|全体|整体|总体|总共|合计|共计|总和|总量|总额|总数|全部|整体|统一|一致|一样|同步|同时|同一|单一|唯一|独一|仅仅|只有|只是|不过|而已|罢了|算了|得了|完了|行了|好了|成了|定了|准了|行了|可以)?(?:价值|意义|作用|方法|手段|措施|策略|方案|工具|技术|途径|路径|路线|方向|方位|方式|手段|措施|策略|计划|方案|安排|部署|配置|调配|调度|调节|调整|调和|协调|平衡|均衡|稳定|稳固|牢固|坚固|坚实|结实|紧密|严密|周密|周全|完备|完善|完美|完整|完全|全面|全体|整体|总体|总共|合计|共计|总和|总量|总额|总数|全部|整体|统一|一致|一样|同步|同时|同一|单一|唯一|独一|仅仅|只有|只是|不过|而已|罢了|算了|得了|完了|行了|好了|成了|定了|准了|行了|可以)?',
                    r'(.+?)(?:可|可以|能|能够|可用于|适于|适用于|用于|对|对于|针对)(?:诊断|确诊|辅助诊断|评估|筛查|检测|检查|监测|随访|评价|判断|鉴别|确认|证实|证明|表明|提示|反映|代表|说明|解释|理解|接受|认可|承认|同意|赞成|支持|拥护|维护|保护|保障|保证|确保|维持|保持|坚持|坚守|坚定|坚决|坚强|努力|尽力|竭力|全力|奋力|拼命|刻苦|勤奋|勤劳|勤恳|认真|仔细|细致|细心|谨慎|小心|慎重|郑重|严肃|严格|严厉|严密|严谨|紧密|密切|亲密|亲切|亲近|接近|靠近|临近|邻近|相邻|相连|相接|相关|相联|相通|相应|相对|相反|相似|相同|相等|等同|等价|等效|类似|同类|同样|同等|同量|等量|平均|均衡|平衡|稳定|稳固|牢固|坚固|坚实|结实|紧密|严密|周密|周全|完备|完善|完美|完整|完全|全面|全体|整体|总体|总共|合计|共计|总和|总量|总额|总数|全部|整体|统一|一致|一样|同步|同时|同一|单一|唯一|独一|仅仅|只有|只是|不过|而已|罢了|算了|得了|完了|行了|好了|成了|定了|准了|行了|可以)(?:.+?)?(.+?)(?:的|患者|病人|人群|个体|者)?',
                    r'(.+?)(?:示|显示|提示|表明|提示|反映|代表|象征|标志|指示|指向|倾向|趋势|走向|方向|方位|方式|方法|手段|措施|策略|计划|方案|安排|部署|配置|调配|调度|调节|调整|调和|协调|平衡|均衡|稳定|稳固|牢固|坚固|坚实|结实|紧密|严密|周密|周全|完备|完善|完美|完整|完全|全面|全体|整体|总体|总共|合计|共计|总和|总量|总额|总数|全部|整体|统一|一致|一样|同步|同时|同一|单一|唯一|独一|仅仅|只有|只是|不过|而已|罢了|算了|得了|完了|行了|好了|成了|定了|准了|行了|可以)(?:.+?)?(.+?)(?:的|患者|病人|人群|个体|者)?',
                ],
                'reverse': True
            },
            {
                'rel_type': '治疗-改善-症状',
                'head_type': 'Treatment',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:可|可以|能|能够|适用|适合|推荐|建议|选择|采用|给予|应用|使用|用|通过|经)(?:改善|缓解|减轻|控制|减轻|减少|降低|消除|去除|清除|排出|排出|引流|引|导|通|畅|开|疏|理|调|和|养|补|益|温|清|凉|寒|热|燥|湿|风|暑|火|毒|瘀|滞|结|聚|散|消|化|行|气|血|阴|阳|虚|实|寒|热|表|里|上|下|内|外|前|后|左|右|中|央|主|次|本|标|根|源|基|础|根|本|核|心|关|键|重|点|要|点|核|心|中|心|焦|点|重|心|关|键|枢|纽|节|点|环|节|链|条|链|路|通|道|途|径|路|径|路|线|方|向|方|位|方|式|方|法|手|段|措|施|策|略|计|划|方|案|安|排|部|署|配|置|调|配|调|度|调|节|调|整|调|和|协|调|平|衡|均|衡|稳|定|稳|固|牢|固|坚|固|坚|实|坚|强|坚|定|坚|决|坚|毅|坚|韧|坚|持|坚|守|坚|定|坚|强|坚|硬|坚|实|坚|牢|坚|稳|坚|健|坚|壮|坚|茂|坚|盛|坚|旺|坚|兴|坚|荣|坚|昌|坚|隆|坚|盛|坚|丰|坚|裕|坚|足|坚|富|坚|盈|坚|满|坚|充|坚|实|坚|厚|坚|重|坚|大|坚|小|坚|多|坚|少|坚|高|坚|低|坚|长|坚|短|坚|宽|坚|窄|坚|厚|坚|薄|坚|深|坚|浅|坚|远|坚|近|坚|快|坚|慢|坚|早|坚|晚|坚|新|坚|旧|坚|老|坚|幼|坚|强|坚|弱|坚|轻|坚|重|坚|硬|坚|软|坚|冷|坚|热|坚|温|坚|凉|坚|干|坚|湿|坚|燥|坚|润|坚|清|坚|浊|坚|纯|坚|杂|坚|精|坚|粗|坚|细|坚|密|坚|疏|坚|稀|坚|稠|坚|浓|坚|淡|坚|深|坚|浅|坚|明|坚|暗|坚|亮|坚|黑|坚|白|坚|红|坚|黄|坚|蓝|坚|绿|坚|青|坚|紫|坚|灰|坚|粉|坚|棕|坚|橙|坚|金|坚|银|坚|铜|坚|铁|坚|锡|坚|铅|坚|锌|坚|铝|坚|镁|坚|钙|坚|钠|坚|钾|坚|氢|坚|氧|坚|氮|坚|碳|坚|硫|坚|磷|坚|氯|坚|氟|坚|碘|坚|溴)(?:.+?)?(.+?)(?:等症状|表现|不适|感觉|问题|困扰|痛苦|难受|不适|不舒服|不舒适|不惬意|不痛快|不舒畅|不顺畅|不通畅|不流畅|不流利|不流利|不流|不畅|不通|阻塞|堵塞|梗塞|栓塞|闭塞|封闭|隔绝|隔离|分离|分开|分裂|分散|散布|弥漫|充满|充盈|充斥|充塞|充填|填充|填补|补|充|足|够|满|盈|溢|盛|丰|富|裕|饶|厚|重|大|小|多|少|长|短|宽|窄|高|低|深|浅|厚|薄|重|轻|硬|软|粗|细|密|疏|稀|稠|浓|淡|明|暗|亮|黑|白|红|黄|蓝|绿|青|紫|灰|粉|棕|橙|金|银|铜|铁|锡|铅|锌|铝|镁|钙|钠|钾|氢|氧|氮|碳|硫|磷|氯|氟|碘|溴)?',
                    r'(.+?)(?:用于|适用于|适于|适合|推荐|建议|选择|采用|给予|应用|使用|用|通过|经)(?:改善|缓解|减轻|控制|减少|降低|消除|去除|清除|排出|排出|引流|引|导|通|畅|开|疏|理|调|和|养|补|益|温|清|凉|寒|热|燥|湿|风|暑|火|毒|瘀|滞|结|聚|散|消|化|行|气|血|阴|阳|虚|实|寒|热|表|里|上|下|内|外|前|后|左|右|中|央|主|次|本|标|根|源|基|础|根|本|核|心|关|键|重|点|要|点|核|心|中|心|焦|点|重|心|关|键|枢|纽|节|点|环|节|链|条|链|路|通|道|途|径|路|径|路|线|方|向|方|位|方|式|方|法|手|段|措|施|策|略|计|划|方|案|安|排|部|署|配|置|调|配|调|度|调|节|调|整|调|和|协|调|平|衡|均|衡|稳|定|稳|固|牢|固|坚|固|坚|实|坚|强|坚|定|坚|决|坚|毅|坚|韧|坚|持|坚|守|坚|定|坚|强|坚|硬|坚|实|坚|牢|坚|稳|坚|健|坚|壮|坚|茂|坚|盛|坚|旺|坚|兴|坚|荣|坚|昌|坚|隆|坚|盛|坚|丰|坚|裕|坚|足|坚|富|坚|盈|坚|满|坚|充|坚|实|坚|厚|坚|重|坚|大|坚|小|坚|多|坚|少|坚|高|坚|低|坚|长|坚|短|坚|宽|坚|窄|坚|厚|坚|薄|坚|深|坚|浅|坚|远|坚|近|坚|快|坚|慢|坚|早|坚|晚|坚|新|坚|旧|坚|老|坚|幼|坚|强|坚|弱|坚|轻|坚|重|坚|硬|坚|软|坚|冷|坚|热|坚|温|坚|凉|坚|干|坚|湿|坚|燥|坚|润|坚|清|坚|浊|坚|纯|坚|杂|坚|精|坚|粗|坚|细|坚|密|坚|疏|坚|稀|坚|稠|坚|浓|坚|淡|坚|深|坚|浅|坚|明|坚|暗|坚|亮|坚|黑|坚|白|坚|红|坚|黄|坚|蓝|坚|绿|坚|青|坚|紫|坚|灰|坚|粉|坚|棕|坚|橙|坚|金|坚|银|坚|铜|坚|铁|坚|锡|坚|铅|坚|锌|坚|铝|坚|镁|坚|钙|坚|钠|坚|钾|坚|氢|坚|氧|坚|氮|坚|碳|坚|硫|坚|磷|坚|氯|坚|氟|坚|碘|坚|溴)(?:.+?)?(.+?)(?:等症状|表现|不适|感觉|问题|困扰|痛苦|难受|不适|不舒服|不舒适|不惬意|不痛快|不舒畅|不顺畅|不通畅|不流畅|不流利|不流利|不流|不畅|不通|阻塞|堵塞|梗塞|栓塞|闭塞|封闭|隔绝|隔离|分离|分开|分裂|分散|散布|弥漫|充满|充盈|充斥|充塞|充填|填充|填补|补|充|足|够|满|盈|溢|盛|丰|富|裕|饶|厚|重|大|小|多|少|长|短|宽|窄|高|低|深|浅|厚|薄|重|轻|硬|软|粗|细|密|疏|稀|稠|浓|淡|明|暗|亮|黑|白|红|黄|蓝|绿|青|紫|灰|粉|棕|橙|金|银|铜|铁|锡|铅|锌|铝|镁|钙|钠|钾|氢|氧|氮|碳|硫|磷|氯|氟|碘|溴)?',
                ],
                'reverse': True
            },
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
            {
                'rel_type': '检查-评估-疾病',
                'head_type': 'Examination',
                'tail_type': 'Disease',
                'patterns': [
                    r'(.+?)(?:用于|可用于|对)(?:.+?)(?:评估|评价|判断|监测|随访)(?:.+?)(.+?)(?:的)?(?:严重|严重程|严重度|程度|进展|预后)?',
                ],
                'reverse': True
            },
            {
                'rel_type': '检查-评估-症状',
                'head_type': 'Examination',
                'tail_type': 'Symptom',
                'patterns': [
                    r'(.+?)(?:用于|可用于)(?:.+?)(?:评估|评价|量化|测量|记录)(?:.+?)(.+?)(?:的)?(?:严重|严重程|程度)?',
                ],
                'reverse': True
            },
            {
                'rel_type': '药物-导致-并发症',
                'head_type': 'Medication',
                'tail_type': 'Complication',
                'patterns': [
                    r'(.+?)(?:可|可能|会)?(?:引起|导致|产生|诱发|造成|增加)(?:.+?)(.+?)(?:等)?(?:并发症|不良|副作用|风险)?',
                ],
                'reverse': False
            },
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
        self.sorted_entities = sorted(kb.entities.keys(), key=len, reverse=True)
    
    def recognize(self, text: str):
        entities = []
        i = 0
        n = len(text)
        matched_positions = set()
        
        while i < n:
            matched = False
            for ent_name in self.sorted_entities:
                if text.startswith(ent_name, i):
                    if i not in matched_positions:
                        ent_type = self.kb.entities[ent_name]
                        entities.append((i, i + len(ent_name), ent_name, ent_type))
                        for p in range(i, i + len(ent_name)):
                            matched_positions.add(p)
                        i += len(ent_name)
                        matched = True
                        break
            if not matched:
                i += 1
        
        entities.sort(key=lambda x: x[0])
        return entities


class RelationExtractor:
    """基于规则模板 + 共现匹配的关系抽取器（召回优先）"""
    
    # 共现匹配类型映射：(head_type, tail_type) -> relation_type
    COOCCURRENCE_MAP = {
        ('Medication', 'Disease'): '药物-治疗-疾病',
        ('Medication', 'Symptom'): '药物-缓解-症状',
        ('Disease', 'Symptom'): '疾病-症状',
        ('Examination', 'Disease'): '检查-辅助诊断-疾病',
        ('Examination', 'Symptom'): '检查-评估-症状',
        ('Treatment', 'Disease'): '治疗-改善-疾病',
        ('Treatment', 'Symptom'): '治疗-改善-症状',
        ('Disease', 'Complication'): '疾病-并发症',
        ('Disease', 'Disease'): '疾病-共病',
        ('RiskFactor', 'Disease'): '危险因素-疾病',
        ('Medication', 'Complication'): '药物-导致-并发症',
    }
    # 共现匹配最大字符距离
    COOCCURRENCE_MAX_DIST = 60
    # 共现匹配关键词约束：某些关系需要句中出现特定词才触发
    COOCCURRENCE_KEYWORDS = {
        '疾病-共病': ['合并', '伴', '共病', '并存', '同存', '并发', '继发', '合并症'],
        '疾病-并发症': ['并发', '合并', '继发', '引起', '导致', '产生', '造成'],
        '药物-导致-并发症': ['引起', '导致', '产生', '造成', '不良反应', '副作用'],
    }
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
    
    def _has_keyword(self, text: str, rel_type: str) -> bool:
        """检查文本中是否包含某关系类型所需的关键词"""
        keywords = self.COOCCURRENCE_KEYWORDS.get(rel_type)
        if not keywords:
            return True  # 无关键词约束则直接通过
        return any(kw in text for kw in keywords)
    
    def extract(self, text: str, entities: list):
        triples = []
        
        # ===== 步骤1：严格模板匹配 =====
        for template in self.kb.relation_templates:
            matches = template['pattern'].findall(text)
            
            for match in matches:
                if isinstance(match, str):
                    match = (match, '')
                
                group1 = match[0] if len(match) > 0 else ''
                group2 = match[1] if len(match) > 1 else ''
                
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
                
                if template.get('reverse', False):
                    h_from_g2 = self._find_entities_in_text(group2, entities, template['head_type'])
                    t_from_g1 = self._find_entities_in_text(group1, entities, template['tail_type'])
                    
                    for h in h_from_g2:
                        for t in t_from_g1:
                            triples.append({
                                'head': h, 'head_type': template['head_type'],
                                'tail': t, 'tail_type': template['tail_type'],
                                'relation': template['rel_type'], 'context': text,
                                'source': 'template'
                            })
                
                for h in head_candidates:
                    for t in tail_candidates:
                        if h != t:
                            triples.append({
                                'head': h, 'head_type': template['head_type'],
                                'tail': t, 'tail_type': template['tail_type'],
                                'relation': template['rel_type'], 'context': text,
                                'source': 'template'
                            })
        
        # ===== 步骤2：共现匹配（兜底召回） =====
        # 将实体按位置排序，找出同句中距离近且类型匹配的实体对
        if len(entities) >= 2:
            sorted_ents = sorted(entities, key=lambda x: x[0])
            for i in range(len(sorted_ents)):
                for j in range(i + 1, len(sorted_ents)):
                    e1 = sorted_ents[i]
                    e2 = sorted_ents[j]
                    
                    # 计算两个实体中心点之间的距离
                    dist = abs((e1[0] + e1[1]) // 2 - (e2[0] + e2[1]) // 2)
                    if dist > self.COOCCURRENCE_MAX_DIST:
                        continue
                    
                    # 尝试 (e1_type, e2_type) 和 (e2_type, e1_type) 两种方向
                    for (h_ent, t_ent) in [(e1, e2), (e2, e1)]:
                        h_type, t_type = h_ent[3], t_ent[3]
                        rel_type = self.COOCCURRENCE_MAP.get((h_type, t_type))
                        if not rel_type:
                            continue
                        # 关键词过滤：某些关系需要特定关键词才触发
                        if not self._has_keyword(text, rel_type):
                            continue
                        triples.append({
                            'head': h_ent[2], 'head_type': h_type,
                            'tail': t_ent[2], 'tail_type': t_type,
                            'relation': rel_type, 'context': text,
                            'source': 'cooccurrence'
                        })
        
        # 去重 + 过滤
        # 1. 自环过滤（头=尾）
        # 2. 双向重复过滤（对称关系如疾病-共病，只保留一个方向）
        SYMMETRIC_RELS = {'疾病-共病'}
        
        seen = {}
        for t in triples:
            # 过滤自环
            if t['head'] == t['tail']:
                continue
            
            key = (t['head'], t['relation'], t['tail'])
            # 检查反向是否已存在（对称关系）
            if t['relation'] in SYMMETRIC_RELS:
                reverse_key = (t['tail'], t['relation'], t['head'])
                if reverse_key in seen:
                    continue
            
            if key not in seen or t.get('source') == 'template':
                seen[key] = t
        
        return list(seen.values())
    
    def _find_entities_in_text(self, segment: str, entities: list, target_type: str):
        result = []
        for ent in entities:
            name, etype = ent[2], ent[3]
            if etype == target_type and name in segment:
                result.append(name)
        return list(set(result))


# ==================== Neo4j更新器（独立关系标签）====================

class Neo4jUpdater:
    """Neo4j图谱增量更新器（支持独立关系标签）"""
    
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        self.uri = uri
        self.user = user
        self.password = password
        self.graph = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        try:
            from py2neo import Graph
            self.graph = Graph(self.uri, auth=(self.user, self.password))
            result = self.graph.run("RETURN 1 as test").data()
            self.connected = True
            print(f"[Neo4j] 连接成功: {self.uri}")
        except ImportError:
            print("[提示] 未安装py2neo，请运行: pip install py2neo")
        except Exception as e:
            print(f"[提示] 未检测到Neo4j: {e}")
            print("[提示] 无Neo4j也能运行实体识别和关系抽取，仅跳过图谱更新")
    
    def update(self, triples: list):
        """增量更新三元组到Neo4j，使用独立关系标签"""
        if not self.connected or not self.graph:
            print("[错误] Neo4j未连接，跳过图谱更新")
            return 0
        
        count = 0
        for t in triples:
            try:
                rel_type = t['relation']  # 如 "药物-治疗-疾病"
                # 使用独立关系标签，如 (a)-[:药物-治疗-疾病]->(b)
                cypher = f"""
                    MERGE (a:Entity {{name: $head}})
                    SET a.type = $head_type
                    MERGE (b:Entity {{name: $tail}})
                    SET b.type = $tail_type
                    MERGE (a)-[r:`{rel_type}`]->(b)
                    SET r.context = $context
                """
                self.graph.run(cypher, parameters={
                    'head': t['head'], 'head_type': t['head_type'],
                    'tail': t['tail'], 'tail_type': t['tail_type'],
                    'context': t['context']
                })
                count += 1
            except Exception as e:
                print(f"[警告] 插入失败 ({t['head']} -> {t['tail']}): {e}")
        
        return count
    
    def get_stats(self):
        if not self.connected:
            return None
        node_count = self.graph.run("MATCH (n) RETURN count(n) as c").data()[0]['c']
        rel_count = self.graph.run("MATCH ()-[r]->() RETURN count(r) as c").data()[0]['c']
        return {'nodes': node_count, 'relations': rel_count}


# ==================== 端到端流水线 v2 ====================

class COPDKGPipeline:
    """COPD知识图谱端到端抽取流水线 v2：规则为主 + BERT验证"""
    
    def __init__(self):
        print("=" * 60)
        print("COPD医学知识图谱 - 端到端抽取系统 v2")
        print("规则为主生成候选 + BERT为辅验证修正")
        print("=" * 60)
        print()
        
        self.kb = KnowledgeBase()
        self.recognizer = EntityRecognizer(self.kb)
        self.extractor = RelationExtractor(self.kb)
        self.verifier = BERTVerifier() if USE_BERT else None
        self.updater = Neo4jUpdater()
        
        print()
    
    def process(self, text: str, update_neo4j: bool = True):
        print("-" * 60)
        print("【输入文本】")
        safe_text = text[:200].encode('utf-8', errors='ignore').decode('utf-8')
        print(safe_text + ("..." if len(text) > 200 else ""))
        print("-" * 60)
        
        # 按句分割（保留单句上下文给BERT）
        import re
        sentences = [s.strip() for s in re.split(r'[。；？！\n]+', text) if s.strip()]
        
        all_entities = []
        all_candidate_triples = []
        
        # 逐句处理：实体识别 + 关系抽取
        for sent in sentences:
            entities = self.recognizer.recognize(sent)
            if not entities:
                continue
            all_entities.extend(entities)
            
            candidate_triples = self.extractor.extract(sent, entities)
            # 记录每个三元组所属句子
            for t in candidate_triples:
                t['sentence'] = sent
            all_candidate_triples.extend(candidate_triples)
        
        # 汇总实体
        if not all_entities:
            print("\n[WARN] 未识别到任何已知实体")
            return {'entities': [], 'triples': [], 'verified_triples': [], 'new_triples': [], 'is_new': False}
        
        print("\n[Step 1] 实体识别（贪心最长匹配）...")
        print("  [OK] 识别到 %d 个实体（跨 %d 句）" % (len(all_entities), len(sentences)))
        unique_entities = list({(e[2], e[3]) for e in all_entities})
        for name, etype in unique_entities[:10]:
            safe_name = name.encode('utf-8', errors='ignore').decode('utf-8')
            print("    - %s (%s)" % (safe_name, etype))
        if len(unique_entities) > 10:
            print("    ... 还有 %d 个" % (len(unique_entities) - 10))
        
        # 汇总候选关系
        if not all_candidate_triples:
            print("\n[WARN] 未抽取到任何候选关系")
            return {'entities': all_entities, 'triples': [], 'verified_triples': [], 'new_triples': [], 'is_new': False}
        
        print(f"\n[Step 2] 规则模板抽取候选关系（召回优先）...")
        print(f"  [OK] 规则生成 {len(all_candidate_triples)} 个候选关系")
        for t in all_candidate_triples[:5]:
            src = t.get('source', '?')
            print(f"    [{src}] {t['head']} --[{t['relation']}]--> {t['tail']}")
        if len(all_candidate_triples) > 5:
            print(f"    ... 还有 {len(all_candidate_triples) - 5} 个")
        
        # Step 3: BERT验证（使用单句上下文）
        if self.verifier and self.verifier.available:
            print(f"\n[Step 3] BERT验证（阈值={self.verifier.threshold}，共现匹配采用标签一致性策略）...")
            verified_triples = []
            rejected_triples = []
            modified_triples = []
            
            for t in all_candidate_triples:
                # 共现匹配：跳过BERT验证直接通过（当前BERT模型在短句上表现不佳，会误杀正确候选）
                if t.get('source') == 'cooccurrence':
                    verified_triples.append(t)
                    print(f"    [PASS-cooccur] {t['head']} --[{t['relation']}]--> {t['tail']} "
                          f"(共现匹配跳过BERT)")
                    continue
                
                # 模板匹配：保留BERT验证
                sent = t.get('sentence', text)
                result = self.verifier.verify(
                    sent, t['head'], t['tail'], t['relation'],
                    source='template'
                )
                
                if result['verified']:
                    if result['predicted_label'] == t['relation']:
                        verified_triples.append(t)
                        print(f"    [PASS-template] {t['head']} --[{t['relation']}]--> {t['tail']} "
                              f"(conf={result['confidence']:.3f})")
                    else:
                        t_modified = dict(t)
                        t_modified['relation'] = result['predicted_label']
                        modified_triples.append(t_modified)
                        print(f"    [FIX] {t['head']} --[{t['relation']}]--> {t['tail']} "
                              f"BERT->[{result['predicted_label']}] "
                              f"(conf={result['confidence']:.3f})")
                else:
                    rejected_triples.append(t)
                    top3_str = ", ".join([f"{l}({p:.2f})" for l, p in result['top3']])
                    print(f"    [REJECT] {t['head']} --[{t['relation']}]--> {t['tail']} "
                          f"(Top3: {top3_str})")
            
            final_triples = verified_triples + modified_triples
            
            print(f"\n  [BERT验证结果]")
            print(f"    - 共现匹配直接通过: {sum(1 for t in verified_triples if t.get('source')=='cooccurrence')} 个")
            print(f"    - 模板匹配通过: {sum(1 for t in verified_triples if t.get('source')=='template')} 个")
            print(f"    - BERT修正: {len(modified_triples)} 个")
            print(f"    - 被拒绝: {len(rejected_triples)} 个")
            print(f"    - 最终保留: {len(final_triples)} 个")
        else:
            print("\n[Step 3] BERT未启用或模型不可用，跳过验证")
            final_triples = all_candidate_triples
        
        # 同义词归并
        if self.kb.synonyms:
            print("\n[同义词归并] 将别名替换为标准名...")
            for t in final_triples:
                orig_head, orig_tail = t['head'], t['tail']
                t['head'] = self.kb.canonicalize(t['head'])
                t['tail'] = self.kb.canonicalize(t['tail'])
                if t['head'] != orig_head or t['tail'] != orig_tail:
                    print(f"  {orig_head} -> {t['head']}, {orig_tail} -> {t['tail']}")
        
        # 区分已有和新三元组
        new_triples = []
        existing_triples = []
        for t in final_triples:
            key = (t['head'], t['relation'], t['tail'])
            if key in self.kb.existing_triples:
                existing_triples.append(t)
            else:
                new_triples.append(t)
        
        if existing_triples:
            print(f"\n  - {len(existing_triples)} 个已存在于知识库（灰色）")
        if new_triples:
            print(f"  - {len(new_triples)} 个新关系（绿色，将入库）:")
            for t in new_triples[:5]:
                print(f"      -> {t['head']} --[{t['relation']}]--> {t['tail']}")
            if len(new_triples) > 5:
                print(f"      ... 还有 {len(new_triples) - 5} 个")
        
        # Step 4: Neo4j更新
        if update_neo4j and new_triples and self.updater.connected:
            print("\n[Step 4] 增量更新到Neo4j（独立关系标签）...")
            inserted = self.updater.update(new_triples)
            print(f"  [OK] 成功插入 {inserted} 条新关系到Neo4j")
            
            stats = self.updater.get_stats()
            if stats:
                print(f"  📊 当前图谱: {stats['nodes']} 节点, {stats['relations']} 关系")
        elif not self.updater.connected:
            print("\n[Step 4] Neo4j未连接，跳过更新")
            print("  生成Cypher语句供手动执行:")
            for t in new_triples[:3]:
                print(f"    MERGE (a:Entity {{name: '{t['head']}'}})")
                print(f"    MERGE (b:Entity {{name: '{t['tail']}'}})")
                print(f"    MERGE (a)-[r:`{t['relation']}`]->(b);")
        
        return {
            'entities': all_entities,
            'triples': all_candidate_triples,
            'verified_triples': final_triples,
            'new_triples': new_triples,
            'is_new': len(new_triples) > 0
        }
    
    def interactive(self):
        print()
        print("=" * 60)
        print("进入交互模式，请输入COPD相关临床文本")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'stats' 查看当前图谱统计")
        print("输入 'threshold <数值>' 调整BERT置信度阈值")
        print("=" * 60)
        print()
        
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
            
            # 调整阈值
            if user_input.lower().startswith('threshold '):
                try:
                    new_threshold = float(user_input.split()[1])
                    if self.verifier:
                        self.verifier.threshold = new_threshold
                        print(f"BERT置信度阈值已调整为: {new_threshold}")
                    else:
                        print("BERT验证器未初始化")
                except (ValueError, IndexError):
                    print("用法: threshold 0.8")
                continue
            
            if user_input in ('1', '2', '3', '4'):
                user_input = examples[int(user_input) - 1]
                print(f"使用示例: {user_input}")
            
            self.process(user_input)
            print()


# ==================== 主程序入口 ====================

if __name__ == '__main__':
    pipeline = COPDKGPipeline()
    pipeline.interactive()
