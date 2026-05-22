# -*- coding: utf-8 -*-
"""
方案C: COPD聚焦过滤
从282条全量结果中，只保留与COPD直接相关的术语
"""
import config  # 统一路径配置


import os
import json

INPUT_TSV = str(config.BASE_DIR / r"种子词典构建结果\29_全部中文文献_最终种子词典_严格清理.tsv")
OUTPUT_DIR = str(config.BASE_DIR / r"种子词典构建结果")

# ========== COPD核心关键词（强匹配） ==========
COPD_CORE_KEYWORDS = [
    '慢阻肺', 'COPD', '慢性阻塞性肺疾病', '阻塞性', '肺气肿', 
    '慢性支气管炎', '气流受限', '不完全可逆', 'AECOPD',
    'FEV1', 'FVC', 'DLCO', '一秒率', '一秒用力呼气容积', '用力肺活量',
    'GOLD', 'mMRC', 'CAT', 'BODE', '急性加重',
    'ICS', 'LABA', 'LAMA', 'SABA', 'SAMA',
    '吸入性糖皮质激素', '支气管扩张剂', '支气管舒张剂',
    '茶碱', '氨茶碱', 'NAC', 'N-乙酰半胱氨酸', '羧甲司坦',
    '戒烟', '氧疗', '肺康复', '无创通气', 'NIV', 'NPPV',
    'LTOT', '长期家庭氧疗', '长期氧疗',
    '肺减容', 'LVRS', '肺移植', '肺减容术',
    '吸烟', '烟草', '空气污染', '生物燃料', '职业粉尘', '呼吸道感染',
    '呼吸困难', '气短', '喘息', '咳痰', '胸闷',
    '气道炎症', '黏液高分泌', '全身炎症', '氧化应激', '气道高反应',
    '肺通气功能', '肺容量', '残气量', '肺总量', '肺活量',
    '深吸气量', 'IC', '肺弥散功能',
    '动脉血气', '脉搏血氧', '血气分析', '血氧饱和度',
    '营养支持', '运动训练', '呼吸训练', '阻抗训练', '运动能力',
    '合并症', '并发症',
    'Ensifentrine', '恩塞芬汀',
    'Dupilumab', '度普利尤单抗',
    'Mepolizumab', '美泊利珠单抗',
    'Azithromycin', '阿奇霉素',
    'Carbocisteine', '羧甲司坦',
]

# ========== COPD合并症白名单 ==========
COPD_COMORBIDITIES = [
    '心血管疾病', '缺血性心脏病', '冠心病', '心力衰竭', '充血性心力衰竭', '心衰',
    '肺动脉高压', 'PH', '肺心病', '慢性肺源性心脏病', '肺源性心脏病', '右心衰竭',
    '糖尿病', '2型糖尿病',
    '骨质疏松', '骨质疏松症',
    '肺癌', '肺部肿瘤',
    '阻塞性睡眠呼吸暂停', 'OSA', 'OSAHS',
    '呼吸衰竭', '呼衰', 'Ⅰ型呼吸衰竭', 'Ⅱ型呼吸衰竭',
    '肺炎', '肺部感染', '肺部并发症',
    '肺栓塞', '肺血栓栓塞',
    '肺结核', '结核',
    '抑郁症', '抑郁', '焦虑症', '焦虑',
    '代谢综合征',
    '心肌梗死', '心梗', '心绞痛', '胸痛',
    '贫血', '红细胞增多症', '胸腔积液', '肺结节',
    '支气管哮喘', '哮喘',
]

# ========== 非COPD强制黑名单 ==========
NON_COPD_BLACKLIST = {
    # 慢性咳嗽相关疾病（鉴别诊断，非COPD核心）
    'CVA', '咳嗽变异性哮喘',
    'PNDS', '鼻后滴流综合征', '上气道咳嗽综合征', 'UACS',
    'EB', '嗜酸粒细胞性支气管炎', '嗜酸性粒细胞性支气管炎',
    '躯体性咳敏综合征', '心因性咳嗽', '心理性咳嗽',
    '抽动性咳嗽', '抽动秽语综合征',
    '百日咳', '迁延性支气管炎',
    '咳嗽高敏感性', '咳嗽敏感性',
    # GERD相关（非COPD核心，尽管可合并）
    '胃食管反流病', '胃食管反流', 'GERD', 'GERC',
    '反流性食管炎', '反流性咽喉炎', '反流症状',
    '弱酸反流', '非酸反流', '胆汁反流', '异常非酸反流',
    '谨慎选择抗反流手', '除胃酸反流', '食管反流', '气道反流问卷',
    '食管反流监测',
    # COVID-19
    'COVID-19', '新型冠状病毒', '新冠肺炎', '新冠',
    # 其他非COPD感染/疾病
    '流行性感冒', '流感', '流感病毒',
    '肺炎支原体', '肺炎衣原体', '肺炎链球菌', '流感嗜血杆菌',
    '不动杆菌感染',
    '病毒感染',
    '囊性纤维化',
    '复发性多软骨炎',
    '急性咳嗽', '亚急性咳嗽', '慢性咳嗽病',
    '消化系统疾病病史',
    # 耳鼻喉
    '鼻窦炎', '变应性鼻炎', '过敏性鼻炎', '非变应性鼻炎',
    '变应性鼻炎还表现', '不佳的变应性鼻炎', '鼻后气管炎',
    '鼻后滴流',
    # 噪声/截断（Symptom）
    '约的痰嗜酸粒细胞', '咳嗽敏感性增', '咳嗽症状积分相比',
    '喷患者的咳嗽缓解', '体位转变后咳嗽', '减轻咳嗽症状',
    '咳嗽按性质又可分', '了解痰液量', '预测慢性咳嗽患者',
    '初诊慢性咳嗽患者', '痰嗜酸粒细者', '防止过无喘息',
    '痰细胞学检查嗜', '患者咳嗽症状', '胸痛咳嗽患者',
    '心理性咳嗽的林', '儿童慢性咳嗽定义', '起的慢性咳嗽',
    '频繁咳嗽影响休息', '咳嗽分外感咳嗽',
    '咳嗽生活质量测评', '咳嗽反射弧', '咳嗽外周感受器',
    '咳嗽症状积分', '咳嗽症状积分相比', '引感性咳嗽',
    '慢性刺激性咳嗽', '慢性咳嗽高敏感性', '迁延性感染性咳嗽',
    '体性咳嗽', '性咳嗽', '咳嗽后呕吐', '咳嗽亦', '加重咳嗽',
    '不伴咳痰', '咳嗽激发试验', '急性咳嗽异常体征',
    '【风热犯肺证】症见咳嗽频剧', '【湿热郁肺证】症见咳嗽',
    '【肺脾阳虚证】症见咳嗽', '【胃气上逆证】阵发性呛咳',
    '预测慢性咳嗽患者', '初诊慢性咳嗽患者',
    '综合性的咳嗽症状', '慢性咳嗽的林', '慢性咳嗽定义',
    '慢性咳嗽患者', '慢性咳嗽症状', '慢性咳嗽外',
    # 噪声（Medication）
    '镇咳药体激动剂', '典型反流症酸药物', '亟需开发新型药物',
    '糖皮质激素及抗', '建议给予抗菌药物', '受体阻断剂',
    '子类药物加', '雾化吸入利多卡', '人工合成的镇咳药',
    '激素治疗的反', '不建议使用吸入', '服标准剂量',
    '线胸片改变', '推荐联合吸入', '镇咳药物分',
    '其前体药物', '线胸片', '方药', '激动剂',
    '口服', '吸入', '吸入药物',
    '糖皮质激素及', '抗组胺药物及', '镇咳药物',
    '镇咳药', '镇咳药物分', '依赖性镇咳药', '非依赖性镇咳药',
    '中枢性镇咳药', '非麻醉性镇咳药', '人工合成的镇咳药',
    '苏子降气丸', '度普利尤单抗', '恩塞芬汀',
    # 噪声（Complication）
    '术后并发症及复发', '统的并发症', '弱酸反流患者漏诊',
    '除胃酸反流', '反流症状', '异常非酸反流',
    '胆汁反流', '弱酸反流', '非酸反流', '谨慎选择抗反流手',
    '气道反流问卷', '食管反流',
    # 噪声（Concept）
    '~onofi', '支气管舒', '气管软化', '减轻症状', '综合判断',
    '普通感冒', '全身症状', '风险提示',
    'Placebo', '安慰剂',
    # 噪声（TCM）
    '中成药', '祛邪',
    # 噪声（Pathology）
    '改善气流受限', '气道高反应性的稳', '肺气肿的形成',
    '气流受限相关症状',
    # 噪声（Disease）
    '气道神经源性炎症', '气道炎症', '气道病变',
    '肺部并发症', '消化系统疾病病史',
    '反复发生肺炎', '支气管炎', '结核中毒症状',
    '典型病原体', '流感嗜血杆',
    '变应性鼻炎还表现', '不佳的变应性鼻炎',
    '鼻窦炎症状',
    # 噪声（Treatment）
    '运动能力', '肺通气功',
    # 噪声（Anatomical）
    '红细胞', '巨噬细胞',
    # 噪声（RiskFactor）
    '抗感染', '混合感染', '不动杆菌感染', '先前的呼吸道感染',
    '细菌感染',
    # 噪声（Guideline）
    '指南制订工作组', '临床应用指南',
    # 噪声（Organization）
    '北京大学第三医院',
    # 其他
    '抗胆碱能药物',  # 太泛
    '减充血剂',
    '磷酸二酯酶抑制剂', '磷酸二酯酶',
    '生物制剂',
    '他汀类药物',
    '第一代抗组胺药物', '抗组胺药物',
    '精神类药物',
    '口服抗菌药物',
    '黏液溶解剂',
    '免疫调节剂',
    '糖皮质激素',
    '抗菌药物',
    '受体阻断剂',
}

# 额外过滤：某些类型中过于宽泛的术语
TOO_GENERAL = {
    '咳嗽',  # 症状类别中保留，但作为疾病实体要过滤
    '病变', '炎症', '症状', '病史',
    '诊断', '治疗', '评估', '管理', '预防', '随访',
    '康复', '检查', '检验', '研究', '分析',
    '建议', '推荐', '指南', '共识', '标准', '规范',
    '原则', '方法', '技术', '方案', '策略', '措施',
    '干预', '对照', '比较', '差异', '相关', '因素',
    '机制', '原理', '理论', '模型', '框架',
    '系统', '结构', '功能', '作用', '效果', '疗效',
    '安全', '风险', '危害', '不良', '事件', '反应',
    '持续', '反复', '间歇', '暂时', '永久',
    '局部', '全身', '单侧', '双侧',
    '恶化', '加重', '好转', '痊愈',
    '缓解', '控制', '稳定',
}


def is_copd_related(word, aliases, word_type):
    """判断术语是否与COPD相关"""
    all_text = word + ' ' + aliases
    
    # 0. 强制黑名单（最高优先级）
    if word in NON_COPD_BLACKLIST:
        return False, '非COPD黑名单'
    
    # 1. COPD核心关键词（强匹配）
    for kw in COPD_CORE_KEYWORDS:
        if kw in all_text:
            return True, f'COPD核心关键词:{kw}'
    
    # 2. 合并症白名单
    for com in COPD_COMORBIDITIES:
        if com in word:
            return True, f'合并症:{com}'
    
    # 3. 按类型的肺部/呼吸关键词匹配
    if word_type == 'Disease':
        # 疾病必须包含肺/支气管/气道/呼吸/胸/心/血管 或 是已知合并症
        lung_kw = ['肺', '支气管', '气道', '呼吸', '胸', '心', '血管', '血栓', '栓塞']
        if any(kw in word for kw in lung_kw):
            return True, '肺部疾病'
        # 其他非肺部疾病（如糖尿病、骨质疏松等）已由合并症白名单覆盖
        return False, '非肺部/非合并症疾病'
    
    elif word_type == 'Symptom':
        # 症状：保留COPD核心症状，过滤慢性咳嗽特异性症状
        copd_symptoms = ['呼吸困难', '气短', '喘息', '咳痰', '胸闷', '乏力',
            '呼吸困难', '气促', '呼吸急促', '呼吸窘迫',
            '咳嗽', '咳', '痰', '喘', '闷', '累', '乏',
            '发热', '烧', '寒战', '畏寒',
            '发绀', '紫绀', '口唇紫绀',
            '水肿', '浮肿', '腹胀',
            '头痛', '头晕', '失眠',
            '意识障碍', '嗜睡', '昏迷',
            '肌肉酸痛', '肌肉疼痛', '肢体酸痛',
            '消瘦', '体重下降', '食欲减退',
            '心悸', '心动过速',
            '自汗', '盗汗',
            '腹泻', '呕吐', '恶心',
            '流清涕', '流涕', '鼻塞',
            '胸痛',
        ]
        if any(s in word for s in copd_symptoms):
            # 但排除明显慢性咳嗽相关的
            cough_specific = ['咳嗽敏感性', '咳嗽反射', '咳嗽生活质量', '咳嗽外周',
                '咳嗽按性质', '咳嗽分外感', '咳嗽症状积分', '咳嗽激发',
                '慢性咳嗽', '亚急性咳嗽', '急性咳嗽', '迁延性咳嗽',
                '心因性咳嗽', '心理性咳嗽', '抽动性咳嗽',
                '咳嗽高敏感', '咳嗽高敏感性',
            ]
            if any(cs in word for cs in cough_specific):
                return False, '慢性咳嗽特异性症状'
            return True, 'COPD相关症状'
        return False, '非COPD症状'
    
    elif word_type == 'Medication':
        # 药物：保留COPD相关药物
        copd_meds = ['吸入', '雾化', '支气管', '激素', '茶碱', '抗生素',
            '抗菌', '祛痰', '抗氧化', '免疫调节', '疫苗',
            '镇咳', '止咳', '平喘', '解痉',
            '受体', '拮抗剂', '激动剂', '抑制剂',
            '单抗', '单克隆抗体',
            '胶囊', '片', '注射', '口服液', '丸', '散', '膏', '丹', '颗粒',
            'NAC', '乙酰半胱氨酸', '羧甲司坦',
            '糖皮质激素', '布地奈德', '氟替卡松', '倍氯米松',
            '沙美特罗', '福莫特罗', '茚达特罗', '奥达特罗',
            '噻托溴铵', '格隆溴铵', '乌美溴铵',
            '沙丁胺醇', '特布他林',
            '孟鲁司特', '扎鲁司特',
            '阿奇霉素', '红霉素', '克拉霉素',
            '甲泼尼龙', '泼尼松', '泼尼松龙', '地塞米松',
            '氨溴索', '溴己新', '厄多司坦',
            '磷酸二酯酶',
        ]
        # 但排除太泛的
        if word in TOO_GENERAL or len(word) <= 2:
            return False, '过于宽泛'
        if any(m in word for m in copd_meds):
            return True, 'COPD相关药物'
        return False, '非COPD药物'
    
    elif word_type == 'Examination':
        # 检查：保留肺部/呼吸相关检查
        copd_exams = ['肺', '支气管', '气道', '呼吸', '胸', 'FEV', 'FVC',
            'DLCO', 'CT', 'X线', '胸片', 'HRCT',
            '血气', '血氧', '氧饱和度', '脉搏血氧',
            '心电图', '超声', 'B超',
            '细胞学', '病理', '活检',
            '镜', '支气管镜', '胸腔镜',
            '功能', '容积', '流速', '流量', '容量',
            '血常规', '血生化', '肝肾功能', '电解质',
            'BMI', '体重指数', '身高', '体重',
            '痰', '诱导痰', 'FeNO', '一氧化氮',
            '量表', '问卷', '评分',
            'mMRC', 'CAT', 'BODE', 'SGRQ',
        ]
        if any(e in word for e in copd_exams):
            return True, 'COPD相关检查'
        return False, '非COPD检查'
    
    elif word_type == 'Treatment':
        # 治疗：保留COPD相关治疗
        copd_treats = ['肺', '支气管', '气道', '呼吸', '胸', '氧', '通气',
            '康复', '训练', '运动', '营养', '支持',
            '戒烟', '戒除', '戒断',
            '吸入', '雾化', '喷雾',
            '手术', '切除', '移植', '减容', 'LVRS',
            '机械', '无创', '有创', 'NIV', 'NPPV', 'CPAP',
            '针灸', '艾灸', '穴位', '贴敷', '贴',
            '体位', '引流', '排痰',
            ' vaccine', '疫苗', '接种',
            '中药', '中成药', '汤剂', '方剂',
            '宣肺', '止咳', '平喘', '化痰', '祛痰', '清热', '解毒',
            '补肺', '健脾', '益肾', '活血', '化瘀', '益气', '养阴',
            '舒肺', '益肺', '润肺', '养肺',
        ]
        if any(t in word for t in copd_treats):
            return True, 'COPD相关治疗'
        return False, '非COPD治疗'
    
    elif word_type == 'Pathology':
        # 病理：保留肺部/呼吸相关病理
        copd_path = ['肺', '支气管', '气道', '呼吸', '胸',
            '气流', '阻塞', '受限', '狭窄', '扩张',
            '炎症', '高反应', '高反应性', '过敏',
            '黏液', '分泌', '高分泌', '纤毛', '杯状细胞',
            '纤维化', '钙化', '坏死', '变性', '水肿', '充血', '淤血',
            '缺氧', '低氧', '高碳酸', 'CO2潴留', '潴留',
            '交换', '扩散', '弥散', '通气', '灌注',
            '氧化应激', '蛋白酶', '抗蛋白酶', '弹性蛋白酶',
            '中性粒细胞', '巨噬细胞', '嗜酸粒细胞', '淋巴细胞',
            '细胞因子', '炎性介质', '趋化因子',
        ]
        if any(p in word for p in copd_path):
            return True, 'COPD相关病理'
        return False, '非COPD病理'
    
    elif word_type == 'Complication':
        # 并发症：只保留已知合并症
        if any(c in word for c in COPD_COMORBIDITIES):
            return True, 'COPD合并症'
        return False, '非COPD合并症'
    
    elif word_type == 'RiskFactor':
        # 危险因素：保留已知COPD危险因素
        copd_risk = ['吸烟', '烟草', '香烟', '烟', '戒烟',
            '空气', '污染', 'PM2.5', 'PM10', '颗粒物',
            '燃料', '生物燃料', '煤炭', '木材', '柴火',
            '粉尘', '职业', '暴露', '接触',
            '感染', '呼吸道', '病毒', '细菌', '支原体', '衣原体',
            '遗传', '家族史', '基因', 'α1-抗胰蛋白酶', 'AAT',
            '年龄', '性别', '男性', '女性',
            '低体重', '营养不良', '社会经济',
            '气候', '温度', '湿度', '季节',
            '室内', '室外', '厨房', '通风',
            '氧化', '氮氧化物', '硫氧化物', '臭氧',
        ]
        if any(r in word for r in copd_risk):
            return True, 'COPD危险因素'
        return False, '非COPD危险因素'
    
    elif word_type == 'Guideline':
        # 指南：只保留COPD相关指南工具
        copd_guide = ['GOLD', 'mMRC', 'CAT', 'BODE', 'SGRQ',
            '慢性阻塞性肺疾病', 'COPD', '慢阻肺',
        ]
        if any(g in all_text for g in copd_guide):
            return True, 'COPD指南工具'
        return False, '非COPD指南'
    
    elif word_type == 'Organization':
        # 机构：保留主要医学组织
        org_keep = ['WHO', 'ERS', 'FDA', 'EMA', 'NMPA', 'ATS',
            'GOLD', '中华医学会', '呼吸病学分会',
        ]
        if any(o in all_text for o in org_keep):
            return True, '医学组织'
        return False, '非相关组织'
    
    elif word_type == 'TCM_Syndrome':
        # 中医证候：保留肺系相关证候
        tcm_keep = ['肺', '脾', '肾', '气', '痰', '湿', '寒', '热', '风',
            '阳虚', '阴虚', '气虚', '血虚', '血瘀',
            '表证', '里证', '实证', '虚证',
            '脉', '舌', '苔',
        ]
        if any(t in word for t in tcm_keep):
            return True, '肺系中医证候'
        return False, '非肺系证候'
    
    elif word_type == 'Concept':
        # 概念：只保留COPD相关概念
        copd_concept = ['病死率', '死亡率', '生存率', '预后',
            '生活质量', '健康相关生活质量', 'HRQoL',
            '急性加重', '加重频率', '加重风险',
            '疾病进展', '肺功能下降', '气流受限进展',
            '鉴别诊断', '诊断标准', '诊断流程',
            '氧化应激', '全身效应', '系统性炎症',
            '共病', '多病共存', '多重用药',
            '依从性', ' adherence', '自我管理',
            '分级', '分期', '分期', '分型', '分度',
            '严重程度', '风险分层', '评估',
        ]
        if any(c in word for c in copd_concept):
            return True, 'COPD相关概念'
        return False, '非COPD概念'
    
    elif word_type == 'Anatomical':
        # 解剖：保留呼吸系統解剖
        ana_keep = ['肺', '支气管', '气道', '气管', '喉', '鼻', '咽', '胸',
            '胸膜', '胸廓', '膈', '膈肌', '纵隔',
            '肺泡', '肺实质', '肺间质', '细支气管',
            '黏膜', '上皮', '纤毛', '腺体',
            '血管', '毛细血管', '肺动脉', '肺静脉',
            '淋巴', '淋巴结',
            '神经', '迷走神经', '受体',
            '细胞', '中性粒细胞', '巨噬细胞', '嗜酸粒细胞',
            '杯状细胞', '肥大细胞', '淋巴细胞', '浆细胞',
        ]
        if any(a in word for a in ana_keep):
            return True, '呼吸系统解剖'
        return False, '非呼吸系统解剖'
    
    return False, '未分类'


def main():
    print("=" * 60)
    print("COPD聚焦过滤 (方案C)")
    print("=" * 60)
    
    with open(INPUT_TSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()[1:]
    
    entries = []
    for line in lines:
        parts = line.strip().split('\t')
        if len(parts) >= 9:
            entries.append({
                'rank': parts[0],
                'standard': parts[1],
                'aliases': parts[2] if parts[2] != '-' else '',
                'type': parts[3],
                'freq': int(parts[4]),
                'title': int(parts[5]),
                'bold': int(parts[6]),
                'table': int(parts[7]),
                'score': float(parts[8]),
            })
    
    print(f"输入: {len(entries)} 条")
    
    # COPD聚焦过滤
    kept = []
    removed = []
    for e in entries:
        std = e['standard']
        aliases = e['aliases']
        word_type = e['type']
        
        keep, reason = is_copd_related(std, aliases, word_type)
        
        if keep:
            kept.append(e)
        else:
            removed.append((std, word_type, reason))
    
    print(f"保留: {len(kept)} 条")
    print(f"过滤: {len(removed)} 条")
    
    # 统计过滤原因
    reason_counts = {}
    for _, _, r in removed:
        reason_counts[r] = reason_counts.get(r, 0) + 1
    print("\n主要过滤原因:")
    for r, c in sorted(reason_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {r}: {c} 条")
    
    # 重新排序
    TYPE_ORDER = ['Disease', 'Symptom', 'Examination', 'Medication', 'Treatment',
                  'Pathology', 'Complication', 'RiskFactor', 'Guideline',
                  'Organization', 'TCM_Syndrome', 'Concept', 'Anatomical']
    kept.sort(key=lambda x: (TYPE_ORDER.index(x['type']) if x['type'] in TYPE_ORDER else 99, -x['score']))
    for i, e in enumerate(kept, 1):
        e['rank'] = i
    
    # 类型统计
    type_counts = {}
    for e in kept:
        t = e['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print(f"\n最终: {len(kept)} 条")
    print("\n类型分布:")
    for t in TYPE_ORDER:
        if t in type_counts:
            print(f"  {t:<14} : {type_counts[t]:>3} 条")
    
    # 保存
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    tsv_path = os.path.join(OUTPUT_DIR, '30_COPD聚焦种子词典.tsv')
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write("排名\t标准术语\t同义词\t类型\t总频次\t标题\t加粗\t表格\t得分\n")
        for e in kept:
            alias = e['aliases'] if e['aliases'] else '-'
            f.write(f"{e['rank']}\t{e['standard']}\t{alias}\t{e['type']}\t"
                    f"{e['freq']}\t{e['title']}\t{e['bold']}\t{e['table']}\t{e['score']:.1f}\n")
    
    json_path = os.path.join(OUTPUT_DIR, '30_COPD聚焦种子词典.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)
    
    TYPE_LABELS = {
        'Disease': '疾病', 'Symptom': '症状体征', 'Examination': '检查检验',
        'Medication': '药物', 'Treatment': '治疗方法', 'Pathology': '病理机制',
        'Complication': '并发症', 'RiskFactor': '危险因素', 'Guideline': '指南标准',
        'Organization': '组织机构', 'TCM_Syndrome': '中医证候', 'Concept': '抽象概念',
        'Anatomical': '解剖部位',
    }
    grouped_path = os.path.join(OUTPUT_DIR, '30_COPD聚焦种子词典_按类型分组.txt')
    with open(grouped_path, 'w', encoding='utf-8') as f:
        for t in TYPE_ORDER:
            items = [e for e in kept if e['type'] == t]
            if not items:
                continue
            f.write(f"\n{'='*50}\n")
            f.write(f"【{TYPE_LABELS[t]} / {t}】({len(items)}条)\n")
            f.write(f"{'='*50}\n")
            for e in items:
                alias = f" ({e['aliases']})" if e['aliases'] else ""
                f.write(f"  - {e['standard']}{alias}\n")
    
    wordlist_path = os.path.join(OUTPUT_DIR, '30_COPD聚焦种子词典.txt')
    with open(wordlist_path, 'w', encoding='utf-8') as f:
        for e in kept:
            f.write(e['standard'] + '\n')
    
    full_path = os.path.join(OUTPUT_DIR, '30_COPD聚焦种子词典_含同义词.txt')
    with open(full_path, 'w', encoding='utf-8') as f:

        for e in kept:
            line = e['standard']
            if e['aliases']:
                line += ' | ' + ' | '.join(e['aliases'].split('、'))
            f.write(line + '\n')
    
    print(f"\n[已保存]")
    print(f"  最终TSV: {tsv_path}")
    print(f"  JSON: {json_path}")
    print(f"  按类型分组: {grouped_path}")
    print(f"  标准词表: {wordlist_path}")
    print(f"  含同义词: {full_path}")
    
    # 预览
    print("\n" + "=" * 70)
    print("Top 50 COPD聚焦种子词典")
    print("=" * 70)
    print(f"{'排名':<4} {'标准术语':<24} {'类型':<10} {'同义词':<16} {'频次':<5} {'得分':<6}")
    print("-" * 70)
    for e in kept[:50]:
        alias = e['aliases'][:14] if e['aliases'] else '-'
        print(f"{e['rank']:<4} {e['standard']:<24} {e['type']:<10} {alias:<16} {e['freq']:<5} {e['score']:<6.1f}")
    
    # 列出被过滤的高分术语（供审查）
    print("\n" + "=" * 70)
    print("被过滤的高分术语 (得分>40) - 供人工复核")
    print("=" * 70)
    high_score_removed = [(s, t, r) for s, t, r in removed if any(
        e['standard'] == s and e['score'] > 40 for e in entries
    )]
    for s, t, r in high_score_removed[:20]:
        score = next((e['score'] for e in entries if e['standard'] == s), 0)
        print(f"  [{t}] {s} (得分{score:.1f}) -> {r}")


if __name__ == '__main__':
    main()
